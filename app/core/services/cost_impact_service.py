"""
Cost Impact Analysis Service

Analyzes how raw material price changes impact BLEND items and finished goods.
Compares current vs next costs from purchasing workbook and traces impacts through BOMs.
"""

from __future__ import annotations

import logging
from decimal import Decimal, InvalidOperation
from typing import Dict, List, Optional, Tuple
from collections import defaultdict

from django.db.models import Q, F, DecimalField, ExpressionWrapper

from core.models import (
    BillOfMaterials,
    CiItem,
    SoSalesOrderDetail,
)
from core.services.bom_costing_service import BomCostingService

LOGGER = logging.getLogger(__name__)


class CostImpactResult:
    """Represents the cost impact analysis results."""

    def __init__(self):
        self.raw_material_changes: List[Dict] = []
        self.affected_blends: List[Dict] = []
        self.affected_finished_goods: List[Dict] = []
        self.sales_order_impacts: List[Dict] = []
        self.summary: Dict = {}


def parse_cost_changes_from_workbook(
    purchasing_costs: Dict[str, Dict[str, Decimal]],
    min_change_threshold: Decimal = Decimal('0.01')
) -> List[Dict]:
    """
    Extract items with price changes from purchasing costs workbook.

    Args:
        purchasing_costs: Dict mapping item_code to {'est_landed': Decimal, 'next_cost': Decimal}
        min_change_threshold: Minimum cost change to include (default $0.01)

    Returns:
        List of items with cost changes, each containing:
        - item_code
        - item_description
        - current_cost (est_landed)
        - next_cost
        - delta
        - pct_change
    """
    cost_changes = []

    for item_code, costs in purchasing_costs.items():
        est_landed = costs.get('est_landed', Decimal('0'))
        next_cost = costs.get('next_cost', Decimal('0'))

        # Skip if either cost is missing or zero
        if est_landed <= 0 or next_cost <= 0:
            continue

        # Calculate delta
        delta = next_cost - est_landed

        # Skip if change is below threshold
        if abs(delta) < min_change_threshold:
            continue

        # Calculate percentage change
        pct_change = (delta / est_landed * 100) if est_landed > 0 else Decimal('0')

        cost_changes.append({
            'item_code': item_code,
            'item_description': '',  # Will be filled in below
            'current_cost': est_landed,
            'next_cost': next_cost,
            'delta': delta,
            'pct_change': pct_change,
        })

    # Look up item descriptions from CiItem
    if cost_changes:
        item_codes = [item['item_code'] for item in cost_changes]
        ci_items = CiItem.objects.filter(itemcode__in=item_codes).values('itemcode', 'itemcodedesc')
        desc_map = {item['itemcode']: item['itemcodedesc'] for item in ci_items}

        for item in cost_changes:
            item['item_description'] = desc_map.get(item['item_code'], '')

    # Sort by absolute delta (largest changes first)
    cost_changes.sort(key=lambda x: abs(x['delta']), reverse=True)

    return cost_changes


