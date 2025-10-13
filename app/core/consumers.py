import json
import logging
import redis
from channels.generic.websocket import AsyncWebsocketConsumer
from channels.exceptions import StopConsumer
from channels.db import database_sync_to_async
from asgiref.sync import sync_to_async
from core.models import CountCollectionLink, BlendCountRecord, BlendComponentCountRecord, ImItemWarehouse, ItemLocation, CiItem
from prodverse.models import WarehouseCountRecord
from django.core.exceptions import ObjectDoesNotExist
import datetime as dt
from decimal import Decimal

logger = logging.getLogger(__name__)

try:
    redis_client = redis.StrictRedis(host='kpk-app_redis_1', port=6379, db=0, decode_responses=True)
    # Probe connection once so failures surface early during development
    redis_client.ping()
except redis.RedisError as exc:
    logger.warning("Redis unavailable for websocket state persistence: %s", exc)
    redis_client = None

STATE_EVENT_LIMIT = 25

def _json_default(value):
    if isinstance(value, Decimal):
        return str(value)
    if isinstance(value, (dt.datetime, dt.date)):
        return value.isoformat()
    return str(value)

def _sanitize_value(value):
    if isinstance(value, dict):
        return {str(key): _sanitize_value(val) for key, val in value.items()}
    if isinstance(value, list):
        return [_sanitize_value(item) for item in value]
    if isinstance(value, tuple):
        return [_sanitize_value(item) for item in value]
    if isinstance(value, Decimal):
        return str(value)
    if isinstance(value, (dt.datetime, dt.date)):
        return value.isoformat()
    if isinstance(value, (int, float, str)) or value is None:
        return value
    return str(value)

def _sanitize_events(events):
    sanitized = []
    for entry in events or []:
        if not isinstance(entry, dict):
            continue
        event_name = entry.get('event')
        data = entry.get('data')
        if event_name is None:
            continue
        sanitized.append({
            'event': _sanitize_value(event_name),
            'data': _sanitize_value(data)
        })
    return sanitized

def _append_event_sync(redis_key: str, event_type: str, payload: dict) -> None:
    """Append an event payload to Redis with bounded history."""
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
        redis_client.set(redis_key, json.dumps(state, default=_json_default))
    except redis.RedisError as exc:
        logger.error("Error appending websocket state to Redis key %s: %s", redis_key, exc)

def _load_events_sync(redis_key: str):
    if redis_client is None:
        return []
    try:
        raw = redis_client.get(redis_key)
        if not raw:
            return []
        state = json.loads(raw)
        events = state.get('events', [])
        if not isinstance(events, list):
            return []
        return events
    except (redis.RedisError, json.JSONDecodeError) as exc:
        logger.error("Error loading websocket state from Redis key %s: %s", redis_key, exc)
        return []

async def _persist_event(redis_key: str, event_type: str, payload: dict) -> None:
    if redis_client is None:
        return
    await sync_to_async(_append_event_sync, thread_sensitive=True)(redis_key, event_type, payload)

async def _load_events(redis_key: str):
    if redis_client is None:
        return []
    return await sync_to_async(_load_events_sync, thread_sensitive=True)(redis_key)

def _clear_events_sync(redis_key: str):
    if redis_client is None:
        return
    try:
        redis_client.delete(redis_key)
    except redis.RedisError as exc:
        logger.error("Error clearing websocket state for Redis key %s: %s", redis_key, exc)

class CountListConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        self.count_list_id = self.scope['url_route']['kwargs'].get('count_list_id')

        if not self.count_list_id or self.count_list_id == "undefined":
            logger.error("Invalid count_list_id received: %s", self.count_list_id)
            await self.close(code=4000)
            return

        self.group_name = f'count_list_unique_{self.count_list_id}'
        self.redis_key = f'count_list:{self.count_list_id}'

        await self.channel_layer.group_add(
            self.group_name,
            self.channel_name
        )

        await self.accept()
        await self._send_initial_state()

    async def disconnect(self, close_code):
        await self.channel_layer.group_discard(
            self.group_name,
            self.channel_name
        )
        
        raise StopConsumer

    async def receive(self, text_data):
        try:
            data = json.loads(text_data)
        except json.JSONDecodeError:
            logger.error("Invalid JSON received on CountListConsumer: %s", text_data)
            return

        action = data.get('action')

        if action == 'update_count':
            await self.update_count(data)
        elif action == 'refresh_on_hand':
            await self.refresh_on_hand(data)
        elif action == 'update_location':
            await self.update_location(data)
        elif action == 'delete_count':
            await self.delete_count(data)
        elif action == 'add_count':
            await self.add_count(data)

    async def update_count(self, data):
        record_id = data['record_id']
        record_type = data['record_type']

        await self.save_count(data)

        event_payload = {
            'type': 'count_updated',
            'record_id': record_id,
            'data': data,
            'sender_channel_name': self.channel_name
        }
        await self.channel_layer.group_send(self.group_name, event_payload)
        await _persist_event(self.redis_key, 'count_updated', {'record_id': record_id, 'data': data})

    async def refresh_on_hand(self, data):
        record_id = data['record_id']
        record_type = data['record_type']

        new_on_hand = float(await self.update_on_hand(record_id, record_type))

        event_payload = {
            'type': 'on_hand_refreshed',
            'record_id': record_id,
            'new_on_hand': new_on_hand,
            'sender_channel_name': self.channel_name
        }
        await self.channel_layer.group_send(self.group_name, event_payload)
        await _persist_event(self.redis_key, 'on_hand_refreshed', {'record_id': record_id, 'new_on_hand': new_on_hand})

    async def update_location(self, data):
        item_code = data['item_code']
        location = data['location']

        await self.update_location_in_db(item_code, location)

        event_payload = {
            'type': 'location_updated',
            'item_code': item_code,
            'location': location,
            'sender_channel_name': self.channel_name
        }
        await self.channel_layer.group_send(self.group_name, event_payload)
        await _persist_event(self.redis_key, 'location_updated', {'item_code': item_code, 'location': location})

    async def delete_count(self, data):
        record_id = data['record_id']
        record_type = data['record_type']
        list_id = data['list_id']

        await self.delete_count_from_db(record_id, record_type, list_id)

        event_payload = {
            'type': 'count_deleted',
            'record_id': record_id,
            'list_id': list_id,
            'sender_channel_name': self.channel_name
        }
        await self.channel_layer.group_send(self.group_name, event_payload)
        await _persist_event(self.redis_key, 'count_deleted', {'record_id': record_id, 'list_id': list_id})
    
    async def add_count(self, data):
        record_type = data['record_type']
        list_id = data['list_id']
        item_code = data['item_code']

        count_info = await self.add_count_to_db(record_type, list_id, item_code)

        event_payload = {
            'type': 'count_added',
            'list_id': list_id,
            'record_id': count_info['id'],
            'item_code': count_info['item_code'],
            'item_description': count_info['item_description'],
            'expected_quantity': float(count_info['expected_quantity']),
            'counted_quantity': float(count_info['counted_quantity']),
            'counted_date': count_info['counted_date'].strftime('%Y-%m-%d'),
            'variance': float(count_info['variance']),
            'count_type': count_info['count_type'],
            'collection_id': count_info['collection_id'],
            'location': count_info['location'],
            'sender_channel_name': self.channel_name
        }
        await self.channel_layer.group_send(self.group_name, event_payload)
        await _persist_event(
            self.redis_key,
            'count_added',
            {
                key: value for key, value in event_payload.items()
                if key not in {'type', 'sender_channel_name'}
            }
        )
    
    async def count_updated(self, event):
        await self.send(text_data=json.dumps(event))

    async def container_updated(self, event):
        await self.send(text_data=json.dumps(event))

    async def on_hand_refreshed(self, event):
        await self.send(text_data=json.dumps(event))

    async def location_updated(self, event):
        await self.send(text_data=json.dumps(event))

    async def count_deleted(self, event):
        await self.send(text_data=json.dumps(event))

    async def count_added(self, event):
        await self.send(text_data=json.dumps(event))

    @database_sync_to_async
    def save_count(self, data):
        record_id = data['record_id']
        record_type = data['record_type']
        expected_quantity = data['expected_quantity']
        counted_quantity = Decimal(data['counted_quantity']) if data['counted_quantity'] != '' else Decimal('0.0')
        counted_date = dt.datetime.strptime(data['counted_date'], '%Y-%m-%d').date()
        variance = data['variance']
        counted = data['counted']
        comment = data['comment']
        containers = data['containers']
        sage_converted_quantity = data['sage_converted_quantity']

        model = self.get_model_for_record_type(record_type)
        record = model.objects.get(id=record_id)

        record.counted_quantity = counted_quantity
        record.expected_quantity = expected_quantity
        record.counted_date = counted_date
        record.variance = variance
        record.counted = counted
        record.comment = comment
        record.containers = containers
        record.sage_converted_quantity = sage_converted_quantity

        record.save()
        
        if ItemLocation.objects.filter(item_code__iexact=record.item_code).exists():
            this_location = ItemLocation.objects.filter(item_code__iexact=record.item_code).first()
            this_location.zone = data['location']
        
            this_location.save()

    @database_sync_to_async
    def update_on_hand(self, record_id, record_type):
        model = self.get_model_for_record_type(record_type)
        record = model.objects.get(id=record_id)
        quantityonhand = ImItemWarehouse.objects.filter(itemcode__iexact=record.item_code, warehousecode__exact='MTG').first().quantityonhand
        record.expected_quantity = quantityonhand
        record.save()
        return record.expected_quantity
    
    @database_sync_to_async
    def update_location_in_db(self, item_code, location):
        record = ItemLocation.objects.get(item_code=item_code)
        record.zone = location
        record.save()
    
    @database_sync_to_async
    def delete_count_from_db(self, record_id, record_type, list_id):
        count_record_model = self.get_model_for_record_type(record_type)
        record = count_record_model.objects.get(id=record_id)
        record.delete()
        count_collection = CountCollectionLink.objects.get(pk=list_id)
        count_collection.count_id_list = [id for id in count_collection.count_id_list if id != record_id]
        count_collection.save()

    @database_sync_to_async
    def add_count_to_db(self, record_type, list_id, item_code):
        """
        Adds a new count record to the database and updates the associated count collection.
        
        Args:
            record_type (str): The type of the count record (e.g., 'blend', 'blendcomponent', 'warehouse').
            list_id (int): The ID of the count collection list to which the count record belongs.
            count_data (dict): A dictionary containing the count data to be added.
        """
        # Get the appropriate model based on the record type
        model = self.get_model_for_record_type(record_type)

        item_description = {item.itemcode : item.itemcodedesc for item in CiItem.objects.filter(itemcode__iexact=item_code)}
        item_quantity = {item.itemcode : item.quantityonhand for item in ImItemWarehouse.objects.filter(itemcode__iexact=item_code).filter(warehousecode__iexact='MTG')}

        this_description = item_description[item_code]
        this_item_onhandquantity = item_quantity[item_code]
        count_collection = CountCollectionLink.objects.get(pk=list_id)

        try:
            new_count_record = model(
                item_code = item_code,
                item_description = this_description,
                expected_quantity = this_item_onhandquantity,
                counted_quantity = 0,
                counted_date = dt.date.today(),
                variance = 0,
                count_type = record_type,
                collection_id = count_collection.collection_id
            )
            new_count_record.save()
                  
            # Update the count collection to include the new record
            
            count_collection.count_id_list.append(new_count_record.id)
            count_collection.save()
            
            location = ItemLocation.objects.filter(item_code__iexact=new_count_record.item_code).first().zone
        
            return {
                'id' : new_count_record.id,
                'item_code' : new_count_record.item_code,
                'item_description' : new_count_record.item_description,
                'expected_quantity' : new_count_record.expected_quantity,
                'counted_quantity' : new_count_record.counted_quantity,
                'counted_date' : new_count_record.counted_date,
                'variance' : new_count_record.variance,
                'count_type' : new_count_record.count_type,
                'collection_id' : new_count_record.collection_id,
                'location' : location
            }

        except Exception as e:
            logger.error(f"Error adding count to database: {str(e)}")

    def get_model_for_record_type(self, record_type):
        if record_type == 'blend':
            return BlendCountRecord
        elif record_type == 'blendcomponent':
            return BlendComponentCountRecord
        elif record_type == 'warehouse':
            return WarehouseCountRecord
        else:
            raise ValueError(f"Invalid record type: {record_type}")

    async def _send_initial_state(self):
        events = await _load_events(self.redis_key)
        if not events:
            return

        try:
            sanitized_events = _sanitize_events(events)
            if not sanitized_events:
                return
            payload = {
                'type': 'initial_state',
                'events': sanitized_events
            }
            await self.send(text_data=json.dumps(payload, default=_json_default))
        except (TypeError, ValueError) as exc:
            logger.error("Failed to serialize count list initial state for %s: %s", self.count_list_id, exc)
            await sync_to_async(_clear_events_sync, thread_sensitive=True)(self.redis_key)
        except Exception as exc:
            logger.exception("Unexpected error sending initial state for %s", self.count_list_id)
            await sync_to_async(_clear_events_sync, thread_sensitive=True)(self.redis_key)

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
        await _persist_event(self.redis_key, 'collection_updated', {
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
        await _persist_event(self.redis_key, 'collection_deleted', {'collection_id': collection_id})

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
        await _persist_event(self.redis_key, 'collection_added', {
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
        await _persist_event(self.redis_key, 'collection_order_updated', {'updated_order': order_pairs})

    async def _send_initial_state(self):
        redis_key_used = self.redis_key
        events = await _load_events(redis_key_used)
        if not events and getattr(self, '_legacy_redis_key', None):
            redis_key_used = self._legacy_redis_key
            events = await _load_events(redis_key_used)
        if not events:
            return

        try:
            sanitized_events = _sanitize_events(events)
            if not sanitized_events:
                return
            payload = {
                'type': 'initial_state',
                'events': sanitized_events
            }
            await self.send(text_data=json.dumps(payload, default=_json_default))
        except (TypeError, ValueError) as exc:
            logger.error("Failed to serialize count collection initial state for %s: %s", self.collection_context, exc)
            if redis_key_used:
                await sync_to_async(_clear_events_sync, thread_sensitive=True)(redis_key_used)
            await self._send_initial_state_error(str(exc))
        except Exception as exc:
            logger.exception("Unexpected error sending initial state for %s", self.collection_context)
            if redis_key_used:
                await sync_to_async(_clear_events_sync, thread_sensitive=True)(redis_key_used)
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
        payload = _sanitize_value(payload)
        try:
            await self.send(text_data=json.dumps(payload, default=_json_default))
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

    @database_sync_to_async
    def update_collection_link_order(self, order_pairs):
        try:
            for collection_id, order_value in order_pairs.items():
                collection_link = CountCollectionLink.objects.get(id=collection_id)
                collection_link.link_order = order_value
                collection_link.save()
        except ObjectDoesNotExist:
            pass

class BlendScheduleConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        context = self.scope['url_route']['kwargs'].get('schedule_context') or 'all'
        if context == "undefined":
            logger.error("Invalid blend schedule context received: %s", context)
            await self.close(code=4000)
            return

        self.schedule_context = context
        self.group_name = f'blend_schedule_unique_{self.schedule_context}'
        self.legacy_group_name = 'blend_schedule_updates'
        self.redis_key = f'blend_schedule:{self.schedule_context}'
        
        await self.channel_layer.group_add(
            self.group_name,
            self.channel_name
        )
        await self.channel_layer.group_add(
            self.legacy_group_name,
            self.channel_name
        )
        
        await self.accept()
        await self._send_initial_state()

    async def disconnect(self, close_code):
        await self.channel_layer.group_discard(
            self.group_name,
            self.channel_name
        )
        await self.channel_layer.group_discard(
            self.legacy_group_name,
            self.channel_name
        )
        raise StopConsumer

    async def receive(self, text_data):
        try:
            data = json.loads(text_data)
            action = data.get('action')
            
            if action == 'ping':
                await self.send(text_data=json.dumps({
                    'type': 'pong',
                    'timestamp': data.get('timestamp')
                }))
        except Exception as e:
            logger.error(f"❌ BlendScheduleConsumer receive error: {e}")

    async def blend_schedule_update(self, event):
        await self.send(text_data=json.dumps(event))

    async def _send_initial_state(self):
        events = await _load_events(self.redis_key)
        if events:
            await self.send(text_data=json.dumps({
                'type': 'initial_state',
                'events': events
            }))
