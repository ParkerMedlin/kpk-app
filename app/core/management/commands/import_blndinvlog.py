import csv
from django.core.management import BaseCommand
from core.models import BlendInvLog
from datetime import datetime

def float_hour_to_time(fh):
    hours, hourSeconds = divmod(fh, 1)
    minutes, seconds = divmod(hourSeconds * 60, 1)
    return (
        int(hours),
        int(minutes),
        int(seconds * 60),
    )

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
                py_datetime = datetime.strptime(row[5].replace('/', '-'), '%m-%d-%Y').date()
                py_datetime = py_datetime.strftime('%Y-%m-%d')
                
                imported_count_record = BlendInvLog(
                    blend_pn = row[0],
                    blend_desc = row[1],
                    starttime = row[2],
                    expOH = row[3],
                    count = row[4],
                    count_date = py_datetime,
                    difference = row[6]
                )
                imported_count_record.save()

