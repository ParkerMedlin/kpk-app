import json
import logging
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP

from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.shortcuts import get_object_or_404
from django.views.decorators.http import require_POST

from core.models import ManualGauge, StorageTank

logger = logging.getLogger(__name__)


def _parse_decimal(value):
    if value is None:
        return None

    if isinstance(value, Decimal):
        return value

    if isinstance(value, (int, float)):
        return Decimal(str(value))

    if isinstance(value, str):
        cleaned = value.strip()
        if not cleaned:
            return None
        try:
            return Decimal(cleaned)
        except InvalidOperation as exc:
            raise ValueError(f"Invalid numeric value: {value}") from exc

    raise ValueError("Unsupported value type for decimal conversion.")


def _format_decimal(value, *, decimal_places=5):
    if value is None:
        return None
    quantizer = Decimal('1').scaleb(-decimal_places)
    quantized = value.quantize(quantizer, rounding=ROUND_HALF_UP)
    text = format(quantized.normalize(), 'f')
    if '.' in text:
        text = text.rstrip('0').rstrip('.')
    return text or '0'


@login_required
@require_POST
def update_manual_gauge(request, storage_tank_id):
    """
    Persist manual gauge measurements for a storage tank.

    Accepts JSON payload with optional dead_space and full_space fields.
    Missing companion values will be derived from the tank's max_inches.
    """

    try:
        payload = json.loads(request.body.decode('utf-8')) if request.body else {}
    except (json.JSONDecodeError, UnicodeDecodeError):
        return JsonResponse({'status': 'error', 'error': 'Invalid JSON payload.'}, status=400)

    storage_tank = get_object_or_404(StorageTank, pk=storage_tank_id)
    gauge, _ = ManualGauge.objects.get_or_create(
        tank_label_kpk=storage_tank.tank_label_kpk,
    )

    fields_present = {
        'dead_space': 'dead_space' in payload,
        'full_space': 'full_space' in payload,
    }

    if not any(fields_present.values()):
        return JsonResponse(
            {
                'status': 'success',
                'gauge': _serialize_gauge(gauge, storage_tank),
                'message': 'No fields provided; existing values returned.',
            }
        )

    dead_space = gauge.dead_space
    full_space = gauge.full_space

    try:
        if fields_present['dead_space']:
            dead_space = _parse_decimal(payload.get('dead_space'))
        if fields_present['full_space']:
            full_space = _parse_decimal(payload.get('full_space'))
    except ValueError as exc:
        return JsonResponse({'status': 'error', 'error': str(exc)}, status=400)

    max_inches = storage_tank.max_inches
    if max_inches is None:
        return JsonResponse({'status': 'error', 'error': 'Storage tank is missing max_inches configuration.'}, status=500)

    max_inches_decimal = Decimal(max_inches)

    if dead_space is not None and (not fields_present['full_space'] or full_space is None):
        full_space = max_inches_decimal - dead_space
    elif full_space is not None and (not fields_present['dead_space'] or dead_space is None):
        dead_space = max_inches_decimal - full_space

    if dead_space is None and full_space is not None:
        dead_space = max_inches_decimal - full_space
    if full_space is None and dead_space is not None:
        full_space = max_inches_decimal - dead_space

    if dead_space is not None and full_space is not None:
        tolerance = Decimal('0.0001')
        imbalance = (dead_space + full_space) - max_inches_decimal
        if imbalance.copy_abs() > tolerance:
            return JsonResponse(
                {
                    'status': 'error',
                    'error': 'Dead space and full space do not align with tank max height.',
                },
                status=400,
            )

    for value, label in ((dead_space, 'Dead space'), (full_space, 'Full space')):
        if value is None:
            continue
        if value < 0:
            return JsonResponse({'status': 'error', 'error': f'{label} must be non-negative.'}, status=400)
        if value > max_inches_decimal:
            return JsonResponse({'status': 'error', 'error': f'{label} cannot exceed tank max height.'}, status=400)

    update_fields = []
    if gauge.dead_space != dead_space:
        gauge.dead_space = dead_space
        update_fields.append('dead_space')
    if gauge.full_space != full_space:
        gauge.full_space = full_space
        update_fields.append('full_space')

    if update_fields:
        gauge.save(update_fields=update_fields + ['updated_at'])

    return JsonResponse({'status': 'success', 'gauge': _serialize_gauge(gauge, storage_tank)})


def _serialize_gauge(gauge, storage_tank):
    gallons = None
    full_space = gauge.full_space
    if full_space is not None and storage_tank.gallons_per_inch is not None:
        gallons = Decimal(storage_tank.gallons_per_inch) * Decimal(full_space)

    return {
        'id': gauge.id,
        'tank_label_kpk': gauge.tank_label_kpk,
        'dead_space': _format_decimal(gauge.dead_space),
        'full_space': _format_decimal(gauge.full_space),
        'gallons': _format_decimal(gallons, decimal_places=2) if gallons is not None else None,
        'updated_at': gauge.updated_at.isoformat() if gauge.updated_at else None,
    }
