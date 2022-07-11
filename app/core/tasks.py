from celery import shared_task
from celery.utils.log import get_task_logger
from django.core.management import call_command
from django.apps import apps
from core.models import Forklift
import os

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "app.settings")

logger = get_task_logger(__name__)

@shared_task
def sample_task():
    qs = Forklift.objects.all()
    qo = qs.first()
    logger.info("The sample task just ran." + qo.unit_number)

@shared_task
def hello():
    print('Hello there!')