def trace_blend_impacts(
    changed_items: List[Dict],
    warehouse: str = "MTG"
) -> List[Dict]:
    """
    Trace which BLEND items are affected by raw material cost changes.

    Args:
        changed_items: List of dicts with item_code, current_cost, next_cost
        warehouse: Warehouse code for inventory checks

    Returns:
        List of affected BLEND items with cost deltas
    """
    if not changed_items:
        return []

    changed_item_codes = {item['item_code'] for item in changed_items}

    # Find all BLEND items that use the changed raw materials as components
    blend_boms = BillOfMaterials.objects.filter(
        component_item_code__in=changed_item_codes,
        item_description__istartswith='BLEND'
    ).values(
        'item_code',
        'item_description',
        'component_item_code',
        'qtyperbill',
        'standard_uom',
    )

    # Group by BLEND item
    blends_dict = defaultdict(list)
    for bom in blend_boms:
        bill_code = bom['item_code']
        blends_dict[bill_code].append(bom)

    affected_blends = []

    # Calculate cost delta for each BLEND
    for blend_code, components in blends_dict.items():
        blend_desc = components[0]['item_description'] if components else ''

        # Calculate the total cost increase for this BLEND
        total_current_cost = Decimal('0')
        total_next_cost = Decimal('0')
        changed_components = []

        for comp in components:
            comp_code = comp['component_item_code']
            qty_per_bill = Decimal(str(comp['qtyperbill'] or 0))

            # Find the cost change for this component
            cost_change = next(
                (item for item in changed_items if item['item_code'] == comp_code),
                None
            )

            if cost_change:
                current = Decimal(str(cost_change['current_cost']))
                next_cost = Decimal(str(cost_change['next_cost']))

                total_current_cost += current * qty_per_bill
                total_next_cost += next_cost * qty_per_bill

                changed_components.append({
                    'component_code': comp_code,
                    'qty_per_bill': float(qty_per_bill),
                    'current_cost': float(current),
                    'next_cost': float(next_cost),
                    'delta': float(next_cost - current),
                })

        cost_delta = total_next_cost - total_current_cost

        if cost_delta != 0:
            affected_blends.append({
                'item_code': blend_code,  # Use item_code for consistency with finished goods
                'blend_code': blend_code,
                'blend_description': blend_desc,
                'current_cost': float(total_current_cost),
                'next_cost': float(total_next_cost),
                'cost_delta': float(cost_delta),
                'pct_change': float((cost_delta / total_current_cost * 100) if total_current_cost > 0 else 0),
                'changed_components': changed_components,
            })

    return affected_blends


def trace_direct_raw_material_impacts(
    changed_items: List[Dict],
    warehouse: str = "MTG"
) -> List[Dict]:
    """
    Trace which finished goods are DIRECTLY affected by raw material changes (not through BLENDs).

    Args:
        changed_items: List of dicts with item_code, current_cost, next_cost, delta
        warehouse: Warehouse code

    Returns:
        List of finished goods with direct raw material cost impacts
    """
    if not changed_items:
        return []

    changed_item_codes = {item['item_code'] for item in changed_items}

    # Find finished goods that DIRECTLY use these raw materials
    fg_boms = BillOfMaterials.objects.filter(
        component_item_code__in=changed_item_codes
    ).exclude(
        item_description__istartswith='BLEND'
    ).values(
        'item_code',
        'item_description',
        'component_item_code',
        'qtyperbill',
    )

    # Group by finished good
    fg_dict = defaultdict(list)
    for bom in fg_boms:
        fg_code = bom['item_code']
        fg_dict[fg_code].append(bom)

    finished_goods = []

    for fg_code, components in fg_dict.items():
        fg_desc = components[0]['item_description'] if components else ''

        total_cost_delta = Decimal('0')
        affected_raw_components = []

        for comp in components:
            comp_code = comp['component_item_code']
            qty_per_bill = Decimal(str(comp['qtyperbill'] or 0))

            # Find the cost change for this component
            cost_change = next(
                (item for item in changed_items if item['item_code'] == comp_code),
                None
            )

            if cost_change:
                delta = Decimal(str(cost_change['delta']))
                total_cost_delta += delta * qty_per_bill

                affected_raw_components.append({
                    'component_code': comp_code,
                    'component_description': cost_change.get('item_description', ''),
                    'qty_per_bill': float(qty_per_bill),
                    'current_cost': float(cost_change['current_cost']),
                    'next_cost': float(cost_change['next_cost']),
                    'delta': float(delta),
                    'extended_delta': float(delta * qty_per_bill),
                })

        if total_cost_delta != 0:
            finished_goods.append({
                'item_code': fg_code,
                'item_description': fg_desc,
                'cost_delta': float(total_cost_delta),
                'affected_raw_materials': affected_raw_components,
            })

    return finished_goods


