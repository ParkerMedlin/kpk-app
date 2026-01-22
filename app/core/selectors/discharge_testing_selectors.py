from typing import List, Optional

from django.db.models import QuerySet

from core.models import BlendContainerClassification, DischargeTestingRecord


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


def get_discharge_type_options() -> List[str]:
    """
    Return distinct non-empty discharge type values sourced
    from BlendContainerClassification.flush_tote.
    """
    return list(
        BlendContainerClassification.objects.exclude(flush_tote__isnull=True)
        .exclude(flush_tote__exact='')
        .values_list('flush_tote', flat=True)
        .distinct()
        .order_by('flush_tote')
    )
