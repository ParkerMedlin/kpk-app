import json
import logging
from channels.generic.websocket import AsyncWebsocketConsumer
from channels.db import database_sync_to_async
from .models import CountCollectionLink, BlendCountRecord, BlendComponentCountRecord
from django.core.exceptions import ObjectDoesNotExist

logger = logging.getLogger(__name__)

# class CountListConsumer(AsyncWebsocketConsumer):
#     async def connect(self):
#         self.count_list_id = self.scope['url_route']['kwargs']['count_list_id']
#         self.group_name = f'count_list_{self.count_list_id}'

#         await self.channel_layer.group_add(
#             self.group_name,
#             self.channel_name
#         )
#         logger.info(f"WebSocket connection established for group: {self.group_name}")
#         await self.accept()

#     async def disconnect(self, close_code):
#         await self.channel_layer.group_discard(
#             self.group_name,
#             self.channel_name
#         )

#     async def receive(self, text_data):
#         data = json.loads(text_data)
#         action = data.get('action')

#         if action == 'update_count':
#             await self.update_count(data)
#         elif action == 'refresh_on_hand':
#             await self.refresh_on_hand(data)

#     async def update_count(self, data):
#         record_id = data['record_id']
#         new_count = data['new_count']
#         record_type = data['record_type']

#         await self.save_count(record_id, new_count, record_type)

#         await self.channel_layer.group_send(
#             self.group_name,
#             {
#                 'type': 'count_updated',
#                 'record_id': record_id,
#                 'new_count': new_count
#             }
#         )

#     async def refresh_on_hand(self, data):
#         record_id = data['record_id']
#         record_type = data['record_type']

#         new_on_hand = await self.get_new_on_hand(record_id, record_type)

#         await self.channel_layer.group_send(
#             self.group_name,
#             {
#                 'type': 'on_hand_refreshed',
#                 'record_id': record_id,
#                 'new_on_hand': new_on_hand
#             }
#         )

#     async def count_updated(self, event):
#         await self.send(text_data=json.dumps(event))

#     async def on_hand_refreshed(self, event):
#         await self.send(text_data=json.dumps(event))

#     @database_sync_to_async
#     def save_count(self, record_id, new_count, record_type):
#         model = self.get_model_for_record_type(record_type)
#         record = model.objects.get(id=record_id)
#         record.counted_quantity = new_count
#         record.save()

#     @database_sync_to_async
#     def get_new_on_hand(self, record_id, record_type):
#         model = self.get_model_for_record_type(record_type)
#         record = model.objects.get(id=record_id)
#         # Implement your logic to get the new on-hand quantity
#         # This is just a placeholder
#         return record.expected_quantity

#     def get_model_for_record_type(self, record_type):
#         if record_type == 'blend':
#             return BlendCountRecord
#         elif record_type == 'blendcomponent':
#             return BlendComponentCountRecord
#         elif record_type == 'warehouse':
#             return WarehouseCountRecord
#         else:
#             raise ValueError(f"Invalid record type: {record_type}")

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
        print('sendindng delett')

    async def collection_updated(self, event):
        await self.send(text_data=json.dumps(event))

    async def collection_deleted(self, event):
        await self.send(text_data=json.dumps(event))

    @database_sync_to_async
    def save_collection_update(self, collection_id, new_name):
        collection = CountCollectionLink.objects.get(id=collection_id)
        collection.collection_id = new_name
        collection.save()

    @database_sync_to_async
    def delete_collection_link(self, collection_id):
        try:
            print(f'orders delettd it {collection_id}')
            collection = CountCollectionLink.objects.get(id=collection_id)
            collection.delete()
        except ObjectDoesNotExist:
            pass