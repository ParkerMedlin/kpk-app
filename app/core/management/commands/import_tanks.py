import csv
from django.core.management import BaseCommand
from core.models import StorageTank


class Command(BaseCommand):
    help = 'Load the foamfactor csv file into the database'

    def add_arguments(self, parser):
        parser.add_argument('--path', type=str)

    def handle(self, *args, **kwargs):
        path = kwargs['path']
        with open(path, 'rt') as f:
            reader = csv.reader(f, dialect='excel')
            # skip the header row
            next(reader)
            for row in reader:
                imported_storage_tank = StorageTank(
                    tank_label = row[0],
                    distance_A = row[1],
                    distance_B = row[2],
                    max_gallons = row[3],
                    max_inches = row[4],
                    gallons_per_inch = row[5]
                )
                imported_storage_tank.save()