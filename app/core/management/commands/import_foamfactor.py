import csv
from django.core.management import BaseCommand
from core.models import FoamFactor


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
                imported_foam_factor = FoamFactor(
                    blend = row[0],
                    factor = row[1],
                    blenddesc = row[2],
                )
                imported_foam_factor.save()