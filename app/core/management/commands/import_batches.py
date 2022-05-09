import csv
from django.core.management import BaseCommand
from core.models import lotnumrecord
from decimal import Decimal

class Command(BaseCommand):
    help = 'Load a lotnumbers csv file into the database'

    def add_arguments(self, parser):
        parser.add_argument('--path', type=str)

    def handle(self, *args, **kwargs):
        path = kwargs['path']
        with open(path, 'rt') as f:
            reader = csv.reader(f, dialect='excel')
            next(reader)
            next(reader)
            for row in reader:
                #convert null to Decimal(0)
                if row[3]:
                    rowAtThree=row[3]
                else:
                    rowAtThree=Decimal(0)
                lotnumrecord.objects.create(
                    part_number=row[0],
                    description=row[1],
                    lot_number=row[2],
                    quantity=rowAtThree,
                    date=row[4],
                )