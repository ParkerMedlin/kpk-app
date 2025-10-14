from core.models import PurchasingAlias
from core.forms import PurchasingAliasForm
from django.shortcuts import get_object_or_404
from django.http import JsonResponse
from django.views.decorators.http import require_POST
from django.contrib.auth.decorators import login_required
import json
from django.utils import timezone
import logging

logger = logging.getLogger(__name__)

@login_required
@require_POST
def update_purchasing_alias_audit(request):
    """Mark a purchasing alias as audited for the current date."""

    try:
        payload = json.loads(request.body.decode('utf-8'))
    except (json.JSONDecodeError, UnicodeDecodeError):
        return JsonResponse({'status': 'error', 'error': 'Invalid JSON payload.'}, status=400)

    alias_id = payload.get('alias_id')
    if not alias_id:
        return JsonResponse({'status': 'error', 'error': 'Missing alias_id.'}, status=400)

    alias = get_object_or_404(PurchasingAlias, pk=alias_id)
    if not alias.monthly_audit_needed:
        return JsonResponse({'status': 'error', 'error': 'Alias is not configured for monthly audit.'}, status=400)

    is_counted = payload.get('is_counted')
    if is_counted is None:
        is_counted = True

    audit_date = timezone.localdate() if is_counted else None
    alias.last_audit_date = audit_date
    alias.save(update_fields=['last_audit_date', 'updated_at'])

    return JsonResponse(
        {
            'status': 'success',
            'alias_id': alias_id,
            'last_audit_date': audit_date.isoformat() if audit_date else None,
            'last_audit_date_formatted': audit_date.strftime('%Y-%m-%d') if audit_date else None,
            'counted_this_month': bool(audit_date),
        }
    )

@login_required
@require_POST
def update_purchasing_alias(request, alias_id):
    """Persist inline edits to a purchasing alias."""

    alias = get_object_or_404(PurchasingAlias, pk=alias_id)

    try:
        payload = json.loads(request.body.decode('utf-8'))
    except (json.JSONDecodeError, UnicodeDecodeError):
        return JsonResponse({'status': 'error', 'error': 'Invalid JSON payload.'}, status=400)

    logger.info('Purchasing alias update payload received for %s: %s', alias_id, payload)

    merged_data = {}
    for field in PurchasingAliasForm.Meta.fields:
        if field in payload:
            merged_data[field] = payload[field]
        else:
            merged_data[field] = getattr(alias, field)

    logger.info('Merged purchasing alias data for %s: %s', alias_id, merged_data)

    form = PurchasingAliasForm(data=merged_data, instance=alias)
    if not form.is_valid():
        logger.warning('Purchasing alias update validation failed for %s: %s', alias_id, form.errors)
        return JsonResponse({'status': 'error', 'errors': form.errors}, status=400)

    updated_alias = form.save()
    changed_fields = form.changed_data

    logger.info('Purchasing alias %s updated fields: %s', alias_id, changed_fields)

    return JsonResponse(
        {
            'status': 'success',
            'alias_id': alias_id,
            'changed_fields': changed_fields,
            'alias': {
                'vendor': updated_alias.vendor,
                'vendor_part_number': updated_alias.vendor_part_number,
                'vendor_description': updated_alias.vendor_description,
                'link': updated_alias.link,
                'blending_notes': updated_alias.blending_notes,
                'monthly_audit_needed': updated_alias.monthly_audit_needed,
                'last_audit_date': updated_alias.last_audit_date.isoformat() if updated_alias.last_audit_date else None,
                'updated_at': updated_alias.updated_at.isoformat() if updated_alias.updated_at else None,
            },
        }
    )

@login_required
@require_POST
def create_purchasing_alias(request):
    """Create a placeholder purchasing alias record for inline editing."""

    try:
        payload = json.loads(request.body.decode('utf-8')) if request.body else {}
    except (json.JSONDecodeError, UnicodeDecodeError):
        return JsonResponse({'status': 'error', 'error': 'Invalid JSON payload.'}, status=400)

    payload.setdefault('monthly_audit_needed', False)

    form = PurchasingAliasForm(data=payload)
    if not form.is_valid():
        logger.warning('Purchasing alias creation failed validation: %s', form.errors)
        return JsonResponse({'status': 'error', 'errors': form.errors}, status=400)

    alias = form.save()

    logger.info('Purchasing alias created with id %s', alias.id)

    return JsonResponse(
        {
            'status': 'success',
            'alias': {
                'id': alias.id,
                'vendor': alias.vendor,
                'vendor_part_number': alias.vendor_part_number,
                'vendor_description': alias.vendor_description,
                'link': alias.link,
                'blending_notes': alias.blending_notes,
                'monthly_audit_needed': alias.monthly_audit_needed,
                'created_at': alias.created_at.isoformat() if alias.created_at else None,
                'updated_at': alias.updated_at.isoformat() if alias.updated_at else None,
            },
        },
        status=201,
    )

@login_required
@require_POST
def delete_purchasing_alias(request, alias_id):
    """Delete a purchasing alias record."""

    alias = get_object_or_404(PurchasingAlias, pk=alias_id)

    alias.delete()

    logger.info('Purchasing alias %s deleted', alias_id)

    return JsonResponse({'status': 'success', 'alias_id': alias_id})