def trace_finished_goods_impacts(
    affected_blends: List[Dict],
    warehouse: str = "MTG"
) -> List[Dict]:
    """
    Trace which finished goods are affected by BLEND cost changes.

    Args:
        affected_blends: List of affected BLEND items with cost deltas
        warehouse: Warehouse code

    Returns:
        List of finished goods with cost impacts
    """
    if not affected_blends:
        return []

    blend_codes = {blend['blend_code'] for blend in affected_blends}

    # Find finished goods that use these BLENDs
    fg_boms = BillOfMaterials.objects.filter(
        component_item_code__in=blend_codes
    ).exclude(
        item_description__istartswith='BLEND'
    ).values(
        'item_code',
        'item_description',
        'component_item_code',
        'qtyperbill',
    )

    # Group by finished good
    fg_dict = defaultdict(list)
    for bom in fg_boms:
        fg_code = bom['item_code']
        fg_dict[fg_code].append(bom)

    finished_goods = []

    for fg_code, components in fg_dict.items():
        fg_desc = components[0]['item_description'] if components else ''

        total_cost_delta = Decimal('0')
        affected_blend_components = []

        for comp in components:
            comp_code = comp['component_item_code']
            qty_per_bill = Decimal(str(comp['qtyperbill'] or 0))

            blend_impact = next(
                (blend for blend in affected_blends if blend['blend_code'] == comp_code),
                None
            )

            if blend_impact:
                blend_delta = Decimal(str(blend_impact['cost_delta']))
                total_cost_delta += blend_delta * qty_per_bill

                affected_blend_components.append({
                    'blend_code': comp_code,
                    'blend_description': blend_impact['blend_description'],
                    'qty_per_bill': float(qty_per_bill),
                    'blend_cost_delta': float(blend_delta),
                    'extended_delta': float(blend_delta * qty_per_bill),
                })

        if total_cost_delta != 0:
            finished_goods.append({
                'item_code': fg_code,
                'item_description': fg_desc,
                'cost_delta': float(total_cost_delta),
                'affected_blends': affected_blend_components,
            })

    return finished_goods


def calculate_sales_order_impacts(
    affected_items: List[Dict],
    warehouse: str = "MTG",
    limit: int = 500
) -> List[Dict]:
    """
    Calculate margin impacts on open sales orders for affected items.

    Args:
        affected_items: List of finished goods and BLENDs with cost deltas
        warehouse: Warehouse code
        limit: Maximum number of orders to analyze

    Returns:
        List of sales orders with margin impacts
    """
    if not affected_items:
        return []

    affected_codes = {item['item_code'] for item in affected_items}

    # Build cost delta lookup
    cost_delta_map = {
        item['item_code']: Decimal(str(item['cost_delta']))
        for item in affected_items
    }

    # Find open sales orders for affected items
    open_qty_expr = ExpressionWrapper(
        F('quantityordered') - F('quantityshipped'),
        output_field=DecimalField(max_digits=20, decimal_places=6)
    )

    orders_qs = SoSalesOrderDetail.objects.filter(
        itemcode__in=affected_codes,
        itemtype__iexact='1'
    ).annotate(
        open_qty=open_qty_expr
    ).filter(
        open_qty__gt=Decimal('0')
    )

    if warehouse != 'ALL':
        orders_qs = orders_qs.filter(warehousecode__iexact=warehouse)

    orders_qs = orders_qs.order_by('promisedate', 'salesorderno')[:limit]

    order_values = orders_qs.values(
        'salesorderno',
        'linekey',
        'itemcode',
        'itemcodedesc',
        'promisedate',
        'unitprice',
        'open_qty',
    )

    sales_order_impacts = []

    for order in order_values:
        item_code = order['itemcode']
        open_qty = Decimal(str(order['open_qty'] or 0))
        unit_price = Decimal(str(order['unitprice'] or 0))

        cost_delta = cost_delta_map.get(item_code, Decimal('0'))
        total_cost_impact = cost_delta * open_qty

        # Calculate new margin
        revenue = unit_price * open_qty
        margin_impact = -total_cost_impact  # Negative because cost increase reduces margin

        sales_order_impacts.append({
            'sales_order_no': order['salesorderno'],
            'line_key': order['linekey'],
            'item_code': item_code,
            'item_description': order['itemcodedesc'],
            'promise_date': order['promisedate'].isoformat() if order['promisedate'] else None,
            'open_qty': float(open_qty),
            'unit_price': float(unit_price),
            'unit_cost_delta': float(cost_delta),
            'total_cost_impact': float(total_cost_impact),
            'margin_impact': float(margin_impact),
            'revenue': float(revenue),
        })

    return sales_order_impacts


