import csv
from django.core.management import BaseCommand
from core.models import blendInstruction

class Command(BaseCommand):
    help = 'Load a lotnumbers csv file into the database'

    def add_arguments(self, parser):
        parser.add_argument('--path', type=str)

    def handle(self, *args, **kwargs):
        path = kwargs['path']
        with open(path, 'rt') as f:
            reader = csv.reader(f, dialect='excel')
            for row in reader:
                blendInstruction.objects.create(
                    bill_no=row[0],
                    status=row[1],
                    step_no=row[2],
                    step_desc=row[3],
                    component_code=row[4],
                    component_desc=row[5],
                )