"""Selectors that provide data required by the batch issue sheet view."""

from core.models import ComponentUsage, LotNumRecord


def get_batch_issue_runs(prod_line):
    """
    Return the base queryset of blend component usage rows for issue sheets.

    Args:
        prod_line (str): Specific production line or 'all'

    """
    queryset = (
        ComponentUsage.objects
        .filter(component_item_description__startswith='BLEND')
        .filter(start_time__lte=12)
        .order_by('start_time')
    )

    if prod_line != 'all':
        queryset = queryset.filter(prod_line__iexact=prod_line)

    return queryset


def get_positive_lot_numbers():
    """Return lot-number records that still have positive quantity on hand."""
    return (
        LotNumRecord.objects
        .filter(sage_qty_on_hand__gt=0)
        .order_by('sage_entered_date')
    )
