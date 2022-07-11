import csv
from django.core.management import BaseCommand
from core.models import Forklift


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
            idIterator = 0
            for row in reader:
                Forklift.objects.create(
                    unit_number = row[0],
                    make = row[1],
                    dept = row[2],
                    normal_operator = row[3],
                    forklift_type = row[4],
                    model_no = row[5],
                    serial_no = row[6]
                )