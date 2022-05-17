import csv
from django.core.management import BaseCommand
from core.models import blendInstruction

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
                blendInstruction.objects.create(
                    step_no = row[0],
                    step_desc = row[1],
                    component_item_code = row[2],
                    blend_part_num = row[3],
                    ref_no = row[4],
                    prepared_by = row[5],
                    prepared_date = row[6],
                    lbs_per_gal = row[7],
                )