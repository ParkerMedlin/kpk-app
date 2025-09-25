import logging
from channels.layers import get_channel_layer
from asgiref.sync import async_to_sync
from django.utils import timezone
from django.http import JsonResponse

logger = logging.getLogger(__name__)


def test_websocket_send(request):
    """Temporary test endpoint to verify WebSocket functionality"""
    try:
        channel_layer = get_channel_layer()
        logger.info(f"🔍 Test WebSocket - Channel layer: {channel_layer}")
        
        test_data = {
            'blend_id': 'test_123',
            'lot_number': 'TEST_LOT',
            'message': 'Test message from Django',
            'timestamp': timezone.now().isoformat()
        }
        
        async_to_sync(channel_layer.group_send)(
            'blend_schedule_updates',
            {
                'type': 'blend_schedule_update',
                'update_type': 'test_message',
                'data': test_data
            }
        )
        
        logger.info("🔍 Test WebSocket message sent successfully")
        return JsonResponse({'status': 'Test WebSocket message sent', 'data': test_data})
        
    except Exception as e:
        logger.error(f"❌ Test WebSocket error: {e}", exc_info=True)
        return JsonResponse({'error': str(e)}, status=500)