from django.contrib.auth.models import User
from django.core.management.base import BaseCommand
from django.conf import settings


class Command(BaseCommand):

    def handle(self, *args, **options):
        if User.objects.count() == 0:
            User.objects.create_superuser("admin", "pmedlin@kinpakinc.com", "blend2021")
        else:
            print('Oopsy woopsy')