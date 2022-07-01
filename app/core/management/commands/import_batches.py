import csv
from django.core.management import BaseCommand
from core.models import LotNumRecord
from decimal import Decimal
from datetime import datetime


###-----NECESSARY FUNCTION FOR CONVERTING EXCEL SERIAL DATES TO ACTUAL USABLE FORMAT-----###
# def floatHourToTime(fh):
#     hours, hourSeconds = divmod(fh, 1)
#     minutes, seconds = divmod(hourSeconds * 60, 1)
#     return (
#         int(hours),
#         int(minutes),
#         int(seconds * 60),
#     )
###-----NECESSARY FUNCTION FOR CONVERTING EXCEL SERIAL DATES TO ACTUAL USABLE FORMAT-----###


class Command(BaseCommand):
    help = 'Load a lotnumbers csv file into the database'

    def add_arguments(self, parser):
        parser.add_argument('--path', type=str)

    def handle(self, *args, **kwargs):
        path = kwargs['path']
        with open(path, 'rt') as f:
            reader = csv.reader(f, dialect='excel')
            #skip first two rows which contain useless headers/data
            next(reader)
            next(reader)
            for row in reader:
                #convert null to Decimal(0)
                if row[3]:
                    rowAtThree=Decimal(float(row[3]))
                else:
                    rowAtThree=Decimal(0)

                ###-----NECESSARY FOR CONVERTING EXCEL SERIAL DATES TO ACTUAL USABLE FORMAT-----###
                #convert excel serial to python datetime
                # try:
                    # excel_date = float(row[4])
                    # hour, minute, second = floatHourToTime(excel_date % 1)
                    # py_datetime = datetime.fromordinal(datetime(1900, 1, 1).toordinal() + int(excel_date) - 2)
                    # py_datetime = py_datetime.replace(hour=hour, minute=minute, second=second)
                #skip rows where datetime is null or blank
                # except ValueError:
                    # next(reader)
                # py_datetime=datetime.strptime("2022-6-2", '%Y-%m-%d').date()
                ###-----NECESSARY FOR CONVERTING EXCEL SERIAL DATES TO ACTUAL USABLE FORMAT-----###

                py_datetime = datetime.strptime(row[4].replace('/', '-'), '%m-%d-%Y').date()
                py_datetime_formatted = py_datetime.strftime('%Y-%m-%d')

                LotNumRecord.objects.create(
                    part_number=row[0],
                    description=row[1],
                    lot_number=row[2],
                    quantity=rowAtThree,
                    date=py_datetime_formatted,
                )