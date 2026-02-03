from typing import Dict, List, Optional, Tuple

from django.contrib.auth import get_user_model
from django.db.models import Q, QuerySet

from core.models import BillOfMaterials, CiItem, DischargeTestingRecord

User = get_user_model()


def list_discharge_tests(limit: Optional[int] = 200) -> QuerySet:
    """
    Return recent discharge testing records ordered newest-first.
    Includes related lab_technician and sampling_personnel for display.
    """
    queryset = (
        DischargeTestingRecord.objects.select_related('lab_technician', 'sampling_personnel')
        .order_by('-date', '-id')
    )

    if limit:
        return queryset[:limit]
    return queryset


def get_discharge_test(pk: int) -> DischargeTestingRecord:
    """Fetch a single discharge testing record by primary key."""
    return (
        DischargeTestingRecord.objects.select_related('lab_technician', 'sampling_personnel')
        .get(pk=pk)
    )


def get_sampling_personnel_options() -> List[Tuple[int, str]]:
    """
    Return active users as (id, display_name) tuples, ordered by display name.
    """
    options: List[Tuple[int, str]] = []
    for user in User.objects.filter(
        is_active=True,
        groups__name__in=['blend_crew', 'blending_line_service', 'line_leader', 'lab'],
    ).distinct().only('id', 'first_name', 'last_name', 'username'):
        display_name = user.get_full_name() or user.get_username()
        options.append((user.id, display_name))

    options.sort(key=lambda option: option[1].lower())
    return options


def get_acid_base_material_options(search_term: str, limit: int = 20) -> List[dict]:
    """
    Return CI item options for acid/base materials as value/label dicts.
    """
    queryset = CiItem.objects.filter(
        Q(itemcodedesc__istartswith='BLEND') | Q(itemcodedesc__istartswith='CHEM')
    )

    if search_term:
        queryset = queryset.filter(
            Q(itemcode__icontains=search_term) | Q(itemcodedesc__icontains=search_term)
        )

    items = queryset.order_by('itemcode').values('itemcode', 'itemcodedesc')[:limit]
    return [
        {'value': item['itemcode'], 'label': f"{item['itemcode']}: {item['itemcodedesc']}"}
        for item in items
    ]


def find_ph_active_component(material_code: str) -> Optional[Dict[str, Optional[str]]]:
    """
    Return the pH-active component item code and description for the given material.
    """
    if not material_code:
        return None

    cleaned_code = material_code.strip()
    if not cleaned_code:
        return None

    watch_codes = set(DischargeTestingRecord.PH_ACTIVE_WATCH_CODES)
    matched_code = None
    if cleaned_code in watch_codes:
        matched_code = cleaned_code
    else:
        matched_code = (
            BillOfMaterials.objects.filter(
                item_code=cleaned_code,
                component_item_code__in=watch_codes,
            )
            .values_list('component_item_code', flat=True)
            .first()
        )

    if not matched_code:
        return None

    description = (
        CiItem.objects.filter(itemcode=matched_code)
        .values_list('itemcodedesc', flat=True)
        .first()
    )
    return {'code': matched_code, 'description': description}
