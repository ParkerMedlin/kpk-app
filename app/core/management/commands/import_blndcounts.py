import csv
from django.core.management import BaseCommand
from core.models import BlendCount


class Command(BaseCommand):
    help = 'Load the blndschcounts csv file into the database'

    def add_arguments(self, parser):
        parser.add_argument('--path', type=str)

    def handle(self, *args, **kwargs):
        path = kwargs['path']
        with open(path, 'rt') as f:
            reader = csv.reader(f, dialect='excel')
            # skip the header row
            next(reader)
            for row in reader:
                BlendCount.objects.create(
                    blend_pn = row[0],
                    blend_desc = row[1],
                    starttime = row[2],
                    expOH = row[3],
                    count = row[4],
                    count_date = row[5],
                    difference = row[6]
                )
