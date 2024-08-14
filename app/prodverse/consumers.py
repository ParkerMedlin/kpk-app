import json
from channels.generic.websocket import AsyncWebsocketConsumer

class CartonPrintConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        self.date = self.scope['url_route']['kwargs']['date']
        self.prod_line = self.scope['url_route']['kwargs']['prodLine']
        self.group_name = f"carton_print_{self.date}_{self.prod_line}"

        # Join the group
        await self.channel_layer.group_add(
            self.group_name,
            self.channel_name
        )

        await self.accept()

    async def disconnect(self, close_code):
        # Leave the group
        await self.channel_layer.group_discard(
            self.group_name,
            self.channel_name
        )

    async def carton_print_update(self, event):
        # Send the update to WebSocket
        await self.send(text_data=json.dumps({
            'itemCode': event['itemCode'],
            'isPrinted': event['isPrinted'],
        }))