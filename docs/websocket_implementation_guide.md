# WebSocket Implementation Guide for KPK App

## Overview

This document outlines the approach for implementing real-time collaborative features using WebSockets in the KPK application. The implementation allows multiple users to simultaneously view and interact with shared data with changes propagating in real-time to all connected clients.

## Architecture

The implementation follows a channel-based WebSocket architecture using Django Channels with Redis as the backing store for both WebSocket communications and state persistence.

### Key Components

1. **Frontend Client**: JavaScript class that handles WebSocket connections, state updates, and UI rendering
2. **Backend Consumer**: Django Channels consumer that manages WebSocket connections, group membership, and message broadcasting
3. **Redis**: Serves dual roles as both the Channels layer for WebSocket communication and as persistent storage for feature state

## Feature-Specific URL Structure and Unique ID Generation

Each collaborative feature should be uniquely identified, typically based on URL components:

```
/app-name/feature-name/{identifier1}/{identifier2}/{identifier3}/...
```

Extract these components to create a unique identifier:

```javascript
// JavaScript (Frontend)
extractUniqueIdFromUrl() {
    // Extract unique ID from URL with proper path analysis
    const path = window.location.pathname;
    const featureRegex = /\/app-name\/feature-name\/([^\/]+)\/([^\/]+)\/([^\/]+)/;
    const match = path.match(featureRegex);
    
    if (match && match.length >= 4) {
        // We have all components
        const id1 = decodeURIComponent(match[1]);
        const id2 = decodeURIComponent(match[2]);
        const id3 = decodeURIComponent(match[3]);
        
        // Create a composite unique ID
        return `${id1}_${id2}_${id3}`;
    }
    
    // Implement fallback mechanisms
    // ...
}
```

## WebSocket Group Isolation

A critical aspect of any WebSocket implementation is ensuring that each instance has its own isolated communication channel:

1. Create unique WebSocket group names:
```python
# Python (Backend)
self.group_name = f"feature_unique_{self.unique_id}"
```

2. Ensure WebSocket connections include the properly encoded unique ID:
```javascript
// JavaScript (Frontend)
this.socket = new WebSocket(`${protocol}//${window.location.host}/ws/feature/${encodeURIComponent(this.unique_id)}/`);
```

3. Broadcast updates only to the specific group:
```python
# Python (Backend)
await self.channel_layer.group_send(
    self.group_name,
    {
        "type": "feature_update",
        "data": data,
        "sender_channel_name": self.channel_name  # Include sender to avoid echo
    }
)
```

## State Management with Redis

Implement persistent state using Redis, with unique keys for each feature instance:

```python
# Python (Backend)
self.redis_key = f"feature:{self.unique_id}"

# Store state
redis_client.set(self.redis_key, text_data)

# Retrieve state
stored_state = redis_client.get(self.redis_key)
```

The frontend should implement a debounce mechanism to prevent excessive state updates:

```javascript
// JavaScript (Frontend)
debounceUpdateState() {
    clearTimeout(this.debounceTimer);
    this.debounceTimer = setTimeout(() => {
        this.updateServerState();
    }, 500); // 500ms debounce
}
```

## Preventing Echo Effects

To prevent echo effects (where a user receives their own updates back), include the sender's channel name in each message:

```python
# Python (Backend)
async def feature_update(self, event):
    # Skip if this is the sender
    if event.get("sender_channel_name") == self.channel_name:
        return
    
    # Send to other clients...
```

## Error Handling

Implement robust error handling throughout your WebSocket implementation:

1. Validate unique IDs:
```python
# Python (Backend)
if not self.unique_id or self.unique_id == "undefined":
    logger.error(f"Invalid unique_id received: '{self.unique_id}'. Closing connection.")
    await self.close(code=4000)
    return
```

2. Handle JSON parsing errors:
```python
# Python (Backend)
try:
    parsed_state = json.loads(stored_state)
    # Use parsed state...
except json.JSONDecodeError:
    logger.error(f"Invalid JSON in stored state for {self.unique_id}, clearing corrupt data")
    redis_client.delete(self.redis_key)
