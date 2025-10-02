import base64
import datetime as dt

from django.db.models import OuterRef, Subquery

from core.models import (
    LotNumRecord,
    HxBlendthese,
    DeskOneSchedule,
    DeskTwoSchedule,
    LetDeskSchedule,
    BlendSheetPrintLog,
)
from core.kpkapp_utils.dates import _is_date_string

RELEVANT_LINES = ['Dm', 'Totes', 'Hx']


def _normalize_run_date(value):
    if not _is_date_string(value):
        return None
    if isinstance(value, dt.datetime):
        return value.date()
    return value


def _format_run_date(value):
    if not value:
        return None
    return value.strftime('%Y-%m-%d')


def _format_datetime(value):
    if not value:
        return None
    if isinstance(value, dt.date) and not isinstance(value, dt.datetime):
        return value.strftime('%Y-%m-%d')
    return value.strftime('%Y-%m-%d %H:%M')


def _get_scheduled_lot_numbers():
    schedule_querysets = (
        DeskOneSchedule.objects.exclude(lot__isnull=True).exclude(lot__exact='')
        .values_list('lot', flat=True),
        DeskTwoSchedule.objects.exclude(lot__isnull=True).exclude(lot__exact='')
        .values_list('lot', flat=True),
        LetDeskSchedule.objects.exclude(lot__isnull=True).exclude(lot__exact='')
        .values_list('lot', flat=True),
    )
    return {
        lot
        for queryset in schedule_querysets
        for lot in queryset
        if lot
    }


def _get_hx_match_keys():
    return {
        (
            item_code,
            prod_line,
            _normalize_run_date(run_date),
        )
        for item_code, prod_line, run_date in HxBlendthese.objects.filter(
            prod_line__in=RELEVANT_LINES
        ).values_list('component_item_code', 'prod_line', 'run_date')
        if item_code
    }


def get_orphaned_lots():
    """Return un-entered lot numbers that are not scheduled or matched to HX runs."""

    scheduled_lot_numbers = _get_scheduled_lot_numbers()
    hx_match_keys = _get_hx_match_keys()

    last_printed_subquery = Subquery(
        BlendSheetPrintLog.objects.filter(
            lot_num_record_id=OuterRef('pk')
        )
        .order_by('-printed_at')
        .values('printed_at')[:1]
    )

    orphaned_lots = []
    lots_queryset = (
        LotNumRecord.objects.filter(
            sage_entered_date__isnull=True
        )
        .annotate(last_printed_at=last_printed_subquery)
        .order_by('date_created')
        .values(
            'id',
            'item_code',
            'item_description',
            'line',
            'lot_number',
            'run_date',
            'date_created',
            'last_printed_at',
        )
    )

    for lot in lots_queryset:
        normalized_run_date = _normalize_run_date(lot['run_date'])

        if lot['lot_number'] in scheduled_lot_numbers:
            continue

        if (lot['item_code'], lot['line'], normalized_run_date) in hx_match_keys:
            continue

        date_created = lot['date_created']

        orphaned_lots.append(
            {
                'lot_id': lot['id'],
                'item_code': lot['item_code'],
                'prod_line': lot['line'],
                'item_description': lot['item_description'],
                'lot_number': lot['lot_number'],
                'run_date': _format_run_date(normalized_run_date),
                'date_created': _format_datetime(date_created),
                'encoded_item_code': base64.b64encode(lot['item_code'].encode()).decode()
                if lot['item_code'] else '',
                'last_printed_at': _format_datetime(lot.get('last_printed_at')),
            }
        )

    return orphaned_lots