def analyze_cost_impacts(
    purchasing_costs: Dict[str, Dict[str, Decimal]],
    warehouse: str = "MTG",
    limit: int = 500
) -> CostImpactResult:
    """
    Perform full cost impact analysis.

    Args:
        purchasing_costs: Purchasing costs map from workbook
        warehouse: Warehouse code for analysis
        limit: Maximum sales orders to analyze

    Returns:
        CostImpactResult with complete analysis
    """
    result = CostImpactResult()

    # Step 1: Parse cost changes from workbook
    raw_material_changes = parse_cost_changes_from_workbook(purchasing_costs)
    result.raw_material_changes = raw_material_changes

    if not raw_material_changes:
        LOGGER.info("No cost changes detected in workbook")
        result.summary = {
            'total_raw_materials_changed': 0,
            'total_blends_affected': 0,
            'total_finished_goods_affected': 0,
            'total_sales_orders_impacted': 0,
            'total_margin_impact': 0.0,
        }
        return result

    # Step 2: Trace BLEND impacts
    affected_blends = trace_blend_impacts(raw_material_changes, warehouse)
    result.affected_blends = affected_blends

    # Step 3: Trace finished goods impacts (both through BLENDs and direct raw materials)
    fg_from_blends = trace_finished_goods_impacts(affected_blends, warehouse)
    fg_from_raw_materials = trace_direct_raw_material_impacts(raw_material_changes, warehouse)

    # Merge finished goods impacts (combine if same item has both types of impacts)
    merged_fg = {}
    for fg in fg_from_blends:
        code = fg['item_code']
        merged_fg[code] = {
            'item_code': code,
            'item_description': fg['item_description'],
            'cost_delta': fg['cost_delta'],
            'affected_blends': fg.get('affected_blends', []),
            'affected_raw_materials': [],
        }

    for fg in fg_from_raw_materials:
        code = fg['item_code']
        if code in merged_fg:
            # Merge with existing entry
            merged_fg[code]['cost_delta'] += fg['cost_delta']
            merged_fg[code]['affected_raw_materials'] = fg.get('affected_raw_materials', [])
        else:
            # New entry
            merged_fg[code] = {
                'item_code': code,
                'item_description': fg['item_description'],
                'cost_delta': fg['cost_delta'],
                'affected_blends': [],
                'affected_raw_materials': fg.get('affected_raw_materials', []),
            }

    affected_finished_goods = list(merged_fg.values())
    result.affected_finished_goods = affected_finished_goods

    # Step 4: Calculate sales order impacts
    # Combine both BLENDs and finished goods for sales order analysis
    all_affected_items = affected_blends + affected_finished_goods
    sales_order_impacts = calculate_sales_order_impacts(all_affected_items, warehouse, limit)
    result.sales_order_impacts = sales_order_impacts

    # Calculate summary
    total_margin_impact = sum(
        order.get('margin_impact', 0)
        for order in sales_order_impacts
    )

    result.summary = {
        'total_raw_materials_changed': len(raw_material_changes),
        'total_blends_affected': len(affected_blends),
        'total_finished_goods_affected': len(affected_finished_goods),
        'total_sales_orders_impacted': len(sales_order_impacts),
        'total_margin_impact': float(total_margin_impact),
    }

    return result
