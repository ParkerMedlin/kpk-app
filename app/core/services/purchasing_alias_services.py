import logging
from collections.abc import Mapping
from typing import Any, Optional

from core.models import PurchasingAlias

logger = logging.getLogger(__name__)

_VALID_SUPPLY_TYPES = {choice[0] for choice in PurchasingAlias.SUPPLY_TYPE_CHOICES}


def normalize_supply_type(value: Any, *, default: Optional[str] = None) -> Optional[str]:
    """
    Normalize arbitrary supply type input into one of the valid choices.
    Falls back to ``default`` when the value is missing or invalid.
    """
    if value is None:
        return default

    normalized = str(value).strip().upper()
    if not normalized:
        return default

    if normalized in _VALID_SUPPLY_TYPES:
        return normalized

    logger.warning("Invalid supply_type received: %s", value)
    return default


def extract_supply_type(request, payload: Optional[Mapping[str, Any]] = None, *, default: Optional[str] = None) -> Optional[str]:
    """
    Retrieve a valid supply type from request GET params or a JSON payload.
    Preference order: request -> payload -> default.
    """
    payload = payload or {}

    request_value = request.GET.get('supply_type') if hasattr(request, 'GET') else None
    normalized_request = normalize_supply_type(request_value)
    if normalized_request:
        return normalized_request

    payload_value = payload.get('supply_type') if isinstance(payload, Mapping) else None
    normalized_payload = normalize_supply_type(payload_value)
    if normalized_payload:
        return normalized_payload

    return default


__all__ = ['normalize_supply_type', 'extract_supply_type']
