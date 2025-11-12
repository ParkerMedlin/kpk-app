"""Selectors that provide data for upcoming blend count views."""

from typing import Dict, Iterable, Optional

from core.models import ComponentShortage, ComponentUsage


def get_upcoming_blend_usage(
    min_hour: int = 8, max_hour: int = 30, excluded_lines: Optional[Iterable[str]] = None
):
    """Return blend component usage rows within the requested time window."""
    queryset = (
        ComponentUsage.objects.filter(component_item_description__startswith="BLEND")
        .filter(start_time__gte=min_hour)
        .filter(start_time__lte=max_hour)
        .order_by("start_time")
    )

    excluded_lines = excluded_lines or ("Hx", "Dm")
    for line in excluded_lines:
        queryset = queryset.exclude(prod_line__iexact=line)

    return queryset


def get_blend_shortage_map() -> Dict[str, int]:
    """Return mapping of blend item codes to shortage start times."""
    shortages = ComponentShortage.objects.filter(
        component_item_description__startswith="BLEND"
    )
    return {shortage.component_item_code: shortage.start_time for shortage in shortages}
