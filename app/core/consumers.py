import json
import logging
from channels.generic.websocket import AsyncWebsocketConsumer
from channels.db import database_sync_to_async
from .models import CountCollectionLink, BlendCountRecord, BlendComponentCountRecord, ImItemWarehouse, ItemLocation
from prodverse.models import WarehouseCountRecord
from django.core.exceptions import ObjectDoesNotExist
import datetime as dt
from decimal import Decimal

logger = logging.getLogger(__name__)

class CountListConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        self.count_list_id = self.scope['url_route']['kwargs']['count_list_id']
        self.group_name = f'count_list_{self.count_list_id}'

        await self.channel_layer.group_add(
            self.group_name,
            self.channel_name
        )

        logger.info(f"WebSocket connection established for group: {self.group_name}")
        await self.accept()

    async def disconnect(self, close_code):
        await self.channel_layer.group_discard(
            self.group_name,
            self.channel_name
        )

    async def receive(self, text_data):
        data = json.loads(text_data)
        action = data.get('action')

        if action == 'update_count':
            await self.update_count(data)
        elif action == 'refresh_on_hand':
            await self.refresh_on_hand(data)
        elif action == 'update_location':
            await self.update_location(data)
        elif action == 'delete_count':
            await self.delete_count(data)

    async def update_count(self, data):
        record_id = data['record_id']
        record_type = data['record_type']
        print(data)

        await self.save_count(data)

        await self.channel_layer.group_send(
            self.group_name,
            {
                'type': 'count_updated',
                'record_id': record_id,
                'data': data
            }
        )

    async def refresh_on_hand(self, data):
        record_id = data['record_id']
        record_type = data['record_type']

        new_on_hand = float(await self.update_on_hand(record_id, record_type))

        await self.channel_layer.group_send(
            self.group_name,
            {
                'type': 'on_hand_refreshed',
                'record_id': record_id,
                'new_on_hand': new_on_hand
            }
        )

    async def update_location(self, data):
        item_code = data['item_code']
        location = data['location']

        await self.update_location_in_db(item_code, location)

        await self.channel_layer.group_send(
            self.group_name,
            {
                'type': 'location_updated',
                'item_code': item_code,
                'location': location
            }
        )

    async def delete_count(self, data):
        record_id = data['record_id']
        record_type = data['record_type']
        
        list_id = data['list_id']

        await self.delete_count_from_db(record_id, record_type)

        await self.channel_layer.group_send(
            self.group_name,
            {
                'type' : 'count_deleted',
                'record_id' : record_id,
                'list_id' : list_id
            }
        )
    
    async def count_updated(self, event):
        await self.send(text_data=json.dumps(event))

    async def on_hand_refreshed(self, event):
        await self.send(text_data=json.dumps(event))

    async def location_updated(self, event):
        await self.send(text_data=json.dumps(event))

    async def count_deleted(self, event):
        await self.send(text_data=json.dumps(event))

    @database_sync_to_async
    def save_count(self, data):
        record_id = data['record_id']
        record_type = data['record_type']
        expected_quantity = data['expected_quantity']
        counted_quantity = Decimal(data['counted_quantity']) if data['counted_quantity'] != '' else Decimal('0.0')
        
        counted_date = dt.datetime.strptime(data['counted_date'], '%Y-%m-%d').date()
        print(counted_date)
        variance = data['variance']
        counted = data['counted']
        comment = data['comment']
        print(data['comment'])

        model = self.get_model_for_record_type(record_type)
        record = model.objects.get(id=record_id)

        record.counted_quantity = counted_quantity
        record.expected_quantity = expected_quantity
        record.counted_date = counted_date
        record.variance = variance
        record.counted = counted
        record.comment = comment

        record.save()

        this_location = ItemLocation.objects.filter(item_code__iexact=record.item_code).first()
        this_location.zone = data['location']
        print(data['location'])
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
        count_list_string = count_collection.count_id_list
        count_list = count_list_string.split(',')
        count_list.remove(str(record_id))
        count_collection.count_id_list = ','.join(count_list)
        count_collection.save()

    def get_model_for_record_type(self, record_type):
        if record_type == 'blend':
            return BlendCountRecord
        elif record_type == 'blendcomponent':
            return BlendComponentCountRecord
        elif record_type == 'warehouse':
            return WarehouseCountRecord
        else:
            raise ValueError(f"Invalid record type: {record_type}")

class CountCollectionConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        
        logger.info(f"WebSocket connection established for group: 'count_collection'")

        await self.channel_layer.group_add('count_collection', self.channel_name)
        await self.accept()

    async def disconnect(self, close_code):
        await self.channel_layer.group_discard('count_collection', self.channel_name)

    async def receive(self, text_data):
        data = json.loads(text_data)
        action = data.get('action')

        if action == 'update_collection':
            await self.update_collection(data)
        elif action == 'delete_collection':
            await self.delete_collection(data)
        elif action == 'add_collection':
            await self.add_collection(data)

    async def update_collection(self, data):
        collection_id = data['collection_id']
        new_name = data['new_name']

        await self.save_collection_update(collection_id, new_name)

        await self.channel_layer.group_send(
            'count_collection',
            {
                'type': 'collection_updated',
                'collection_id': collection_id,
                'new_name': new_name
            }
        )

    async def delete_collection(self, data):
        collection_id = data['collection_id']

        await self.delete_collection_link(collection_id)

        await self.channel_layer.group_send(
            'count_collection',
            {
                'type': 'collection_deleted',
                'collection_id': collection_id
            }
        )
        # print('sendindng delett')

    async def add_collection(self, data):
        collection_id = data['collection_id']

        await self.channel_layer.group_send(
            'count_collection',
            {
                'type': 'collection_added',
                'collection_id': collection_id
            }
        )

    async def collection_updated(self, event):
        await self.send(text_data=json.dumps(event))

    async def collection_deleted(self, event):
        await self.send(text_data=json.dumps(event))

    async def collection_added(self, event):
        await self.send(text_data=json.dumps(event))

    @database_sync_to_async
    def save_collection_update(self, collection_id, new_name):
        collection = CountCollectionLink.objects.get(id=collection_id)
        collection.collection_name = new_name
        collection.save()
        
        return new_name

    @database_sync_to_async
    def delete_collection_link(self, collection_id):
        try:
            print(f'orders delettd it {collection_id}')
            collection = CountCollectionLink.objects.get(id=collection_id)
            collection.delete()
        except ObjectDoesNotExist:
            pass