```

3. Implement reconnection logic on the frontend:
```javascript
// JavaScript (Frontend)
if (!event.wasClean && this.reconnectAttempts < this.maxReconnectAttempts) {
    setTimeout(() => {
        this.reconnectAttempts++;
        this.initWebSocket();
        console.log(`Attempting to reconnect (${this.reconnectAttempts}/${this.maxReconnectAttempts})...`);
    }, this.reconnectDelay);
}
```

## ASGI Configuration

Define WebSocket routes in the ASGI configuration:

```python
# Python (asgi.py)
websocket_routes = [
    # Other routes...
    re_path(r'ws/feature/(?P<unique_id>.+)/$', FeatureConsumer.as_asgi()),
]
```

Note the use of the `.+` regex pattern which allows for complex IDs with special characters.

## Implementation Steps

1. **Define Your Data Model**: Determine what state needs to be shared in real-time

2. **Create the Consumer**:
   ```python
   # feature/consumers.py
   class FeatureConsumer(AsyncWebsocketConsumer):
       async def connect(self):
           self.unique_id = self.scope['url_route']['kwargs']['unique_id']
           
           # Validate unique_id
           if not self.unique_id:
               await self.close(code=4000)
               return
               
           self.group_name = f"feature_unique_{self.unique_id}"
           self.redis_key = f"feature:{self.unique_id}"
           
           # Join group
           await self.channel_layer.group_add(
               self.group_name,
               self.channel_name
           )
           
           await self.accept()
           
           # Send initial state
           try:
               stored_state = redis_client.get(self.redis_key)
               if stored_state:
                   parsed_state = json.loads(stored_state)
                   await self.send(text_data=json.dumps({
                       'type': 'initial_state',
                       'data': parsed_state
                   }))
           except Exception as e:
               logger.error(f"Error retrieving state: {e}")
   
       async def disconnect(self, close_code):
           # Leave group
           await self.channel_layer.group_discard(
               self.group_name,
               self.channel_name
           )
       
       async def receive(self, text_data):
           try:
               data = json.loads(text_data)
               
               # Store state
               redis_client.set(self.redis_key, text_data)
               
               # Broadcast update
               await self.channel_layer.group_send(
                   self.group_name,
                   {
                       "type": "feature_update",
                       "data": data,
                       "sender_channel_name": self.channel_name
                   }
               )
           except Exception as e:
               logger.error(f"Error in receive: {e}")
       
       async def feature_update(self, event):
           # Skip if sender
           if event.get("sender_channel_name") == self.channel_name:
               return
               
           # Send update to WebSocket
           await self.send(text_data=json.dumps({
               'type': 'feature_update',
               'data': event['data']
           }))
   ```

3. **Add ASGI Route**: Update `asgi.py` to include your new consumer:
   ```python
   websocket_routes = [
       # Existing routes...
       re_path(r'ws/feature/(?P<unique_id>.+)/$', FeatureConsumer.as_asgi()),
   ]
   ```

4. **Frontend Implementation**:
   ```javascript
   class FeatureClient {
       constructor() {
           this.socket = null;
           this.reconnectAttempts = 0;
           this.maxReconnectAttempts = 5;
           this.reconnectDelay = 3000;
           this.debounceTimer = null;
           
           // Extract unique ID
           this.unique_id = this.extractUniqueIdFromUrl();
           
           // Initialize
           this.setupFeature();
           this.initWebSocket();
       }
       
       extractUniqueIdFromUrl() {
           // Implementation specific to feature URL structure
       }
       
       initWebSocket() {
           if (this.socket) {
               this.socket.close();
           }
           
           try {
               const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
               this.socket = new WebSocket(`${protocol}//${window.location.host}/ws/feature/${encodeURIComponent(this.unique_id)}/`);
               
               this.socket.onopen = () => {
                   console.log(`WebSocket connection established`);
                   this.reconnectAttempts = 0;
               };
               
               this.socket.onmessage = (event) => {
                   const message = JSON.parse(event.data);
                   
                   if (message.type === 'feature_update') {
                       this.handleUpdate(message.data);
                   } else if (message.type === 'initial_state') {
                       this.applyInitialState(message.data);
                   }
               };
               
               // Add error and close handlers with reconnection logic
           } catch (error) {
               console.error("WebSocket initialization error:", error);
           }
       }
       
       updateServerState() {
           // Collect and send current state
           const state = this.collectCurrentState();
           
           if (this.socket && this.socket.readyState === WebSocket.OPEN) {
               this.socket.send(JSON.stringify(state));
           }
       }
       
       debounceUpdateState() {
           clearTimeout(this.debounceTimer);
           this.debounceTimer = setTimeout(() => {
               this.updateServerState();
           }, 500);
       }
       
       // Other methods specific to feature...
   }
   ```

## Key Learnings and Best Practices

1. **URL-Based Unique Identifiers**: Use URL components to create unique identifiers for WebSocket groups and Redis keys to ensure proper isolation of state.

2. **Input Validation**: Validate unique IDs before establishing WebSocket connections to prevent issues with undefined or malformed identifiers.

3. **Explicit Group Naming**: Use a distinct prefix for WebSocket groups to prevent potential collisions.

4. **URL Parameter Encoding**: Always use `encodeURIComponent()` when including URL parameters in WebSocket connections to handle special characters properly.

5. **Redis Key Namespacing**: Use a consistent prefix for Redis keys to make debugging easier and prevent key collisions.

6. **Echo Prevention**: Include the sender's channel name in messages to filter out echoes on the receiving end.

7. **Debouncing Updates**: Implement debounce logic for state updates to reduce network traffic during rapid user interactions.

8. **Comprehensive Logging**: Add detailed logging at all stages of the WebSocket lifecycle to help troubleshoot issues.

9. **Reconnection Strategy**: Implement a backoff strategy for WebSocket reconnections to improve resilience.

10. **Error Recovery**: Implement specific error handlers for different failure scenarios.

## Common Issues and Solutions

### Issue: Cross-Instance Update Leakage

**Problem**: Updates from one instance being received by users viewing different instances.

**Solution**:
- Use a truly unique WebSocket group name
- Include all relevant URL components in the unique ID
- Validate the unique ID on connection

### Issue: Undefined Unique IDs

**Problem**: WebSocket connections being established with `undefined` unique IDs.

**Solution**:
- Initialize unique ID in constructor
- Add fallback logic if ID extraction fails
- Add validation on the server side to reject invalid connections

### Issue: State Persistence Problems

**Problem**: State not being correctly stored or retrieved from Redis.

**Solution**:
- Use consistent key formatting
- Add error handling for JSON parsing
- Implement logging to track state changes

### Issue: Special Characters in IDs

**Problem**: Special characters in identifiers causing WebSocket connection failures.

**Solution**:
- Use `encodeURIComponent()` when creating WebSocket URLs
- Use flexible regex patterns in ASGI routes (`(?P<unique_id>.+)` instead of `(?P<unique_id>\w+)`)

## Conclusion

This WebSocket implementation approach provides a robust foundation for adding real-time collaborative features to the KPK application. By following these patterns and best practices, developers can implement real-time functionality that is reliable, maintainable, and properly isolated across different feature instances. 