from typing import Optional

from django.db.models import QuerySet

from core.models import DischargeTestingRecord


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

