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
        # with open(path, 'rt') as f:
        #     reader = csv.reader(f, dialect='excel')
        #     for row in reader:
        #         try:
        #             imported_blend_instruction = BlendInstruction(
        #                 blend_item_code = row[5],
        #                 step_number = row[0],
        #                 step_description = row[1],
        #                 component_item_code = row[3]
        #             )
        #             if row[3] and not row[3] == 'WATER':
        #                 print(row[3])
        #             imported_blend_instruction.save()
        #         except ValueError:
        #             continue

        with open(path, 'rt') as f:
            reader = csv.DictReader(f)
            # for key in reader:
            #     print(key)
            # for row in reader:
            #     try:
            #         imported_blend_instruction = BlendInstruction(
            #             blend_item_code = row['blend_item_code'] if row['blend_item_code'] else None,
            #             step_number = row['step_number'] if row['step_number'] else None,
            #             step_description = row['step_description'] if row['step_description'] else None,
            #             component_item_code = row['component_item_code'] if row['component_item_code'] else None
            #         )
            #         if row['component_item_code'] and not row['component_item_code'] == 'WATER':
            #             print(row['component_item_code'])
            #         imported_blend_instruction.save()
            #     except ValueError:
            #         continue
