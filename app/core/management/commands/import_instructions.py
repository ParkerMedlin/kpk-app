import csv
from django.core.management import BaseCommand
from core.models import BlendInstruction
from decimal import Decimal


class Command(BaseCommand):
    help = 'Load the blendinstructions csv file into the database'

    def add_arguments(self, parser):
        parser.add_argument('--path', type=str)

    def handle(self, *args, **kwargs):
        path = kwargs['path']
        with open(path, 'rt') as f:
            reader = csv.reader(f, dialect='excel')
            next(reader)
            next(reader)
            for row in reader:
                try:
                    imported_blend_instruction = BlendInstruction(
                        blend_item_code = row[4],
                        step_number = int(float(row[0])),
                        step_description = row[1],
                        component_item_code = row[2],
                    )
                    imported_blend_instruction.save()
                except ValueError:
                    continue
