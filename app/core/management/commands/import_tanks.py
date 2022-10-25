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
                    fill_height = row[1],
                    measuring_distance = row[2],
                    distance_A = row[3],
                    distance_B = row[4],
                    scaled_volume = row[5],
                    max_scaled_volume =row[6],
                    percent_filled = row[7],
                    gal_per_inch = row[8]
                )
                imported_storage_tank.save()