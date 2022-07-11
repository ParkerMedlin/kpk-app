from django.contrib.auth.models import User
from django.core.management import BaseCommand
import os

class Command(BaseCommand):
    def handle(self, *args, **kwargs):
        u = User.objects.get(username='admin')
        u.set_password(os.environ['DJANGO_SUPERUSER_PASSWORD'])
        u.first_name = 'Admin'
        u.last_name = 'Blending'
        u.save()