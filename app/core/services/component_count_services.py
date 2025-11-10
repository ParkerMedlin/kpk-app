"""Business logic for upcoming component count view."""

from __future__ import annotations

import base64
from datetime import date as date_cls
from typing import List, Optional, Sequence

from core.selectors.component_count_selectors import (
    get_component_items,
    get_latest_component_adjustments,
    get_latest_component_counts,
)

DEFAULT_COMPONENT_PREFIXES: Sequence[str] = ("CHEM", "DYE", "FRAGRANCE")
DEFAULT_TRANSACTION_CODES: Sequence[str] = ("IA", "II", "IZ", "IP")


def build_upcoming_component_counts(
    *,
    prefixes: Sequence[str] = DEFAULT_COMPONENT_PREFIXES,
    transaction_codes: Sequence[str] = DEFAULT_TRANSACTION_CODES,
) -> List[dict]:
    """
    Prepare UI-ready component records that may require a new count.
    """
    component_items = get_component_items(prefixes)
    if not component_items:
        return []

    item_lookup = {item["itemcode"]: item["itemcodedesc"] for item in component_items}
    adjustments = get_latest_component_adjustments(item_lookup.keys(), transaction_codes)
    if not adjustments:
        return []

    counts = get_latest_component_counts(adjustments.keys())

    upcoming_components: List[dict] = []
    for item_code, adjustment in adjustments.items():
        description = (
            counts.get(item_code, {}).get("item_description") or item_lookup[item_code]
        )
        count_details = counts.get(item_code)

        last_count_date = (
            count_details.get("counted_date") if count_details is not None else None
        )
        last_count_qty = (
            count_details.get("counted_quantity") if count_details is not None else None
        )

        upcoming_components.append(
            {
                "item_code": item_code,
                "encoded_item_code": _encode_item_code(item_code),
                "item_description": description,
                "last_adjustment_date": adjustment.get("transactiondate"),
                "last_adjustment_code": adjustment.get("transactioncode"),
                "last_transaction_qty": adjustment.get("transactionqty"),
                "last_count_date": last_count_date,
                "last_count_qty": last_count_qty,
                "needs_count": _determine_needs_count(
                    adjustment.get("transactiondate"), last_count_date
                ),
            }
        )

    upcoming_components.sort(
        key=lambda item: (
            item["last_adjustment_date"] or date_cls.min,
            item["item_code"],
        ),
        reverse=True,
    )
    return upcoming_components


def _encode_item_code(item_code: str) -> str:
    return base64.b64encode(item_code.encode("utf-8")).decode("utf-8")


def _determine_needs_count(
    last_adjustment_date, last_count_date
) -> Optional[bool]:
    """
    Flag whether the component should be re-counted.
    """
    if not last_adjustment_date:
        return None

    if last_count_date is None:
        return True

    if last_adjustment_date > last_count_date:
        return True

    return False
