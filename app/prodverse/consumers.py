import json
import logging
import redis
from channels.generic.websocket import AsyncWebsocketConsumer
from channels.exceptions import StopConsumer
from asgiref.sync import sync_to_async

logger = logging.getLogger(__name__)

# Initialize Redis connection
redis_client = redis.StrictRedis(host='kpk-app_redis_1', port=6379, db=0, decode_responses=True)

STATE_EVENT_LIMIT = 25

def _append_event_sync(redis_key: str, event_type: str, payload: dict) -> None:
    if redis_client is None:
        return
    try:
        existing = redis_client.get(redis_key)
        if existing:
            try:
                state = json.loads(existing)
            except json.JSONDecodeError:
                state = {'events': []}
        else:
            state = {'events': []}
        events = state.get('events', [])
        events.append({'event': event_type, 'data': payload})
        state['events'] = events[-STATE_EVENT_LIMIT:]
        redis_client.set(redis_key, json.dumps(state))
    except redis.RedisError as exc:
        logger.error("Error appending Redis state for %s: %s", redis_key, exc)

def _load_events_sync(redis_key: str):
    if redis_client is None:
        return []
    try:
        raw = redis_client.get(redis_key)
        if not raw:
            return []
        state = json.loads(raw)
        return state.get('events', [])
    except (redis.RedisError, json.JSONDecodeError) as exc:
        logger.error("Error loading Redis state for %s: %s", redis_key, exc)
        return []

async def _persist_event(redis_key: str, event_type: str, payload: dict) -> None:
    if redis_client is None:
        return
    await sync_to_async(_append_event_sync, thread_sensitive=True)(redis_key, event_type, payload)

async def _load_events(redis_key: str):
    if redis_client is None:
        return []
    return await sync_to_async(_load_events_sync, thread_sensitive=True)(redis_key)

class CartonPrintConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        self.date = self.scope['url_route']['kwargs'].get('date')
        raw_prod_line = self.scope['url_route']['kwargs'].get('prodLine')
        self.prod_line = raw_prod_line.replace(" ", "_") if raw_prod_line else None

        if not self.date or not self.prod_line or self.date == "undefined" or self.prod_line == "undefined":
            logger.error("Invalid carton print connection parameters: date=%s, prod_line=%s", self.date, self.prod_line)
            await self.close(code=4000)
            return

        self.group_name = f"carton_print_unique_{self.date}_{self.prod_line}"
        self.redis_key = f"carton_print:{self.date}:{self.prod_line}"
        self.events_key = f"carton_print_events:{self.date}:{self.prod_line}"

        # Log connection
        logger.info(f"WebSocket connection established for group: {self.group_name}")

        # Join the group
        await self.channel_layer.group_add(
            self.group_name,
            self.channel_name
        )

        await self.accept()
        await self._send_initial_state()

    async def disconnect(self, close_code):
        # Log disconnection
        logger.info(f"WebSocket connection closed for group: {self.group_name}")

        # Leave the group
        await self.channel_layer.group_discard(
            self.group_name,
            self.channel_name
        )

        raise StopConsumer

    async def receive(self, text_data):
        data = json.loads(text_data)
        item_code = data['itemCode']
        is_printed = data['isPrinted']

        # Log the action
        logger.info(f"Updating Redis: {self.redis_key} - {item_code} -> {is_printed}")

        # Update Redis
        try:
            if is_printed:
                redis_client.sadd(self.redis_key, item_code)
            else:
                redis_client.srem(self.redis_key, item_code)
        except redis.RedisError as exc:
            logger.error("Error updating Redis set %s: %s", self.redis_key, exc)

        # Log the current state of the Redis set
        try:
            current_items = redis_client.smembers(self.redis_key)
            logger.info(f"Current items in Redis for {self.redis_key}: {list(current_items)}")
        except redis.RedisError:
            logger.info("Unable to retrieve current items for %s", self.redis_key)
            current_items = []

        # Broadcast the update to the group
        await self.channel_layer.group_send(
            self.group_name,
            {
                "type": "carton_print_update",
                "itemCode": item_code,
                "isPrinted": is_printed,
                "sender_channel_name": self.channel_name
            }
        )
        await _persist_event(self.events_key, "carton_print_update", {
            "itemCode": item_code,
            "isPrinted": is_printed
        })

    async def carton_print_update(self, event):
        # Log the broadcast event
        logger.info(f"Broadcasting update: {event}")

        # Send the update to WebSocket
        await self.send(text_data=json.dumps({
            'itemCode': event['itemCode'],
            'isPrinted': event['isPrinted'],
        }))

    async def _send_initial_state(self):
        events = await _load_events(self.events_key)
        if events:
            await self.send(text_data=json.dumps({
                'type': 'initial_state',
                'events': events
            }))
            return

        # Fallback to set membership snapshot if no events stored yet
        if redis_client is None:
            return
        try:
            current_items = await sync_to_async(redis_client.smembers, thread_sensitive=True)(self.redis_key)
        except redis.RedisError as exc:
            logger.error("Error loading initial carton print state for %s: %s", self.redis_key, exc)
            return

        if current_items:
            events = [
                {
                    'event': 'carton_print_update',
                    'data': {
                        'itemCode': item,
                        'isPrinted': True
                    }
                }
                for item in current_items
            ]
            await self.send(text_data=json.dumps({
                'type': 'initial_state',
                'events': events
            }))

class ScheduleUpdateConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        self.schedule_context = self.scope['url_route']['kwargs'].get('schedule_context') or 'global'
        if self.schedule_context == "undefined":
            logger.error("Invalid schedule context received: %s", self.schedule_context)
            await self.close(code=4000)
            return

        self.group_name = f"schedule_updates_unique_{self.schedule_context}"
        self.redis_key = f"schedule_updates:{self.schedule_context}"

        await self.channel_layer.group_add(self.group_name, self.channel_name)
        await self.accept()
        await self._send_initial_state()

    async def disconnect(self, close_code):
        await self.channel_layer.group_discard(self.group_name, self.channel_name)

        raise StopConsumer

    async def receive(self, text_data):
        text_data_json = json.loads(text_data)
        message = text_data_json['message']

        await self.channel_layer.group_send(
            self.group_name,
            {
                'type': 'schedule_update',
                'message': message,
                'sender_channel_name': self.channel_name
            }
        )
        await _persist_event(self.redis_key, 'schedule_update', {'message': message})

    async def schedule_update(self, event):
        message = event['message']

        await self.send(text_data=json.dumps({
            'message': message
        }))

    async def _send_initial_state(self):
        events = await _load_events(self.redis_key)
        if events:
            await self.send(text_data=json.dumps({
                'type': 'initial_state',
                'events': events
            }))

class SpecSheetConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        self.spec_id = self.scope['url_route']['kwargs']['spec_id']
        
        # Add additional debugging and validation for spec_id
        logger.info(f"Connecting with raw spec_id value: '{self.spec_id}'")
        
        # Verify spec_id is not empty or malformed
        if not self.spec_id or self.spec_id == "undefined":
            logger.error(f"Invalid spec_id received: '{self.spec_id}'. Closing connection.")
            # Close with error code
            await self.close(code=4000)
            return
            
        # Create a group name that is guaranteed to be unique per spec sheet
        # Use a specific prefix to avoid any collision with other WebSocket groups
        self.group_name = f"spec_sheet_unique_{self.spec_id}"
        self.redis_key = f"spec_sheet:{self.spec_id}"

        # Log connection with detailed spec_id information
        logger.info(f"WebSocket connection established for spec sheet: {self.group_name} with ID: {self.spec_id}")
        logger.debug(f"Redis key for state storage: {self.redis_key}")

        # Join the group - ensure we're using the updated group name
        await self.channel_layer.group_add(
            self.group_name,
            self.channel_name
        )

        await self.accept()
        
        # Retrieve and send the current state from Redis if available
        try:
            stored_state = redis_client.get(self.redis_key)
            if stored_state:
                logger.info(f"Retrieved stored state for spec sheet: {self.spec_id}")
                logger.debug(f"State content: {stored_state[:100]}...")  # Log first 100 chars to avoid huge logs
                
                # Parse stored state to ensure it's valid JSON before sending
                try:
                    parsed_state = json.loads(stored_state)
                    await self.send(text_data=json.dumps({
                        'type': 'initial_state',
                        'data': parsed_state
                    }))
                except json.JSONDecodeError:
                    logger.error(f"Invalid JSON in stored state for {self.spec_id}, clearing corrupt data")
                    redis_client.delete(self.redis_key)
            else:
                logger.info(f"No stored state found for spec sheet: {self.spec_id}")
        except Exception as e:
            logger.error(f"Error retrieving spec sheet state from Redis: {e}")

    async def disconnect(self, close_code):
        # Log disconnection
        logger.info(f"WebSocket connection closed for spec sheet: {self.group_name} with ID: {self.spec_id}")

        # Leave the group - ensure we're using the updated group name
        await self.channel_layer.group_discard(
            self.group_name,
            self.channel_name
        )
        raise StopConsumer

    async def receive(self, text_data):
        try:
            data = json.loads(text_data)
            
            # Ensure that data includes this.spec_id to guarantee we're saving to the correct key
            try:
                # Store the state in Redis for persistence
                redis_client.set(self.redis_key, text_data)
                logger.info(f"Updated Redis state for spec sheet: {self.spec_id}")
                logger.debug(f"Updated with data: {text_data[:100]}...")  # Log first 100 chars
            except Exception as e:
                logger.error(f"Error storing spec sheet state in Redis: {e}")
            
            # Log the action
            logger.info(f"Spec sheet update received for {self.group_name} with ID: {self.spec_id}")
            
            # Broadcast the update to ONLY this specific group
            await self.channel_layer.group_send(
                self.group_name,  # Using our specific unique group name
                {
                    "type": "spec_sheet_update",
                    "data": data,
                    "sender_channel_name": self.channel_name  # Include sender to avoid echo
                }
            )
        except json.JSONDecodeError:
            logger.error(f"Received invalid JSON data for spec sheet: {self.spec_id}")
        except Exception as e:
            logger.error(f"Unexpected error in receive for spec sheet {self.spec_id}: {e}")

    async def spec_sheet_update(self, event):
        # Skip if this is the sender
        if event.get("sender_channel_name") == self.channel_name:
            return
            
        # Log the broadcast event
        logger.info(f"Broadcasting spec sheet update to clients in {self.group_name} with ID: {self.spec_id}")

        # Send the update to WebSocket clients
        await self.send(text_data=json.dumps({
            'type': 'spec_sheet_update',
            'data': event['data']
        }))
