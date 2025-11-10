"""Service helpers for the batch issue table view."""

from collections import defaultdict
import datetime as dt


def resolve_issue_date(issue_date):
    """Resolve 'nextDay' shorthand into a concrete date string."""
    if issue_date != "nextDay":
        return issue_date

    tomorrow = dt.date.today() + dt.timedelta(days=1)
    if tomorrow.weekday() == 4:  # Friday
        target_date = tomorrow + dt.timedelta(days=2)
    else:
        target_date = tomorrow
    return target_date.strftime("%m-%d-%y")


def classify_shortage(after_run_quantity):
    """Return shortage classification for a post-run quantity."""
    if after_run_quantity is None:
        return 'noshortage'
    if after_run_quantity < 0:
        return 'short'
    if after_run_quantity < 25:
        return 'warning'
    return 'noshortage'


def dedupe_runs_by_component_and_line(prod_runs):
    """Yield runs ensuring only one per (component, prod_line) pair."""
    seen = set()
    for run in prod_runs:
        key = (run.component_item_code, run.prod_line)
        if key in seen:
            continue
        seen.add(key)
        yield run


def build_lot_number_lookup(lot_numbers):
    """Map item codes to their lot-number display tuples."""
    lookup = defaultdict(list)
    for lot_record in lot_numbers:
        lookup[lot_record.item_code].append(
            (lot_record.lot_number, f"{lot_record.sage_qty_on_hand} gal")
        )
    return lookup


def lot_numbers_for_run(run, lot_lookup):
    """Return lot-number display list for a specific run."""
    lot_numbers = list(lot_lookup.get(run.component_item_code, []))
    if run.procurement_type != 'M':
        lot_numbers.append(("Purchased", "See QC lab."))
    elif not lot_numbers:  # Manufactured with no lots on hand
        lot_numbers.append(("Unavailable", "Check issue sheet page on tablet."))
    return lot_numbers


def build_run_payload(run, issue_date, lot_lookup):
    """Convert a ComponentUsage instance into the template payload dict."""
    return {
        'component_item_code': run.component_item_code,
        'component_item_description': run.component_item_description,
        'component_on_hand_qty': run.component_on_hand_qty,
        'prod_line': run.prod_line,
        'issue_date': issue_date,
        'shortage_flag': classify_shortage(run.component_onhand_after_run),
        'lot_numbers': lot_numbers_for_run(run, lot_lookup),
    }


def group_runs_by_line(runs):
    """Build the prod-line structure expected by the template."""
    line_mappings = [
        ('INLINE', 'INLINE'),
        ('PD LINE', 'PD LINE'),
        ('JB LINE', 'JB LINE'),
    ]
    return [
        {'prod_line': label, 'run_list': [run for run in runs if run['prod_line'] == filter_value]}
        for label, filter_value in line_mappings
    ]


def build_batch_issue_data(prod_runs, lot_numbers, issue_date):
    """
    Assemble context data for the batch issue table.

    Returns:
        tuple(list, list): runs_this_line, prod_runs_by_line
    """
    lot_lookup = build_lot_number_lookup(lot_numbers)

    runs_this_line = [
        build_run_payload(run, issue_date, lot_lookup)
        for run in dedupe_runs_by_component_and_line(prod_runs)
    ]

    prod_runs_by_line = group_runs_by_line(runs_this_line)
    return runs_this_line, prod_runs_by_line
