import logging
from decimal import Decimal, InvalidOperation
from typing import Any, Dict, Iterable, Optional, Union

from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.db import transaction

from app.websockets import base_consumer
from core.models import FlushToteReading
from core.websockets.serializer import serialize_for_websocket

logger = logging.getLogger(__name__)
User = get_user_model()

GROUP_LINE_PERSONNEL = "line personnel"
GROUP_LAB_TECHNICIAN = "lab technician"


def _user_in_group(user: Optional[User], group_name: str) -> bool:
    if not user or not getattr(user, "is_authenticated", False):
        return False
    return user.groups.filter(name__iexact=group_name).exists()


def _parse_ph(value: Any, field_name: str) -> Optional[Decimal]:
    """
    Convert input into a Decimal with two decimal places.

    Raises ValidationError if the value cannot be parsed.
    """
    if value in (None, ""):
        return None
    try:
        parsed = Decimal(str(value)).quantize(Decimal("0.01"))
    except (InvalidOperation, TypeError, ValueError):
        raise ValidationError({field_name: "Enter a valid pH value."})
    return parsed


def _serialize_flush_tote(tote: FlushToteReading) -> Dict[str, Any]:
    return serialize_for_websocket(
        {
            "id": tote.id,
            "date": tote.date,
            "production_line": tote.production_line,
            "flush_type": tote.flush_type,
            "initial_pH": tote.initial_pH,
            "action_required": tote.action_required,
            "final_pH": tote.final_pH,
            "approval_status": tote.approval_status,
            "lab_technician_id": tote.lab_technician_id,
            "lab_technician_name": _user_display(tote.lab_technician),
            "line_personnel_id": tote.line_personnel_id,
            "line_personnel_name": _user_display(tote.line_personnel),
        }
    )


def _user_display(user: Optional[User]) -> Optional[str]:
    if not user:
        return None
    full_name = user.get_full_name()
    return full_name or user.username


def _broadcast_flush_tote_event(event: str, tote: FlushToteReading) -> None:
    """
    Broadcast a flush tote event to shared and per-tote websocket groups.
    """
    channel_layer = get_channel_layer()
    if channel_layer is None:
        logger.warning("Channel layer unavailable; skipping flush tote broadcast")
        return

    payload = {
        "type": "flush_tote_event",
        "event": event,
        "data": base_consumer.sanitize_payload(_serialize_flush_tote(tote)),
    }

    group_names: Iterable[str] = {
        "flush_totes_all",
        f"flush_tote_{tote.pk}",
    }

    for group_name in group_names:
        try:
            async_to_sync(channel_layer.group_send)(group_name, payload)
        except Exception:
            logger.exception("Failed to broadcast flush tote event to %s", group_name)


def create_flush_tote_reading(
    *,
    production_line: str,
    flush_type: str,
    user: Optional[User] = None,
    initial_pH: Any = None,
    action_required: Optional[str] = None,
    final_pH: Any = None,
) -> FlushToteReading:
    """
    Create a new flush tote record with optional initial/final pH values.
    Assigns line_personnel when the creator belongs to the line personnel group.
    """
    initial_value = _parse_ph(initial_pH, "initial_pH")
    final_value = _parse_ph(final_pH, "final_pH")

    if final_value is not None and initial_value is None:
        raise ValidationError({"final_pH": "Initial pH must be recorded before final pH."})

    status = FlushToteReading.STATUS_PENDING
    if initial_value is not None and not FlushToteReading.is_ph_in_range(initial_value):
        status = FlushToteReading.STATUS_NEEDS_ACTION
    if final_value is not None:
        if not FlushToteReading.is_ph_in_range(final_value):
            raise ValidationError(
                {"final_pH": f"Final pH must be between {FlushToteReading.PH_MIN} and {FlushToteReading.PH_MAX}."}
            )
        status = FlushToteReading.STATUS_APPROVED

    tote = FlushToteReading(
        production_line=production_line,
        flush_type=flush_type,
        initial_pH=initial_value,
        action_required=action_required,
        final_pH=final_value,
        approval_status=status,
    )

    if _user_in_group(user, GROUP_LINE_PERSONNEL):
        tote.line_personnel = user
    if initial_value is not None and _user_in_group(user, GROUP_LAB_TECHNICIAN):
        tote.lab_technician = user

    tote.full_clean()

    with transaction.atomic():
        tote.save()
        transaction.on_commit(lambda: _broadcast_flush_tote_event("tote_created", tote))
    return tote


