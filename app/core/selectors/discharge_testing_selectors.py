from typing import List, Optional, Tuple

from django.contrib.auth import get_user_model
from django.db.models import QuerySet

from core.models import DischargeTestingRecord

User = get_user_model()


def list_discharge_tests(limit: Optional[int] = 200) -> QuerySet:
    """
    Return recent discharge testing records ordered newest-first.
    Includes related lab_technician and sampling_personnel for display.
    """
    queryset = (
        DischargeTestingRecord.objects.select_related('lab_technician', 'sampling_personnel')
        .order_by('-date', '-id')
    )

    if limit:
        return queryset[:limit]
    return queryset


def get_discharge_test(pk: int) -> DischargeTestingRecord:
    """Fetch a single discharge testing record by primary key."""
    return (
        DischargeTestingRecord.objects.select_related('lab_technician', 'sampling_personnel')
        .get(pk=pk)
    )


def get_sampling_personnel_options() -> List[Tuple[int, str]]:
    """
    Return active users as (id, display_name) tuples, ordered by display name.
    """
    options: List[Tuple[int, str]] = []
    for user in User.objects.filter(is_active=True).only('id', 'first_name', 'last_name', 'username'):
        display_name = user.get_full_name() or user.get_username()
        options.append((user.id, display_name))

    options.sort(key=lambda option: option[1].lower())
    return options
