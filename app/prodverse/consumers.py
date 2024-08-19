import json
import logging
import redis
from channels.generic.websocket import AsyncWebsocketConsumer

logger = logging.getLogger(__name__)

# Initialize Redis connection
redis_client = redis.StrictRedis(host='kpk-app_redis_1', port=6379, db=0, decode_responses=True)

class CartonPrintConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        self.date = self.scope['url_route']['kwargs']['date']
        self.prod_line = self.scope['url_route']['kwargs']['prodLine'].replace(" ", "_")
        self.group_name = f"carton_print_{self.date}_{self.prod_line}"

        # Log connection
        logger.info(f"WebSocket connection established for group: {self.group_name}")

        # Join the group
        await self.channel_layer.group_add(
            self.group_name,
            self.channel_name
        )

        await self.accept()

    async def disconnect(self, close_code):
        # Log disconnection
        logger.info(f"WebSocket connection closed for group: {self.group_name}")

        # Leave the group
        await self.channel_layer.group_discard(
            self.group_name,
            self.channel_name
        )

    async def receive(self, text_data):
        data = json.loads(text_data)
        item_code = data['itemCode']
        is_printed = data['isPrinted']
        redis_key = f"carton_print:{self.date}:{self.prod_line}"

        # Log the action
        logger.info(f"Updating Redis: {redis_key} - {item_code} -> {is_printed}")

        # Update Redis
        if is_printed:
            redis_client.sadd(redis_key, item_code)
        else:
            redis_client.srem(redis_key, item_code)

        # Log the current state of the Redis set
        current_items = redis_client.smembers(redis_key)
        logger.info(f"Current items in Redis for {redis_key}: {list(current_items)}")

        # Broadcast the update to the group
        await self.channel_layer.group_send(
            self.group_name,
            {
                "type": "carton_print_update",
                "itemCode": item_code,
                "isPrinted": is_printed,
            }
        )

    async def carton_print_update(self, event):
        # Log the broadcast event
        logger.info(f"Broadcasting update: {event}")

        # Send the update to WebSocket
        await self.send(text_data=json.dumps({
            'itemCode': event['itemCode'],
            'isPrinted': event['isPrinted'],
        }))

class ScheduleUpdateConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        await self.channel_layer.group_add("schedule_updates", self.channel_name)
        await self.accept()

    async def disconnect(self, close_code):
        await self.channel_layer.group_discard("schedule_updates", self.channel_name)

    async def receive(self, text_data):
        text_data_json = json.loads(text_data)
        message = text_data_json['message']

        await self.channel_layer.group_send(
            "schedule_updates",
            {
                'type': 'schedule_update',
                'message': message
            }
        )

    async def schedule_update(self, event):
        message = event['message']

        await self.send(text_data=json.dumps({
            'message': message
        }))