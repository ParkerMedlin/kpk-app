import logging
from decimal import Decimal, InvalidOperation
from typing import Any, Dict, Iterable, Optional, Union

from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.db import transaction

from app.websockets import base_consumer
from core.models import DischargeTestingRecord
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


def _serialize_discharge_test(tote: DischargeTestingRecord) -> Dict[str, Any]:
    return serialize_for_websocket(
        {
            "id": tote.id,
            "date": tote.date,
            "production_line": tote.production_line,
            "flush_type": tote.flush_type,
            "initial_pH": tote.initial_pH,
            "action_required": tote.action_required,
            "final_pH": tote.final_pH,
            "lab_technician_id": tote.lab_technician_id,
            "lab_technician_name": _user_display(tote.lab_technician),
            "line_personnel_id": tote.line_personnel_id,
            "line_personnel_name": _line_personnel_display(tote),
        }
    )


def _user_display(user: Optional[User]) -> Optional[str]:
    if not user:
        return None
    full_name = user.get_full_name()
    return full_name or user.username


def _line_personnel_display(tote: DischargeTestingRecord) -> Optional[str]:
    line_name = getattr(tote, "line_personnel_name", None)
    if line_name:
        return line_name
    return _user_display(tote.line_personnel)


def _resolve_line_personnel(name: str) -> Optional[User]:
    cleaned = (name or "").strip()
    if not cleaned:
        return None

    user = User.objects.filter(username__iexact=cleaned).first()
    if user:
        return user

    parts = cleaned.split()
    if len(parts) >= 2:
        first_name = parts[0]
        last_name = " ".join(parts[1:])
        user = User.objects.filter(first_name__iexact=first_name, last_name__iexact=last_name).first()
        if user:
            return user

    return User.objects.filter(first_name__iexact=cleaned).first()


def _is_lab_user(user: Optional[User]) -> bool:
    if not user or not getattr(user, "is_authenticated", False):
        return False
    return user.is_staff or user.is_superuser or _user_in_group(user, GROUP_LAB_TECHNICIAN)


def _broadcast_discharge_testing_event(event: str, tote: DischargeTestingRecord) -> None:
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
        "data": base_consumer.sanitize_payload(_serialize_discharge_test(tote)),
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


def create_discharge_test(
    *,
    production_line: str,
    flush_type: str,
    line_personnel_name: Optional[str] = None,
    user: Optional[User] = None,
    initial_pH: Any = None,
    action_required: Optional[str] = None,
    final_pH: Any = None,
) -> DischargeTestingRecord:
    """
    Create a new discharge testing record with optional initial/final pH values.
    Assigns lab_technician to the submitting user and accepts line personnel name input.
    """
    initial_value = _parse_ph(initial_pH, "initial_pH")
    final_value = _parse_ph(final_pH, "final_pH")

    if final_value is not None and initial_value is None:
        raise ValidationError({"final_pH": "Initial pH must be recorded before final pH."})

    cleaned_action = (action_required or "").strip() or None
    line_personnel_user = None
    cleaned_line_personnel = (line_personnel_name or "").strip()

    if not cleaned_line_personnel:
        if _user_in_group(user, GROUP_LINE_PERSONNEL):
            line_personnel_user = user
            cleaned_line_personnel = _user_display(user) or ""
        else:
            raise ValidationError({"line_personnel_name": "Line personnel name is required."})

    status = DischargeTestingRecord.STATUS_PENDING
    if initial_value is not None and not DischargeTestingRecord.is_ph_in_range(initial_value):
        status = DischargeTestingRecord.STATUS_NEEDS_ACTION
    if final_value is not None:
        if (
            initial_value is not None
            and not DischargeTestingRecord.is_ph_in_range(initial_value)
            and not cleaned_action
        ):
            raise ValidationError({"action_required": "Action details are required when initial pH is out of range."})
        if not DischargeTestingRecord.is_ph_in_range(final_value):
            raise ValidationError(
                {"final_pH": f"Final pH must be between {DischargeTestingRecord.PH_MIN} and {DischargeTestingRecord.PH_MAX}."}
            )
        status = DischargeTestingRecord.STATUS_APPROVED

    tote = DischargeTestingRecord(
        production_line=production_line,
        flush_type=flush_type,
        initial_pH=initial_value,
        action_required=cleaned_action,
        final_pH=final_value
    )

    if hasattr(tote, "line_personnel_name") and cleaned_line_personnel:
        tote.line_personnel_name = cleaned_line_personnel

    if line_personnel_user is None and cleaned_line_personnel and not hasattr(tote, "line_personnel_name"):
        line_personnel_user = _resolve_line_personnel(cleaned_line_personnel)
        if line_personnel_user is None:
            raise ValidationError({"line_personnel_name": "Line personnel not found."})

    if line_personnel_user is not None:
        tote.line_personnel = line_personnel_user

    if _is_lab_user(user):
        tote.lab_technician = user

    tote.full_clean()

    with transaction.atomic():
        tote.save()
        transaction.on_commit(lambda: _broadcast_discharge_testing_event("tote_created", tote))
    return tote


