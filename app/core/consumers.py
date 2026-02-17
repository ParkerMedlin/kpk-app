import asyncio
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
    DISCONNECT_TIMEOUT,
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
        try:
            await asyncio.wait_for(
                self.channel_layer.group_discard(self.group_name, self.channel_name),
                timeout=DISCONNECT_TIMEOUT,
            )
        except (asyncio.TimeoutError, Exception):
            logger.debug("group_discard timed out for %s", self.group_name)
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
        elif action == 'hide_collection':
            await self.hide_collection(data)
        elif action == 'restore_collection':
            await self.restore_collection(data)
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

    async def hide_collection(self, data):
        collection_id = data['collection_id']

        collection_data = await self.hide_collection_link(collection_id)
        if not collection_data:
            return

        event_payload = {
            'type': 'collection_hidden',
            'collection_id': collection_id,
            'collection_name': collection_data['collection_name'],
            'record_type': collection_data['record_type'],
            'created_at': collection_data['created_at'],
            'sender_channel_name': self.channel_name
        }
        await self.channel_layer.group_send(self.group_name, event_payload)
        await persist_event(self.redis_key, 'collection_hidden', {
            'collection_id': collection_id,
            'collection_name': collection_data['collection_name'],
            'record_type': collection_data['record_type'],
            'created_at': collection_data['created_at'],
        })

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

    async def restore_collection(self, data):
        collection_id = data['collection_id']

        collection_data = await self.restore_collection_link(collection_id)
        if not collection_data:
            return

        event_payload = {
            'type': 'collection_restored',
            'collection_id': collection_id,
            'collection_name': collection_data['collection_name'],
            'record_type': collection_data['record_type'],
            'link_order': collection_data['link_order'],
            'sender_channel_name': self.channel_name
        }
        await self.channel_layer.group_send(self.group_name, event_payload)
        await persist_event(self.redis_key, 'collection_restored', {
            'collection_id': collection_id,
            'collection_name': collection_data['collection_name'],
            'record_type': collection_data['record_type'],
            'link_order': collection_data['link_order']
        })
    
    async def update_collection_order(self, data):
        order_pairs = data['collection_link_order']
        sanitized_order = await self.update_collection_link_order(order_pairs)
        if sanitized_order is None:
            sanitized_order = {}

        event_payload = {
            'type': 'collection_order_updated',
            'updated_order': sanitized_order,
            'sender_channel_name': self.channel_name
        }
        await self.channel_layer.group_send(self.group_name, event_payload)
        await persist_event(self.redis_key, 'collection_order_updated', {'updated_order': sanitized_order})

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

    async def _forward_collection_event(self, event, forward_to_sender=False):
        if not forward_to_sender and event.get('sender_channel_name') == self.channel_name:
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

    async def collection_hidden(self, event):
        await self._forward_collection_event(event, forward_to_sender=True)

    async def collection_restored(self, event):
        await self._forward_collection_event(event, forward_to_sender=True)

    async def collection_added(self, event):
        await self._forward_collection_event(event, forward_to_sender=True)

    async def collection_order_updated(self, event):
        await self._forward_collection_event(event)

    @database_sync_to_async
    def save_collection_update(self, collection_id, new_name):
        collection = CountCollectionLink.objects.get(id=collection_id)
        collection.collection_name = new_name
        collection.save()

    @database_sync_to_async
    def hide_collection_link(self, collection_id):
        try:
            collection = CountCollectionLink.objects.get(id=collection_id)
            collection.is_hidden = True
            collection.save(update_fields=['is_hidden'])
            return {
                'collection_name': collection.collection_name,
                'record_type': collection.record_type,
                'created_at': collection.created_at.isoformat() if collection.created_at else None,
            }
        except ObjectDoesNotExist:
            return None

    @database_sync_to_async
    def restore_collection_link(self, collection_id):
        try:
            collection = CountCollectionLink.objects.get(id=collection_id)
            collection.is_hidden = False
            collection.save(update_fields=['is_hidden'])
            return {
                'collection_name': collection.collection_name,
                'record_type': collection.record_type,
                'link_order': collection.link_order,
            }
        except ObjectDoesNotExist:
            return None

    @database_sync_to_async
    def update_collection_link_order(self, order_pairs):
        """
        Persist the new ordering for CountCollectionLink rows and return a sanitized mapping
        that can be broadcast to other websocket clients.
        """
        if not isinstance(order_pairs, dict):
            logger.error("update_collection_link_order expected dict, received %s", type(order_pairs))
            return {}

        sanitized_pairs = {}
        for collection_id_raw, order_raw in order_pairs.items():
            try:
                collection_id = int(collection_id_raw)
                order_value = int(order_raw)
            except (TypeError, ValueError):
                logger.warning(
                    "Skipping invalid order pair for CountCollectionLink: id=%s order=%s",
                    collection_id_raw,
                    order_raw,
                )
                continue
            sanitized_pairs[collection_id] = order_value

        if not sanitized_pairs:
            return {}

        links = {
            link.id: link
            for link in CountCollectionLink.objects.filter(id__in=sanitized_pairs.keys())
        }

        updated_pairs = {}
        for collection_id, order_value in sanitized_pairs.items():
            link = links.get(collection_id)
            if not link:
                logger.warning(
                    "CountCollectionLink with id %s not found while updating order", collection_id
                )
                continue

            if link.link_order != order_value:
                link.link_order = order_value
                link.save(update_fields=['link_order'])

            updated_pairs[str(collection_id)] = order_value

        return updated_pairs
