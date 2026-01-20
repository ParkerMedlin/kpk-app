from typing import List, Optional

from django.db.models import QuerySet

from core.models import BlendContainerClassification, FlushToteReading


def list_flush_totes(limit: Optional[int] = 200) -> QuerySet:
    """
    Return recent flush tote readings ordered newest-first.
    Includes related lab_technician and line_personnel for display.
    """
    queryset = (
        FlushToteReading.objects.select_related('lab_technician', 'line_personnel')
        .order_by('-date', '-id')
    )

    if limit:
        return queryset[:limit]
    return queryset


def get_flush_tote(pk: int) -> FlushToteReading:
    """Fetch a single flush tote reading by primary key."""
    return (
        FlushToteReading.objects.select_related('lab_technician', 'line_personnel')
        .get(pk=pk)
    )


def get_flush_type_options() -> List[str]:
    """
    Return distinct non-empty flush tote type values sourced
    from BlendContainerClassification.flush_tote.
    """
    return list(
        BlendContainerClassification.objects.exclude(flush_tote__isnull=True)
        .exclude(flush_tote__exact='')
        .values_list('flush_tote', flat=True)
        .distinct()
        .order_by('flush_tote')
    )
