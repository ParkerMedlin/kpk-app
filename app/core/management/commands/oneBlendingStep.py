            
from django.core.management import BaseCommand
from core.models import BlendingStep

class Command(BaseCommand):
    help = 'set all the reports to NOT trigger'

    def handle(self, *args, **kwargs):            
        stepRow = BlendingStep(step_no = "1")
        stepRow.save()