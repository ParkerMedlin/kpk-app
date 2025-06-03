from django.core.management.base import BaseCommand
from django.utils import timezone
from channels.layers import get_channel_layer
from asgiref.sync import async_to_sync
import redis
import json
import logging

from core.models import LotNumRecord, BlendSheetPrintLog, DeskOneSchedule, DeskTwoSchedule, LetDeskSchedule
from django.contrib.auth import get_user_model

User = get_user_model()
logger = logging.getLogger(__name__)

class Command(BaseCommand):
    help = 'Process Excel macro completion events from Redis'

    def handle(self, *args, **options):
        redis_client = redis.Redis(host='redis', port=6379, decode_responses=True)
        pubsub = redis_client.pubsub()
        pubsub.subscribe('excel_macro_completions')
        self.stdout.write(self.style.SUCCESS('Subscribed to excel_macro_completions channel'))

        for message in pubsub.listen():
            if message['type'] != 'message':
                continue
            try:
                event_data = json.loads(message['data'])
                self.process_completion(event_data)
            except Exception as e:
                logger.error(f"Error processing completion event: {e}")

    def process_completion(self, event_data):
        lot_id = event_data.get('lot_num_record_id')
        if not lot_id:
            return

        try:
            lot_record = LotNumRecord.objects.get(pk=lot_id)
        except LotNumRecord.DoesNotExist:
            logger.warning(f"LotNumRecord not found for id {lot_id}")
            return

        macro_to_run = event_data.get('macro_to_run')

        # Create print log snapshot
        details_snapshot = {
            'lot_number': lot_record.lot_number,
            'item_code': lot_record.item_code,
            'lot_quantity': str(lot_record.lot_quantity),
            'run_date': lot_record.run_date.strftime('%Y-%m-%d %H:%M:%S') if lot_record.run_date else None,
            'item_description': lot_record.item_description,
            'line': lot_record.line,
            'print_type': 'single_blend_sheet' if macro_to_run == 'blndSheetGen' else 'production_package'
        }

        # Identify user
        user = None
        user_id = event_data.get('user_id')
        if user_id:
            try:
                user = User.objects.get(pk=user_id)
            except User.DoesNotExist:
                user = None

        # Write to BlendSheetPrintLog
        BlendSheetPrintLog.objects.create(
            lot_num_record=lot_record,
            printed_by=user,
            details_at_print_time=details_snapshot,
            printed_at=timezone.now()
        )
        logger.info(f"Logged print event for lot {lot_record.lot_number}")

        # Broadcast WebSocket updates
        channel_layer = get_channel_layer()
        # Desk schedule updates
        desk_models = [DeskOneSchedule, DeskTwoSchedule, LetDeskSchedule]
        for model_cls in desk_models:
            schedule_items = model_cls.objects.filter(lot=lot_record.lot_number)
            for item in schedule_items:
                status_data = {
                    'blend_id': item.pk,
                    'lot_num_record_id': lot_record.pk,
                    'has_been_printed': True,
                    'last_print_event_str': timezone.now().strftime('%b %d, %Y'),
                    'print_history_json': getattr(lot_record, 'blend_sheet_print_history_json_data', '[]'),
                    'was_edited_after_last_print': getattr(lot_record, 'was_edited_after_last_print', False),
                    'blend_area': item.blend_area,
                    'item_code': item.item_code,
                    'lot_number': lot_record.lot_number,
                    'is_urgent': getattr(lot_record, 'is_urgent', False)
                }
                async_to_sync(channel_layer.group_send)(
                    'blend_schedule_updates',
                    {
                        'type': 'blend_schedule_update',
                        'update_type': 'blend_status_changed',
                        'data': status_data
                    }
                )

        # Additional update for non-desk lines
        if lot_record.line in ['Hx', 'Dm', 'Totes']:
            status_data = {
                'blend_id': lot_record.pk,
                'lot_num_record_id': lot_record.pk,
                'has_been_printed': True,
                'last_print_event_str': timezone.now().strftime('%b %d, %Y'),
                'print_history_json': getattr(lot_record, 'blend_sheet_print_history_json_data', '[]'),
                'was_edited_after_last_print': getattr(lot_record, 'was_edited_after_last_print', False),
                'blend_area': lot_record.line,
                'item_code': lot_record.item_code,
                'lot_number': lot_record.lot_number,
                'is_urgent': getattr(lot_record, 'is_urgent', False)
            }
            async_to_sync(channel_layer.group_send)(
                'blend_schedule_updates',
                {
                    'type': 'blend_schedule_update',
                    'update_type': 'blend_status_changed',
                    'data': status_data
                }
            )