def record_discharge_initial_ph(
    tote: Union[int, DischargeTestingRecord],
    *,
    ph_value: Any,
    user: Optional[User] = None,
) -> DischargeTestingRecord:
    """
    Record the initial pH measurement.
    Sets status to needs_action when out of range; otherwise keeps/returns pending.
    """
    instance = _resolve_discharge_test(tote)
    initial_value = _parse_ph(ph_value, "initial_pH")
    if initial_value is None:
        raise ValidationError({"initial_pH": "Initial pH is required."})

    instance.initial_pH = initial_value

    if _is_lab_user(user):
        instance.lab_technician = user

    instance.full_clean()

    with transaction.atomic():
        instance.save(update_fields=[
            "initial_pH",
            "lab_technician",
            "line_personnel",
        ])
        transaction.on_commit(lambda: _broadcast_discharge_testing_event("initial_ph_recorded", instance))
    return instance


def record_discharge_action_and_final_ph(
    tote: Union[int, DischargeTestingRecord],
    *,
    action_text: Optional[str],
    final_ph: Any,
    user: Optional[User] = None,
) -> DischargeTestingRecord:
    """
    Record corrective action (if needed) and the final pH.
    Requires an initial pH to exist; final pH must be within allowed range.
    Approves the tote when final pH is compliant.
    """
    instance = _resolve_discharge_test(tote)
    if instance.initial_pH is None:
        raise ValidationError({"final_pH": "Initial pH must be recorded before final pH."})

    final_value = _parse_ph(final_ph, "final_pH")
    if final_value is None:
        raise ValidationError({"final_pH": "Final pH is required."})

    if not DischargeTestingRecord.is_ph_in_range(final_value):
        raise ValidationError(
            {"final_pH": f"Final pH must be between {DischargeTestingRecord.PH_MIN} and {DischargeTestingRecord.PH_MAX}."}
        )

    cleaned_action = (action_text or "").strip()
    initial_out_of_range = not DischargeTestingRecord.is_ph_in_range(instance.initial_pH)
    if initial_out_of_range and not (cleaned_action or instance.action_required):
        raise ValidationError({"action_required": "Action details are required when initial pH is out of range."})

    if cleaned_action:
        instance.action_required = cleaned_action
    instance.final_pH = final_value

    if _is_lab_user(user):
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
        transaction.on_commit(lambda: _broadcast_discharge_testing_event("final_ph_recorded", instance))
    return instance


def _resolve_discharge_test(tote: Union[int, DischargeTestingRecord]) -> DischargeTestingRecord:
    if isinstance(tote, DischargeTestingRecord):
        return tote
    try:
        return DischargeTestingRecord.objects.get(pk=tote)
    except DischargeTestingRecord.DoesNotExist as exc:
        raise ValidationError({"id": "Flush tote not found."}) from exc
