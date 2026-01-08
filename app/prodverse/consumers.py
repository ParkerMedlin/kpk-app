import asyncio
import json
import logging

from channels.exceptions import StopConsumer
from channels.generic.websocket import AsyncWebsocketConsumer

from app.websockets.base_consumer import (
    DISCONNECT_TIMEOUT,
    load_events,
    persist_event,
)

logger = logging.getLogger(__name__)

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
        try:
            await asyncio.wait_for(
                self.channel_layer.group_discard(self.group_name, self.channel_name),
                timeout=DISCONNECT_TIMEOUT,
            )
        except (asyncio.TimeoutError, Exception):
            logger.debug("group_discard timed out for %s", self.group_name)
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
        await persist_event(self.redis_key, 'schedule_update', {'message': message})

    async def schedule_update(self, event):
        message = event['message']

        await self.send(text_data=json.dumps({
            'message': message
        }))

    async def _send_initial_state(self):
        events = await load_events(self.redis_key)
        if events:
            await self.send(text_data=json.dumps({
                'type': 'initial_state',
                'events': events
            }))
