from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from core.models import DeskLaborRate
from decimal import Decimal


DESKS = [
    'Desk_1',
    'Desk_2',
    'LET_Desk',
    'Hx',
    'Dm',
    'Totes',
]


class Command(BaseCommand):
    help = "Seed the DeskLaborRate table with known desks if they don't already exist."

    def add_arguments(self, parser):
        parser.add_argument(
            '--rate',
            type=str,
            default='0.00',
            help='Default hourly rate to seed for desks that do not yet exist (default: 0.00)',
        )
        parser.add_argument(
            '--username',
            type=str,
            default=None,
            help='Optional username to record as updated_by for new rows.',
        )

    def handle(self, *args, **options):
        default_rate_str = options['rate']
        username = options.get('username')

        try:
            default_rate = Decimal(default_rate_str)
        except Exception as exc:
            self.stderr.write(self.style.ERROR(f"Invalid rate '{default_rate_str}': {exc}"))
            return

        user = None
        if username:
            User = get_user_model()
            user = User.objects.filter(username=username).first()
            if not user:
                self.stderr.write(self.style.WARNING(f"Username '{username}' not found; updated_by will be null."))

        created = 0
        for desk in DESKS:
            obj, was_created = DeskLaborRate.objects.get_or_create(
                desk_name=desk,
                defaults={'hourly_rate': default_rate, 'updated_by': user},
            )
            if was_created:
                created += 1
                self.stdout.write(self.style.SUCCESS(f"Created rate for {desk} at {default_rate}"))
        if created == 0:
            self.stdout.write("No new desk rates needed; all desks already present.")
        else:
            self.stdout.write(self.style.SUCCESS(f"Seeded {created} desk labor rate(s)."))
