import json
import logging
from channels.generic.websocket import AsyncWebsocketConsumer
from channels.db import database_sync_to_async
from .models import CountCollectionLink, BlendCountRecord, BlendComponentCountRecord, ImItemWarehouse, ItemLocation, CiItem
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
        elif action == 'add_count':
            await self.add_count(data)

    async def update_count(self, data):
        record_id = data['record_id']
        record_type = data['record_type']
        print(data.get('containerId','no containerId found'))

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

        await self.delete_count_from_db(record_id, record_type, list_id)

        await self.channel_layer.group_send(
            self.group_name,
            {
                'type' : 'count_deleted',
                'record_id' : record_id,
                'list_id' : list_id
            }
        )
    
    async def add_count(self, data):
        record_type = data['record_type']
        list_id = data['list_id']
        item_code = data['item_code']

        count_info = await self.add_count_to_db(record_type, list_id, item_code)

        await self.channel_layer.group_send(
            self.group_name,
            {
                'type' : 'count_added',
                'list_id' : list_id,
                'record_id' : count_info['id'],
                'item_code' : count_info['item_code'],
                'item_description' : count_info['item_description'],
                'expected_quantity' : float(count_info['expected_quantity']),
                'counted_quantity' : float(count_info['counted_quantity']),
                'counted_date' : count_info['counted_date'].strftime('%Y-%m-%d'),
                'variance' : float(count_info['variance']),
                'count_type' : count_info['count_type'],
                'collection_id' : count_info['collection_id'],
                'location' : count_info['location']
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
        print(containers)

        model = self.get_model_for_record_type(record_type)
        record = model.objects.get(id=record_id)

        record.counted_quantity = counted_quantity
        record.expected_quantity = expected_quantity
        record.counted_date = counted_date
        record.variance = variance
        record.counted = counted
        record.comment = comment
        record.containers = containers

        record.save()

        this_location = ItemLocation.objects.filter(item_code__iexact=record.item_code).first()
        this_location.zone = data['location']
        
        this_location.save()

    @database_sync_to_async
    def update_on_hand(self, record_id, record_type):
        model = self.get_model_for_record_type(record_type)
        record = model.objects.get(id=record_id)
        quantityonhand = ImItemWarehouse.objects.filter(itemcode__iexact=record.item_code, warehousecode__exact='MTG').first().quantityonhand
        record.expected_quantity = quantityonhand
        print(quantityonhand)
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
            print(str(e))

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
        elif action == 'update_collection_order':
            await self.update_collection_order(data)

    async def update_collection(self, data):
        collection_id = data['collection_id']
        new_name = data['new_name']

        await self.save_collection_update(collection_id, new_name)

        await self.channel_layer.group_send(
            'count_collection',
            {
                'type': 'collection_updated',
                'collection_id': collection_id,
                'new_name': new_name,

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
        record_type = data['record_type']

        await self.channel_layer.group_send(
            'count_collection',
            {
                'type': 'collection_added',
                'collection_id': collection_id,
                'record_type': record_type
            }
        )
    
    async def update_collection_order(self, data):
        order_pairs = data['collection_link_order']
        await self.update_collection_link_order(order_pairs)

        await self.channel_layer.group_send(
            'count_collection',
            {
                'type': 'collection_order_updated',
                'updated_order': order_pairs
            }
        )

    async def collection_updated(self, event):
        await self.send(text_data=json.dumps(event))

    async def collection_deleted(self, event):
        await self.send(text_data=json.dumps(event))

    async def collection_added(self, event):
        await self.send(text_data=json.dumps(event))

    async def collection_order_updated(self, event):
        await self.send(text_data=json.dumps(event))

    @database_sync_to_async
    def save_collection_update(self, collection_id, new_name):
        collection = CountCollectionLink.objects.get(id=collection_id)
        collection.collection_name = new_name
        collection.save()

    @database_sync_to_async
    def delete_collection_link(self, collection_id):
        try:
            print(f'orders delettd it {collection_id}')
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