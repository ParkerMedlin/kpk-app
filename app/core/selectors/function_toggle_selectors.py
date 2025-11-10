from core.models import FunctionToggle


def get_all_function_toggles():
    """Return all function toggles ordered by name."""
    return FunctionToggle.objects.order_by('function_name')


def get_function_toggle_status(function_name: str) -> str:
    """Return toggle status for a function; default to 'on' when missing."""
    normalized_name = (function_name or '').strip()
    if not normalized_name:
        return FunctionToggle.STATUS_ON

    try:
        toggle = FunctionToggle.objects.get(function_name=normalized_name)
        return toggle.status
    except FunctionToggle.DoesNotExist:
        return FunctionToggle.STATUS_ON
