import csv
from django.core.management import BaseCommand
from core.models import BlendInvLog
from datetime import datetime
from core.models import CountRecord

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
                
                imported_count_record = CountRecord(
                     part_number = row[0],
                    part_description = row[1],
                    expected_quantity = row[3],
                    counted_quantity = row[4],
                    counted_date = py_datetime,
                    variance = row[6]
                )
                imported_count_record.save()

