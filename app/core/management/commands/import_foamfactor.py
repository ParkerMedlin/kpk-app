import csv
from django.core.management import BaseCommand
from core.models import FoamFactor
from decimal import Decimal


class Command(BaseCommand):
    help = 'Load the foamfactor csv file into the database'

    def add_arguments(self, parser):
        parser.add_argument('--path', type=str)

    def handle(self, *args, **kwargs):
        path = kwargs['path']
        with open(path, 'rt') as f:
            reader = csv.reader(f, dialect='excel')
            # skip the first two rows
            next(reader)
            idIterator = 0
            for row in reader:
                FoamFactor.objects.create(
                    blend = row[0],
                    factor = row[1],
                    blendDesc = row[2],
                )