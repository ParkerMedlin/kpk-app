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

    logger.info(
        'Manual gauge update requested | tank_id=%s | payload_bytes=%s',
        storage_tank_id,
        len(request.body or b''),
    )

    storage_tank = get_object_or_404(StorageTank, pk=storage_tank_id)
    fields_present = {
        'dead_space': 'dead_space' in payload,
        'full_space': 'full_space' in payload,
    }

    dead_space = None
    full_space = None

    try:
        if fields_present['dead_space']:
            dead_space = _parse_decimal(payload.get('dead_space'))
        if fields_present['full_space']:
            full_space = _parse_decimal(payload.get('full_space'))
    except ValueError as exc:
        logger.warning(
            'Manual gauge update rejected | tank_label=%s | reason=%s | payload=%s',
            storage_tank.tank_label_kpk,
            exc,
            payload,
        )
        return JsonResponse({'status': 'error', 'error': str(exc)}, status=400)

    max_inches = storage_tank.max_inches
    if max_inches is None:
        return JsonResponse({'status': 'error', 'error': 'Storage tank is missing max_inches configuration.'}, status=500)

    max_inches_decimal = Decimal(max_inches)

    def resolve_counterpart(primary_value):
        if primary_value is None:
            return None
        # Always derive the complement server-side to avoid rounding mismatches.
        complement = max_inches_decimal - primary_value
        if complement < 0:
            raise ValueError('Measurement exceeds tank max height.')
        return complement

    try:
        if dead_space is None and full_space is None:
            raise ValueError('At least one measurement value is required.')

        if dead_space is not None:
            full_space = resolve_counterpart(dead_space)

        if full_space is not None:
            dead_space = resolve_counterpart(full_space)
    except ValueError as exc:
        logger.warning(
            'Manual gauge update rejected | tank_label=%s | reason=%s | payload=%s',
            storage_tank.tank_label_kpk,
            exc,
            payload,
        )
        return JsonResponse({'status': 'error', 'error': str(exc)}, status=400)

    try:
        for value, label in ((dead_space, 'Dead space'), (full_space, 'Full space')):
            if value is None:
                continue
            if value < 0:
                raise ValueError(f'{label} must be non-negative.')
            if value > max_inches_decimal:
                raise ValueError(f'{label} cannot exceed tank max height.')
    except ValueError as exc:
        logger.warning(
            'Manual gauge update rejected | tank_label=%s | reason=%s | payload=%s',
            storage_tank.tank_label_kpk,
            exc,
            payload,
        )
        return JsonResponse({'status': 'error', 'error': str(exc)}, status=400)

    user = getattr(request, 'user', None)
    recorded_by = ''
    if user and user.is_authenticated:
        recorded_by = user.get_full_name().strip() or user.get_username()

    gauge = ManualGauge.objects.create(
        tank_label_kpk=storage_tank.tank_label_kpk,
        dead_space=dead_space,
        full_space=full_space,
        recorded_by=recorded_by,
    )
    logger.info(
        'Manual gauge entry created | tank_label=%s | dead=%s | full=%s | gauge_id=%s | recorded_by=%s',
        storage_tank.tank_label_kpk,
        dead_space,
        full_space,
        gauge.id,
        recorded_by,
    )

    response_payload = _serialize_gauge(gauge, storage_tank)
    logger.info(
        'Manual gauge update response | tank_label=%s | response=%s',
        storage_tank.tank_label_kpk,
        response_payload,
    )
    return JsonResponse({'status': 'success', 'gauge': response_payload})


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
        'created_at': gauge.created_at.isoformat() if gauge.created_at else None,
        'recorded_by': gauge.recorded_by,
    }
