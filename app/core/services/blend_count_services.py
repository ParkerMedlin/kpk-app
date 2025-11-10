"""Business logic for upcoming blend count views."""

from typing import Iterable, List, Optional

from core.selectors.blend_count_selectors import (
    get_blend_shortage_map,
    get_upcoming_blend_usage,
)
from core.selectors.inventory_selectors import (
    get_latest_count_dates,
    get_latest_transaction_dates,
)

NEEDS_COUNT_TRANSACTION_CODES = {"II", "IA", "IZ"}


def build_upcoming_blend_runs(
    min_hour: int = 8,
    max_hour: int = 30,
    excluded_lines: Optional[Iterable[str]] = None,
    count_table: str = "core_blendcountrecord",
) -> List[dict]:
    """Return fully hydrated upcoming blend runs ready for rendering."""
    upcoming_run_qs = list(get_upcoming_blend_usage(min_hour, max_hour, excluded_lines))

    if not upcoming_run_qs:
        return []

    # Preserve the ordering from the queryset (start_time ascending) while dropping duplicates.
    component_item_codes = []
    seen_codes = set()
    for component_code in (run.component_item_code for run in upcoming_run_qs):
        if component_code in seen_codes:
            continue
        seen_codes.add(component_code)
        component_item_codes.append(component_code)

    if not component_item_codes:
        return []

    latest_transactions_dict = get_latest_transaction_dates(component_item_codes)
    latest_counts_dict = get_latest_count_dates(component_item_codes, count_table)
    shortage_map = get_blend_shortage_map()

    upcoming_runs = []
    seen = set()

    for run in upcoming_run_qs:
        item_code = run.component_item_code

        if item_code in seen:
            continue
        seen.add(item_code)

        last_count_date, last_count_quantity = latest_counts_dict.get(item_code, (None, None))
        last_transaction_date, last_transaction_code = latest_transactions_dict.get(
            item_code, (None, None)
        )

        run_dict = {
            "item_code": item_code,
            "item_description": run.component_item_description,
            "expected_quantity": run.component_on_hand_qty,
            "start_time": run.start_time,
            "prod_line": run.prod_line,
            "last_count_date": last_count_date if last_count_date is not None else "",
            "last_count_quantity": (
                last_count_quantity if last_count_quantity is not None else ""
            ),
            "last_transaction_date": (
                last_transaction_date if last_transaction_date is not None else ""
            ),
            "last_transaction_code": (
                last_transaction_code if last_transaction_code is not None else ""
            ),
        }

        if item_code in shortage_map:
            run_dict["shortage"] = True
            run_dict["shortage_hour"] = shortage_map[item_code]
        else:
            run_dict["shortage"] = False

        needs_count = determine_needs_count(
            last_transaction_date, last_transaction_code, last_count_date
        )
        if needs_count is not None:
            run_dict["needs_count"] = needs_count

        upcoming_runs.append(run_dict)

    return upcoming_runs


def determine_needs_count(
    last_transaction_date, last_transaction_code, last_count_date
) -> Optional[bool]:
    """
    Decide whether the blend requires a new count.

    Returns:
        True if a post-count transaction occurred, False if a stock adjustment made the
        count current, None if insufficient data to decide.
    """
    if not last_transaction_date or not last_count_date:
        return None

    if (
        last_transaction_date < last_count_date
        and last_transaction_code in NEEDS_COUNT_TRANSACTION_CODES
    ):
        return False

    if last_transaction_date > last_count_date:
        return True

    return None
