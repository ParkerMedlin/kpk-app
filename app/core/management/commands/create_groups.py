from django.contrib.auth.models import Group
from django.core.management.base import BaseCommand

class Command(BaseCommand):
    def handle(self, **options):
        Group.objects.create(name='front_office')
        Group.objects.create(name='blend_crew')
        Group.objects.create(name='forklift_operator')
        Group.objects.create(name='lab')
