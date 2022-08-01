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
            # skip the first two rows
            next(reader)
            next(reader)
            for row in reader:
                BlendInstruction.objects.create(
                    step_no = int(float(row[0])),
                    step_desc = row[1],
                    step_qty = row[3],
                    step_unit = row[4],
                    component_item_code = str(row[5]),
                    notes_1 = row[6],
                    notes_2 = row[7],
                    blend_part_num = row[11],
                    ref_no = row[12],
                    prepared_by = row[13],
                    prepared_date = row[14],
                    lbs_per_gal = row[15],
                )
