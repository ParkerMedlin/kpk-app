from django.contrib.auth.models import User
from django.core.management import BaseCommand
import os

class Command(BaseCommand):
    def handle(self, *args, **kwargs):
        django_superuser = User.objects.get(username='admin')
        django_superuser.set_password(os.environ['DJANGO_SUPERUSER_PASSWORD'])
        django_superuser.first_name = 'Admin'
        django_superuser.last_name = 'Blending'
        django_superuser.save()