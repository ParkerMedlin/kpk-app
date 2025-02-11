from django.contrib.auth.models import User
from django.core.management.base import BaseCommand
from django.conf import settings
import os


class Command(BaseCommand):

    def handle(self, *args, **options):
        if User.objects.count() == 0:
            User.objects.create_superuser(os.environ['DJANGO_SUPERUSER_USERNAME'], "pmedlin@kinpakinc.com", os.environ['DJANGO_SUPERUSER_PASSWORD'])
        else:
            print('Oopsy woopsy')