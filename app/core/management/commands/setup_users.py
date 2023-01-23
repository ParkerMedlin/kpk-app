from django.contrib.auth.models import User
from django.core.management import BaseCommand
import csv

class Command(BaseCommand):
    def handle(self, *args, **kwargs):
        path = kwargs['path']
        with open(path, 'rt') as user_table_file:
            reader = csv.reader(user_table_file, dialect='excel')
            next(reader)
            for row in reader:
                User.objects.create_user(
                    row[0],
                    email = row[1],
                    password = row[2],
                    first_name = row[3],
                    last_name = row[4]
                )