"""Selectors for retrieving component count data."""

from typing import Dict, Iterable, List, Sequence

from django.db.models import Q

from core.models import BlendComponentCountRecord, CiItem, ImItemTransactionHistory

ComponentItem = Dict[str, str]
TransactionDetails = Dict[str, object]
CountDetails = Dict[str, object]


def get_component_items(
    prefixes: Sequence[str] = ("CHEM", "DYE", "FRAGRANCE"),
) -> List[ComponentItem]:
    """
    Return component itemcodes/descriptions filtered by the provided prefixes.
    """
    if not prefixes:
        return []

    prefix_filter = Q()
    for prefix in prefixes:
        prefix_filter |= Q(itemcodedesc__startswith=prefix)

    return list(
        CiItem.objects.filter(prefix_filter)
        .values("itemcode", "itemcodedesc")
        .order_by("itemcode")
    )


def get_latest_component_adjustments(
    item_codes: Iterable[str],
    transaction_codes: Sequence[str] = ("IA", "II", "IZ", "IP"),
) -> Dict[str, TransactionDetails]:
    """
    Return the latest qualifying adjustment per component item.
    """
    item_codes = list(item_codes)
    if not item_codes:
        return {}

    adjustments = (
        ImItemTransactionHistory.objects.filter(
            itemcode__in=item_codes, transactioncode__in=transaction_codes
        )
        .order_by("itemcode", "-transactiondate", "-id")
    )

    latest_adjustments: Dict[str, TransactionDetails] = {}
    for adjustment in adjustments:
        item_code = adjustment.itemcode
        if item_code in latest_adjustments:
            continue

        latest_adjustments[item_code] = {
            "transactiondate": adjustment.transactiondate,
            "transactioncode": adjustment.transactioncode,
            "transactionqty": adjustment.transactionqty,
        }

    return latest_adjustments


def get_latest_component_counts(
    item_codes: Iterable[str],
) -> Dict[str, CountDetails]:
    """
    Return the latest counted record per component item (counted=True only).
    """
    item_codes = list(item_codes)
    if not item_codes:
        return {}

    counts = (
        BlendComponentCountRecord.objects.filter(
            item_code__in=item_codes, counted=True
        )
        .order_by("item_code", "-counted_date", "-id")
    )

    latest_counts: Dict[str, CountDetails] = {}
    for count in counts:
        item_code = count.item_code
        if item_code in latest_counts:
            continue

        latest_counts[item_code] = {
            "counted_date": count.counted_date,
            "counted_quantity": count.counted_quantity,
            "item_description": count.item_description,
        }

    return latest_counts
