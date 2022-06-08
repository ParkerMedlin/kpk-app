import csv
from django.core.management import BaseCommand
from core.models import Forklift
from decimal import Decimal


class Command(BaseCommand):
    help = 'Load the forklift csv file into the database'

    def add_arguments(self, parser):
        parser.add_argument('--path', type=str)

    def handle(self, *args, **kwargs):
        path = kwargs['path']
        with open(path, 'rt') as f:
            reader = csv.reader(f, dialect='excel')
            # skip the first two rows
            next(reader)
            for row in reader:
                Forklift.objects.create(
                    forklift_id = row[0],
                    forklift_serial = row[1],
                    forklift_operator = row[2],
                )