def record_initial_ph(
    tote: Union[int, FlushToteReading],
    *,
    ph_value: Any,
    user: Optional[User] = None,
) -> FlushToteReading:
    """
    Record the initial pH measurement.
    Sets status to needs_action when out of range; otherwise keeps/returns pending.
    """
    instance = _resolve_tote(tote)
    initial_value = _parse_ph(ph_value, "initial_pH")
    if initial_value is None:
        raise ValidationError({"initial_pH": "Initial pH is required."})

    instance.initial_pH = initial_value
    if not FlushToteReading.is_ph_in_range(initial_value):
        instance.approval_status = FlushToteReading.STATUS_NEEDS_ACTION
    elif instance.approval_status != FlushToteReading.STATUS_APPROVED:
        instance.approval_status = FlushToteReading.STATUS_PENDING

    if _user_in_group(user, GROUP_LAB_TECHNICIAN):
        instance.lab_technician = user

    instance.full_clean()

    with transaction.atomic():
        instance.save(update_fields=[
            "initial_pH",
            "approval_status",
            "lab_technician",
            "line_personnel",
        ])
        transaction.on_commit(lambda: _broadcast_flush_tote_event("initial_ph_recorded", instance))
    return instance


def record_action_and_final_ph(
    tote: Union[int, FlushToteReading],
    *,
    action_text: Optional[str],
    final_ph: Any,
    user: Optional[User] = None,
) -> FlushToteReading:
    """
    Record corrective action (if needed) and the final pH.
    Requires an initial pH to exist; final pH must be within allowed range.
    Approves the tote when final pH is compliant.
    """
    instance = _resolve_tote(tote)
    if instance.initial_pH is None:
        raise ValidationError({"final_pH": "Initial pH must be recorded before final pH."})

    final_value = _parse_ph(final_ph, "final_pH")
    if final_value is None:
        raise ValidationError({"final_pH": "Final pH is required."})

    if not FlushToteReading.is_ph_in_range(final_value):
        raise ValidationError(
            {"final_pH": f"Final pH must be between {FlushToteReading.PH_MIN} and {FlushToteReading.PH_MAX}."}
        )

    cleaned_action = (action_text or "").strip()
    initial_out_of_range = not FlushToteReading.is_ph_in_range(instance.initial_pH)
    if initial_out_of_range and not (cleaned_action or instance.action_required):
        raise ValidationError({"action_required": "Action details are required when initial pH is out of range."})

    if cleaned_action:
        instance.action_required = cleaned_action
    instance.final_pH = final_value
    instance.approval_status = FlushToteReading.STATUS_APPROVED

    if _user_in_group(user, GROUP_LAB_TECHNICIAN):
        instance.lab_technician = user

    instance.full_clean()

    with transaction.atomic():
        instance.save(update_fields=[
            "action_required",
            "final_pH",
            "approval_status",
            "lab_technician",
            "line_personnel",
        ])
        transaction.on_commit(lambda: _broadcast_flush_tote_event("final_ph_recorded", instance))
    return instance


def _resolve_tote(tote: Union[int, FlushToteReading]) -> FlushToteReading:
    if isinstance(tote, FlushToteReading):
        return tote
    try:
        return FlushToteReading.objects.get(pk=tote)
    except FlushToteReading.DoesNotExist as exc:
        raise ValidationError({"id": "Flush tote not found."}) from exc
