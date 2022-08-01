from django.core.management import BaseCommand
from core.models import CeleryTaskSetting

class Command(BaseCommand):
    help = 'set all the reports to NOT trigger'

    def handle(self, *args, **kwargs):
        CeleryTaskSetting.objects.create(
            checklist_issues = False,
            checklist_sub_track = False
        )
