import datetime as dt
import json
import logging
from decimal import Decimal

from asgiref.sync import sync_to_async
from channels.db import database_sync_to_async
from channels.exceptions import StopConsumer
from channels.generic.websocket import AsyncWebsocketConsumer
from django.core.exceptions import ObjectDoesNotExist

from app.websockets.base_consumer import (
    clear_events,
    json_default,
    load_events,
    persist_event,
    sanitize_events,
    sanitize_payload,
)
from core.models import (
    BlendComponentCountRecord,
    BlendCountRecord,
    CiItem,
    CountCollectionLink,
    ImItemWarehouse,
    ItemLocation,
)
from prodverse.models import WarehouseCountRecord

logger = logging.getLogger(__name__)

class CountCollectionConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        raw_context = self.scope['url_route']['kwargs'].get('collection_context')
        normalized_context = raw_context or 'count_collection_global'

        if normalized_context in {'global', 'count_collection_global', None, ''}:
            self.collection_context = 'count_collection_global'
        else:
            self.collection_context = normalized_context

        if self.collection_context == "undefined":
            logger.error("Invalid collection_context received: %s", self.collection_context)
            await self.close(code=4000)
            return

        self.group_name = f'count_collection_unique_{self.collection_context}'
        self.redis_key = f'count_collection:{self.collection_context}'
        self._legacy_redis_key = 'count_collection:global' if self.collection_context == 'count_collection_global' else None

        await self.channel_layer.group_add(self.group_name, self.channel_name)
        await self.accept()
        await self._send_initial_state()

    async def disconnect(self, close_code):
        await self.channel_layer.group_discard(self.group_name, self.channel_name)

        raise StopConsumer

    async def receive(self, text_data):
        try:
            data = json.loads(text_data)
        except json.JSONDecodeError:
            logger.error("Invalid JSON received on CountCollectionConsumer: %s", text_data)
            return

        action = data.get('action')

        if action == 'update_collection':
            await self.update_collection(data)
        elif action == 'delete_collection':
            await self.delete_collection(data)
        elif action == 'add_collection':
            await self.add_collection(data)
        elif action == 'update_collection_order':
            await self.update_collection_order(data)

    async def update_collection(self, data):
        collection_id = data['collection_id']
        new_name = data['new_name']

        await self.save_collection_update(collection_id, new_name)

        event_payload = {
            'type': 'collection_updated',
            'collection_id': collection_id,
            'new_name': new_name,
            'sender_channel_name': self.channel_name
        }
        await self.channel_layer.group_send(self.group_name, event_payload)
        await persist_event(self.redis_key, 'collection_updated', {
            'collection_id': collection_id,
            'new_name': new_name
        })

    async def delete_collection(self, data):
        collection_id = data['collection_id']

        await self.delete_collection_link(collection_id)

        event_payload = {
            'type': 'collection_deleted',
            'collection_id': collection_id,
            'sender_channel_name': self.channel_name
        }
        await self.channel_layer.group_send(self.group_name, event_payload)
        await persist_event(self.redis_key, 'collection_deleted', {'collection_id': collection_id})

    async def add_collection(self, data):
        collection_id = data['collection_id']
        record_type = data['record_type']

        event_payload = {
            'type': 'collection_added',
            'collection_id': collection_id,
            'record_type': record_type,
            'sender_channel_name': self.channel_name
        }
        await self.channel_layer.group_send(self.group_name, event_payload)
        await persist_event(self.redis_key, 'collection_added', {
            'collection_id': collection_id,
            'record_type': record_type
        })
    
    async def update_collection_order(self, data):
        order_pairs = data['collection_link_order']
        await self.update_collection_link_order(order_pairs)

        event_payload = {
            'type': 'collection_order_updated',
            'updated_order': order_pairs,
            'sender_channel_name': self.channel_name
        }
        await self.channel_layer.group_send(self.group_name, event_payload)
        await persist_event(self.redis_key, 'collection_order_updated', {'updated_order': order_pairs})

    async def _send_initial_state(self):
        redis_key_used = self.redis_key
        events = await load_events(redis_key_used)
        if not events and getattr(self, '_legacy_redis_key', None):
            redis_key_used = self._legacy_redis_key
            events = await load_events(redis_key_used)
        if not events:
            return

        try:
            sanitized_events = sanitize_events(events)
            if not sanitized_events:
                return
            payload = {
                'type': 'initial_state',
                'events': sanitized_events
            }
            await self.send(text_data=json.dumps(payload, default=json_default))
        except (TypeError, ValueError) as exc:
            logger.error("Failed to serialize count collection initial state for %s: %s", self.collection_context, exc)
            if redis_key_used:
                await clear_events(redis_key_used)
            await self._send_initial_state_error(str(exc))
        except Exception as exc:
            logger.exception("Unexpected error sending initial state for %s", self.collection_context)
            if redis_key_used:
                await clear_events(redis_key_used)
            await self._send_initial_state_error(str(exc))

    async def _send_initial_state_error(self, message: str):
        try:
            await self.send(text_data=json.dumps({
                'type': 'initial_state_error',
                'error': message
            }))
        except Exception:
            logger.exception("Failed to notify client about initial state error for %s", self.collection_context)

    async def _forward_collection_event(self, event):
        if event.get('sender_channel_name') == self.channel_name:
            return

        payload = {key: value for key, value in event.items() if key != 'sender_channel_name'}
        payload = sanitize_payload(payload)
        try:
            await self.send(text_data=json.dumps(payload, default=json_default))
        except (TypeError, ValueError) as exc:
            logger.error("Failed to serialize count collection event for %s: %s", self.collection_context, exc)
        except Exception:
            logger.exception("Unexpected error forwarding count collection event for %s", self.collection_context)

    async def collection_updated(self, event):
        await self._forward_collection_event(event)

    async def collection_deleted(self, event):
        await self._forward_collection_event(event)

    async def collection_added(self, event):
        await self._forward_collection_event(event)

    async def collection_order_updated(self, event):
        await self._forward_collection_event(event)

    @database_sync_to_async
    def save_collection_update(self, collection_id, new_name):
        collection = CountCollectionLink.objects.get(id=collection_id)
        collection.collection_name = new_name
        collection.save()

    @database_sync_to_async
    def delete_collection_link(self, collection_id):
        try:
            collection = CountCollectionLink.objects.get(id=collection_id)
            collection.delete()
        except ObjectDoesNotExist:
            pass
