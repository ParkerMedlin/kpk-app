from __future__ import annotations
import copy
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import date
from decimal import Decimal, InvalidOperation
from typing import Dict, Iterable, List, Optional, Set, Tuple

from django.db.models import F, DecimalField, ExpressionWrapper

from core.models import BmBillDetail, CiItem, ImItemCost, SoSalesOrderDetail


class BomCostingError(Exception):
    """Base class for costing related exceptions."""


class ItemNotFoundError(BomCostingError):
    """Raised when the requested item does not exist in CI_Item."""


class CircularBomReferenceError(BomCostingError):
    """Raised when a circular reference is detected while traversing a BOM."""


@dataclass
class CostRow:
    level: int
    item_code: str
    description: str
    action: str
    quantity: Decimal
    unit_cost: Decimal
    extended_cost: Decimal
    note: str = ""
    is_header: bool = False

    def to_dict(self) -> Dict[str, object]:
        """Return a JSON-safe dictionary representation of the row."""
        return {
            "level": self.level,
            "item": self.item_code,
            "desc": self.description,
            "action": self.action,
            "qty": float(self.quantity),
            "unit": float(self.unit_cost),
            "ext": float(self.extended_cost),
            "note": self.note,
            "isHeader": self.is_header,
        }


@dataclass
class ComputationResult:
    total_cost: Decimal
    rows: List[CostRow]


@dataclass
class CostResult:
    item_code: str
    item_description: str
    requested_quantity: Decimal
    warehouse_code: str
    total_cost: Decimal
    unit_cost: Decimal
    rows: List[CostRow]


@dataclass
class LayerConsumption:
    """Represents consumption from a single inventory layer."""
    date_label: str
    reference: str
    quantity: Decimal
    unit_cost: Decimal
    extended_cost: Decimal

    def to_dict(self) -> Dict[str, object]:
        return {
            "dateLabel": self.date_label,
            "reference": self.reference,
            "qty": float(self.quantity),
            "unitCost": float(self.unit_cost),
            "extCost": float(self.extended_cost),
        }


@dataclass
class ComponentCost:
    """Cost info for a single BOM component."""
    item_code: str
    description: str
    action: str
    quantity: Decimal
    unit_cost: Decimal
    extended_cost: Decimal
    note: str = ""

    def to_dict(self) -> Dict[str, object]:
        return {
            "item": self.item_code,
            "desc": self.description,
            "action": self.action,
            "qty": float(self.quantity),
            "unit": float(self.unit_cost),
            "ext": float(self.extended_cost),
            "note": self.note,
        }


@dataclass
class CostRootCause:
    """A root cause for a cost increase - identifies which sub-component drove the change."""
    item: str
    desc: str
    prior_cost: Decimal
    new_cost: Decimal
    change_pct: Decimal
    reason: str  # e.g., "Layer exhausted", "Switched to production"

    def to_dict(self) -> Dict[str, object]:
        return {
            "item": self.item,
            "desc": self.desc,
            "priorCost": float(self.prior_cost),
            "newCost": float(self.new_cost),
            "changePct": float(self.change_pct),
            "reason": self.reason,
        }


@dataclass
class CostImpactEvent:
    """Records when a component's cost changes significantly in the queue."""
    component_item: str
    component_desc: str
    trigger_order_no: str
    trigger_order_position: int
    prior_unit_cost: Decimal
    new_unit_cost: Decimal
    cost_change_pct: Decimal
    prior_action: str
    new_action: str
    trigger_item: str = ""  # The finished good item that triggered the cost change
    trigger_item_desc: str = ""
    prior_note: str = ""
    new_note: str = ""
    affects_current: bool = False  # True if this event affects the current order
    root_causes: List["CostRootCause"] = field(default_factory=list)

    def to_dict(self) -> Dict[str, object]:
        return {
            "componentItem": self.component_item,
            "componentDesc": self.component_desc,
            "triggerOrderNo": self.trigger_order_no,
            "triggerOrderPosition": self.trigger_order_position,
            "priorUnitCost": float(self.prior_unit_cost),
            "newUnitCost": float(self.new_unit_cost),
            "costChangePct": float(self.cost_change_pct),
            "priorAction": self.prior_action,
            "newAction": self.new_action,
            "triggerItem": self.trigger_item,
            "triggerItemDesc": self.trigger_item_desc,
            "priorNote": self.prior_note,
            "newNote": self.new_note,
            "affectsCurrent": self.affects_current,
            "rootCauses": [rc.to_dict() for rc in self.root_causes],
        }


@dataclass
class PrecedentOrder:
    """Represents a sales order in the precedent demand queue."""
    sales_order_no: str
    line_key: str
    promise_date: Optional[date]
    open_qty: Decimal
    layers_consumed: List[LayerConsumption] = field(default_factory=list)
    total_cost: Decimal = Decimal("0")
    unit_cost: Decimal = Decimal("0")
    production_qty: Decimal = Decimal("0")
    purchase_qty: Decimal = Decimal("0")
    is_current: bool = False
    top_components: List[ComponentCost] = field(default_factory=list)

    def to_dict(self) -> Dict[str, object]:
        return {
            "salesOrderNo": self.sales_order_no,
            "lineKey": self.line_key,
            "promiseDate": self.promise_date.isoformat() if self.promise_date else None,
            "openQty": float(self.open_qty),
            "layersConsumed": [lc.to_dict() for lc in self.layers_consumed],
            "totalCost": float(self.total_cost),
            "unitCost": float(self.unit_cost),
            "productionQty": float(self.production_qty),
            "purchaseQty": float(self.purchase_qty),
            "isCurrent": self.is_current,
            "topComponents": [c.to_dict() for c in self.top_components],
        }


@dataclass
class ComponentPrecedent:
    """Precedent demand for a BOM component."""
    item_code: str
    description: str
    qty_per_unit: Decimal
    total_qty_needed: Decimal
    queue_position: int
    total_open_orders: int
    prior_orders: List[PrecedentOrder] = field(default_factory=list)
    current_order: Optional[PrecedentOrder] = None
    available_stock: Decimal = Decimal("0")
    shortfall: Decimal = Decimal("0")

    def to_dict(self) -> Dict[str, object]:
        return {
            "itemCode": self.item_code,
            "description": self.description,
            "qtyPerUnit": float(self.qty_per_unit),
            "totalQtyNeeded": float(self.total_qty_needed),
            "queuePosition": self.queue_position,
            "totalOpenOrders": self.total_open_orders,
            "priorOrders": [po.to_dict() for po in self.prior_orders],
            "currentOrder": self.current_order.to_dict() if self.current_order else None,
            "availableStock": float(self.available_stock),
            "shortfall": float(self.shortfall),
        }


@dataclass
class TopCostDriver:
    """Top cost driver for display."""
    item: str
    desc: str
    action: str
    unit: Decimal
    ext: Decimal
    pct: int
    note: str = ""

    def to_dict(self) -> Dict[str, object]:
        return {
            "item": self.item,
            "desc": self.desc,
            "action": self.action,
            "unit": float(self.unit),
            "ext": float(self.ext),
            "pct": self.pct,
            "note": self.note,
        }


@dataclass
class PrecedentDemandResult:
    """Complete precedent demand analysis for an item."""
    item_code: str
    description: str
    queue_position: int
    total_open_orders: int
    prior_orders: List[PrecedentOrder] = field(default_factory=list)
    current_order: Optional[PrecedentOrder] = None
    available_stock_before: Decimal = Decimal("0")
    total_prior_consumption: Decimal = Decimal("0")
    components: List[ComponentPrecedent] = field(default_factory=list)
    cost_impact_events: List[CostImpactEvent] = field(default_factory=list)
    top_cost_drivers: List[TopCostDriver] = field(default_factory=list)

    def to_dict(self) -> Dict[str, object]:
        return {
            "itemCode": self.item_code,
            "description": self.description,
            "queuePosition": self.queue_position,
            "totalOpenOrders": self.total_open_orders,
            "priorOrders": [po.to_dict() for po in self.prior_orders],
            "currentOrder": self.current_order.to_dict() if self.current_order else None,
            "availableStockBefore": float(self.available_stock_before),
            "totalPriorConsumption": float(self.total_prior_consumption),
            "components": [c.to_dict() for c in self.components],
            "costImpactEvents": [e.to_dict() for e in self.cost_impact_events],
            "topCostDrivers": [d.to_dict() for d in self.top_cost_drivers],
        }


class BomCostingService:
    """FIFO costing engine backed by the application's PostgreSQL database."""

    # Class-level cache for BOM relationships - shared across instances
    # This is safe because BOMs rarely change mid-request
    _global_bom_graph: Optional[Dict[str, object]] = None
    _global_bom_graph_loaded: bool = False

    def __init__(
        self,
        warehouse_code: str = "ALL",
        max_depth: int = 10,
        purchasing_costs: Optional[Dict[str, Dict[str, Decimal]]] = None,
    ):
        self.warehouse_code = (warehouse_code or "ALL").upper()
        self.max_depth = max_depth
        self._inventory_cache: Dict[str, List[Dict[str, object]]] = {}
        self._bom_cache: Dict[str, List[Dict[str, Decimal]]] = {}
        self._item_cache: Dict[str, Dict[str, object]] = {}
        self.purchasing_costs = purchasing_costs or {}

    @classmethod
    def _load_global_bom_graph(cls) -> Dict[str, object]:
        """Load and cache BOM relationships globally for fast lookup."""
        if cls._global_bom_graph_loaded and cls._global_bom_graph is not None:
            return cls._global_bom_graph

        all_boms = list(
            BmBillDetail.objects.all()
            .values("billno", "componentitemcode", "quantityperbill")
        )

        bom_by_parent: Dict[str, List[Dict[str, object]]] = defaultdict(list)
        parents_by_component: Dict[str, Set[str]] = defaultdict(set)

        for row in all_boms:
            parent = (row.get("billno") or "").strip().upper()
            component = (row.get("componentitemcode") or "").strip().upper()
            qty_raw = row.get("quantityperbill")
            if parent and component:
                try:
                    qty = Decimal(str(qty_raw)) if qty_raw is not None else Decimal("0")
                except:
                    qty = Decimal("0")
                if qty > Decimal("0"):
                    bom_by_parent[parent].append({"code": component, "quantity": qty})
                    parents_by_component[component].add(parent)

        cls._global_bom_graph = {
            "bom_by_parent": dict(bom_by_parent),
            "parents_by_component": dict(parents_by_component),
        }
        cls._global_bom_graph_loaded = True
        return cls._global_bom_graph

    @classmethod
    def invalidate_bom_cache(cls) -> None:
        """Call this if BOM data changes to force reload."""
        cls._global_bom_graph = None
        cls._global_bom_graph_loaded = False

    def warm_caches(self, item_codes: Iterable[str]) -> None:
        """Preload inventory, BOM, and metadata caches for the provided item set."""
        pending: Set[str] = {
            (code or "").strip().upper() for code in item_codes or [] if code
        }
        seen: Set[str] = set()

        while pending:
            batch = {code for code in pending if code and code not in seen}
            if not batch:
                break
            seen.update(batch)
            self._prefetch_items(batch)
            new_components = self._prefetch_boms(batch)
            self._prefetch_inventory(batch)
            pending.update(code for code in new_components if code not in seen)

    def _prefetch_items(self, item_codes: Set[str]) -> None:
        missing = [code for code in item_codes if code not in self._item_cache]
        if not missing:
            return

        rows = CiItem.objects.filter(itemcode__in=missing).values(
            "itemcode", "itemcodedesc", "standardunitcost", "procurementtype"
        )
        for row in rows:
            key = (row.get("itemcode") or "").strip().upper()
            if not key:
                continue
            self._item_cache[key] = {
                "code": key,
                "description": row.get("itemcodedesc") or key,
                "standard_cost": self._to_decimal(row.get("standardunitcost")),
                "procurement_type": (row.get("procurementtype") or "").strip(),
                "exists": True,
            }

        for code in missing:
            if code not in self._item_cache:
                self._item_cache[code] = {
                    "code": code,
                    "description": code,
                    "standard_cost": Decimal("0"),
                    "procurement_type": "",
                    "exists": False,
                }

    def _prefetch_boms(self, item_codes: Set[str]) -> Set[str]:
        missing = [code for code in item_codes if code not in self._bom_cache]
        if not missing:
            return set()

        new_components: Set[str] = set()

        # Try global cache first (much faster)
        if self._global_bom_graph_loaded and self._global_bom_graph:
            bom_by_parent = self._global_bom_graph["bom_by_parent"]
            for code in missing:
                components = bom_by_parent.get(code, [])
                self._bom_cache[code] = components
                for comp in components:
                    new_components.add(comp["code"])
            return new_components

        # Fallback to DB query
        bom_rows = BmBillDetail.objects.filter(billno__in=missing).values(
            "billno", "componentitemcode", "quantityperbill"
        )
        lookup: Dict[str, List[Dict[str, Decimal]]] = defaultdict(list)

        for row in bom_rows:
            bill_no = (row.get("billno") or "").strip().upper()
            component_code = (row.get("componentitemcode") or "").strip().upper()
            quantity = self._to_decimal(row.get("quantityperbill"))
            if not bill_no:
                continue
            if component_code and quantity > Decimal("0"):
                lookup[bill_no].append({"code": component_code, "quantity": quantity})
                new_components.add(component_code)

        for code in missing:
            self._bom_cache[code] = lookup.get(code, [])

        return new_components

    def _prefetch_inventory(self, item_codes: Set[str]) -> None:
        missing = [code for code in item_codes if code not in self._inventory_cache]
        if not missing:
            return

        filters = {"itemcode__in": missing, "quantityonhand__gt": Decimal("0")}
        if self.warehouse_code != "ALL":
            filters["warehousecode__iexact"] = self.warehouse_code

        raw_layers = (
            ImItemCost.objects.filter(**filters)
            .values(
                "itemcode",
                "receiptdate",
                "receiptno",
                "unitcost",
                "quantityonhand",
                "warehousecode",
            )
            .order_by("receiptdate", "id")
        )

        by_item: Dict[str, List[Dict[str, object]]] = defaultdict(list)
        for layer in raw_layers:
            key = (layer.get("itemcode") or "").strip().upper()
            if not key:
                continue
            qty = self._to_decimal(layer.get("quantityonhand"))
            unit_cost = self._to_decimal(layer.get("unitcost"))
            if qty <= Decimal("0"):
                continue
            receipt_date = layer.get("receiptdate")
            date_label = receipt_date.strftime("%Y-%m-%d") if receipt_date else "No Date"
            by_item[key].append(
                {
                    "qty": qty,
                    "unit": unit_cost,
                    "date_label": date_label,
                    "reference": layer.get("receiptno") or "No Ref",
                    "warehouse": layer.get("warehousecode") or "",
                }
            )

        for code in missing:
            self._inventory_cache[code] = by_item.get(code, [])

    def calculate(
        self, item_code: str, quantity: Decimal, *, capture_rows: bool = True
    ) -> CostResult:
        """Return the costing breakdown for the requested item and quantity."""
        normalized_code = (item_code or "").strip().upper()
        if not normalized_code:
            raise ValueError("An item code is required.")

        requested_quantity = self._to_decimal(quantity)
        if requested_quantity <= Decimal("0"):
            raise ValueError("Quantity must be greater than zero.")

        item_meta = self._get_item_metadata(normalized_code)
        if not item_meta["exists"]:
            raise ItemNotFoundError(f"Item {normalized_code} was not found.")

        computation = self._get_cost(
            normalized_code,
            requested_quantity,
            level=0,
            ancestry=tuple(),
            capture_rows=capture_rows,
        )
        unit_cost = (
            computation.total_cost / requested_quantity
            if requested_quantity > Decimal("0")
            else Decimal("0")
        )

        return CostResult(
            item_code=normalized_code,
            item_description=item_meta["description"],
            requested_quantity=requested_quantity,
            warehouse_code=self.warehouse_code,
            total_cost=computation.total_cost,
            unit_cost=unit_cost,
            rows=computation.rows if capture_rows else [],
        )

    def calculate_precedent_demand(
        self,
        item_code: str,
        quantity: Decimal,
        sales_order_no: str,
        line_key: str,
        promise_date: Optional[date] = None,
        max_display_orders: int = 50,
    ) -> Tuple[CostResult, PrecedentDemandResult]:
        """
        Calculate cost with full queue simulation, showing precedent demand.

        This simulates FIFO consumption across relevant open SO lines,
        ordered by promise date, to accurately reflect inventory state when
        the current order's turn comes. This matches the main report's logic.

        Returns both the accurate CostResult and the PrecedentDemandResult for display.
        """
        normalized_code = (item_code or "").strip().upper()
        if not normalized_code:
            raise ValueError("An item code is required.")

        item_meta = self._get_item_metadata(normalized_code)
        if not item_meta["exists"]:
            raise ItemNotFoundError(f"Item {normalized_code} was not found.")

        # Find all items that could affect this item's cost
        relevant_items, all_components = self._find_relevant_items_for_costing_fast(normalized_code)

        # Get open SO lines only for relevant items
        open_qty_expr = ExpressionWrapper(
            F("quantityordered") - F("quantityshipped"),
            output_field=DecimalField(max_digits=20, decimal_places=6),
        )

        so_filters = {"itemtype__iexact": "1", "itemcode__in": relevant_items}
        if self.warehouse_code != "ALL":
            so_filters["warehousecode__iexact"] = self.warehouse_code

        all_so_lines = list(
            SoSalesOrderDetail.objects.filter(**so_filters)
            .annotate(open_qty=open_qty_expr)
            .filter(open_qty__gt=Decimal("0"))
            .values(
                "salesorderno",
                "linekey",
                "lineseqno",
                "itemcode",
                "itemcodedesc",
                "promisedate",
                "open_qty",
            )
            .order_by("promisedate", "salesorderno", "lineseqno")
        )

        # Find the current order's position in the filtered queue
        current_index = -1
        for idx, so_line in enumerate(all_so_lines):
            so_no = (so_line.get("salesorderno") or "").strip()
            lk = (so_line.get("linekey") or "").strip()
            if so_no == sales_order_no and lk == line_key:
                current_index = idx
                break

        # If not found, append as new order at end
        if current_index < 0:
            current_index = len(all_so_lines)
            all_so_lines.append({
                "salesorderno": sales_order_no,
                "linekey": line_key,
                "itemcode": normalized_code,
                "itemcodedesc": item_meta["description"],
                "promisedate": promise_date,
                "open_qty": quantity,
            })

        # Count orders for the same item to show queue position within item
        same_item_orders = [
            so for so in all_so_lines
            if (so.get("itemcode") or "").strip().upper() == normalized_code
        ]
        item_queue_position = 0
        for idx, so in enumerate(same_item_orders):
            so_no = (so.get("salesorderno") or "").strip()
            lk = (so.get("linekey") or "").strip()
            if so_no == sales_order_no and lk == line_key:
                item_queue_position = idx + 1
                break

        # Batch load ALL data we need upfront
        self._inventory_cache.clear()
        self._bom_cache.clear()
        self._item_cache.clear()

        all_item_codes = {
            (so.get("itemcode") or "").strip().upper()
            for so in all_so_lines[:current_index + 1]
            if so.get("itemcode")
        }
        all_item_codes.update(all_components)
        self.warm_caches(all_item_codes)

        # Get initial stock for the target item (before any consumption)
        initial_layers = self._inventory_cache.get(normalized_code, [])
        available_stock_before = sum(layer["qty"] for layer in initial_layers)

        # Deep copy inventory cache for simulation
        simulation_inventory = {
            k: [layer.copy() for layer in v]
            for k, v in self._inventory_cache.items()
        }

        # Process all orders up to and including current
        prior_orders_for_same_item: List[PrecedentOrder] = []
        total_prior_consumption = Decimal("0")
        current_order: Optional[PrecedentOrder] = None
        current_cost_result: Optional[CostResult] = None

        # Track component costs across same-item orders to detect inflection points
        last_component_costs: Dict[str, Dict[str, object]] = {}
        cost_impact_events: List[CostImpactEvent] = []
        same_item_order_position = 0

        self._inventory_cache = simulation_inventory

        for so_line in all_so_lines[:current_index + 1]:
            so_no = (so_line.get("salesorderno") or "").strip()
            lk = (so_line.get("linekey") or "").strip()
            so_item = (so_line.get("itemcode") or "").strip().upper()
            so_qty = self._to_decimal(so_line.get("open_qty"))
            so_promise = so_line.get("promisedate")
            is_current = (so_no == sales_order_no and lk == line_key)
            is_same_item = (so_item == normalized_code)

            if so_qty <= Decimal("0"):
                continue

            # Capture layer state before this order for same-item orders
            layers_before = []
            if is_same_item:
                same_item_order_position += 1
                item_layers = self._inventory_cache.get(so_item, [])
                layers_before = [
                    {"qty": l["qty"], "unit": l["unit"], "date_label": l["date_label"], "reference": l["reference"]}
                    for l in item_layers if l["qty"] > Decimal("0")
                ]

            # Calculate cost for this order (this depletes inventory cache)
            # Capture rows for all same-item orders to track component costs
            try:
                result = self._get_cost(
                    so_item,
                    so_qty,
                    level=0,
                    ancestry=tuple(),
                    capture_rows=is_same_item,
                )
            except (ItemNotFoundError, CircularBomReferenceError):
                continue

            # Track component cost changes for same-item orders
            if is_same_item and result.rows:
                current_component_costs = self._extract_component_costs(result.rows)

                # Compare to previous order's component costs
                for comp_code, comp_info in current_component_costs.items():
                    if comp_code in last_component_costs:
                        prev_info = last_component_costs[comp_code]
                        prev_unit = prev_info["unit_cost"]
                        curr_unit = comp_info["unit_cost"]

                        # Check for significant cost increase (>5%)
                        if prev_unit > Decimal("0"):
                            pct_change = ((curr_unit - prev_unit) / prev_unit) * Decimal("100")
                            if pct_change > Decimal("5"):
                                cost_impact_events.append(
                                    CostImpactEvent(
                                        component_item=comp_code,
                                        component_desc=comp_info["description"],
                                        trigger_order_no=so_no,
                                        trigger_order_position=same_item_order_position,
                                        prior_unit_cost=prev_unit,
                                        new_unit_cost=curr_unit,
                                        cost_change_pct=pct_change,
                                        prior_action=prev_info["action"],
                                        new_action=comp_info["action"],
                                        prior_note=prev_info.get("note", ""),
                                        new_note=comp_info.get("note", ""),
                                    )
                                )

                last_component_costs = current_component_costs

            if is_current:
                unit_cost = result.total_cost / so_qty if so_qty > Decimal("0") else Decimal("0")
                current_cost_result = CostResult(
                    item_code=normalized_code,
                    item_description=item_meta["description"],
                    requested_quantity=so_qty,
                    warehouse_code=self.warehouse_code,
                    total_cost=result.total_cost,
                    unit_cost=unit_cost,
                    rows=result.rows,
                )

                layers_consumed = self._extract_layer_consumption_fast(layers_before, so_item)
                production_qty = sum(
                    r.quantity for r in result.rows
                    if r.action == "MAKE" and r.item_code == normalized_code
                )
                purchase_qty = sum(
                    r.quantity for r in result.rows
                    if r.action in ("BUY", "STD") and r.item_code == normalized_code
                )

                current_order = PrecedentOrder(
                    sales_order_no=so_no,
                    line_key=lk,
                    promise_date=so_promise,
                    open_qty=so_qty,
                    layers_consumed=layers_consumed,
                    total_cost=result.total_cost,
                    unit_cost=unit_cost,
                    production_qty=production_qty,
                    purchase_qty=purchase_qty,
                    is_current=True,
                )

            elif is_same_item:
                layers_consumed = self._extract_layer_consumption_fast(layers_before, so_item)
                stock_consumed = sum(lc.quantity for lc in layers_consumed)
                total_prior_consumption += stock_consumed

                unit_cost = result.total_cost / so_qty if so_qty > Decimal("0") else Decimal("0")
                production_qty = Decimal("0")
                purchase_qty = Decimal("0")

                if stock_consumed < so_qty:
                    shortfall = so_qty - stock_consumed
                    bom = self._bom_cache.get(so_item, [])
                    if bom:
                        production_qty = shortfall
                    else:
                        purchase_qty = shortfall

                if len(prior_orders_for_same_item) < max_display_orders:
                    prior_orders_for_same_item.append(
                        PrecedentOrder(
                            sales_order_no=so_no,
                            line_key=lk,
                            promise_date=so_promise,
                            open_qty=so_qty,
                            layers_consumed=layers_consumed,
                            total_cost=result.total_cost,
                            unit_cost=unit_cost,
                            production_qty=production_qty,
                            purchase_qty=purchase_qty,
                            is_current=False,
                        )
                    )

        components: List[ComponentPrecedent] = []

        # Analyze component cost timeline across ALL orders (not just same-item)
        # This shows when each component's cost layer changes, regardless of parent item
        component_cost_events = self._analyze_component_cost_timeline(
            target_item=normalized_code,
            target_components=all_components,
            all_so_lines=all_so_lines,
            current_order_index=current_index,
            current_so_no=sales_order_no,
            current_line_key=line_key,
        )

        # Merge component-level events with any same-item events
        all_cost_events = cost_impact_events + component_cost_events

        # Extract top cost drivers from the current order's breakdown
        top_drivers: List[TopCostDriver] = []
        if current_cost_result and current_cost_result.rows:
            top_drivers = self._extract_top_cost_drivers(
                current_cost_result.rows,
                current_cost_result.total_cost,
            )

        precedent_result = PrecedentDemandResult(
            item_code=normalized_code,
            description=item_meta["description"],
            queue_position=item_queue_position,
            total_open_orders=len(same_item_orders),
            prior_orders=prior_orders_for_same_item,
            current_order=current_order,
            available_stock_before=available_stock_before,
            total_prior_consumption=total_prior_consumption,
            components=components,
            cost_impact_events=all_cost_events,
            top_cost_drivers=top_drivers,
        )

        if current_cost_result is None:
            self._inventory_cache.clear()
            current_cost_result = self.calculate(normalized_code, quantity)

        return current_cost_result, precedent_result

    def _find_relevant_items_for_costing_fast(self, item_code: str) -> Tuple[Set[str], Set[str]]:
        """
        Find all items that could affect the cost of the target item.
        OPTIMIZED: Uses globally cached BOM graph.

        Returns:
            Tuple of (relevant_items for SO filtering, all_components for cache warming)
        """
        relevant = {item_code}
        all_components: Set[str] = {item_code}

        # Use globally cached BOM graph
        graph = self._load_global_bom_graph()
        bom_by_parent = graph["bom_by_parent"]
        parents_by_component = graph["parents_by_component"]

        # Recursively find all components of target item
        to_check = {item_code}
        while to_check:
            current = to_check.pop()
            for comp_info in bom_by_parent.get(current, []):
                comp = comp_info["code"]
                if comp not in all_components:
                    all_components.add(comp)
                    to_check.add(comp)
                    relevant.add(comp)

        # Find all parent items that use any of these components
        for comp in all_components:
            relevant.update(parents_by_component.get(comp, set()))

        return relevant, all_components

    def _extract_layer_consumption_fast(
        self,
        layers_before: List[Dict[str, object]],
        item_code: str,
    ) -> List[LayerConsumption]:
        """Compare layer state before/after to extract what was consumed. Uses cache directly."""
        consumed: List[LayerConsumption] = []
        layers_after = self._inventory_cache.get(item_code, [])

        # Build lookup of current layer quantities
        after_by_ref: Dict[str, Decimal] = {}
        for layer in layers_after:
            key = f"{layer['date_label']}|{layer['reference']}"
            after_by_ref[key] = layer["qty"]

        for layer in layers_before:
            key = f"{layer['date_label']}|{layer['reference']}"
            qty_before = layer["qty"]
            qty_after = after_by_ref.get(key, Decimal("0"))
            qty_consumed = qty_before - qty_after

            if qty_consumed > Decimal("0"):
                consumed.append(
                    LayerConsumption(
                        date_label=layer["date_label"],
                        reference=layer["reference"],
                        quantity=qty_consumed,
                        unit_cost=layer["unit"],
                        extended_cost=qty_consumed * layer["unit"],
                    )
                )

        return consumed

    def _extract_component_costs(
        self, rows: List[CostRow]
    ) -> Dict[str, Dict[str, object]]:
        """
        Extract component-level costs from cost breakdown rows.

        Returns dict keyed by component item code with unit cost, action, etc.
        For components that appear multiple times (different actions), uses
        weighted average unit cost.

        NOTE: We include MAKE header rows (is_header=True) because when a component
        switches from STOCK to MAKE, we need to capture that cost change.
        """
        component_data: Dict[str, Dict[str, object]] = {}

        for row in rows:
            # Skip level 0 (the parent item itself)
            if row.level < 1:
                continue

            item_code = row.item_code

            # For MAKE headers, capture the production cost
            # For regular rows (STOCK, BUY), capture as usual
            if row.is_header and row.action == "MAKE":
                # MAKE header - this represents production cost for a sub-assembly
                if item_code not in component_data:
                    component_data[item_code] = {
                        "description": row.description,
                        "action": row.action,
                        "unit_cost": row.unit_cost,
                        "total_qty": row.quantity,
                        "total_cost": row.extended_cost,
                        "note": row.note,
                    }
                # Don't aggregate MAKE headers - they represent the rolled-up cost
                continue

            # Skip other header rows (shouldn't be any, but just in case)
            if row.is_header:
                continue

            if item_code not in component_data:
                component_data[item_code] = {
                    "description": row.description,
                    "action": row.action,
                    "unit_cost": row.unit_cost,
                    "total_qty": row.quantity,
                    "total_cost": row.extended_cost,
                    "note": row.note,
                }
            else:
                # Aggregate multiple entries for same component (e.g., multiple STOCK layers)
                existing = component_data[item_code]
                # Only aggregate if same action type (don't mix STOCK with MAKE)
                if existing["action"] == row.action:
                    existing["total_qty"] += row.quantity
                    existing["total_cost"] += row.extended_cost
                    # Recalculate weighted average unit cost
                    if existing["total_qty"] > Decimal("0"):
                        existing["unit_cost"] = existing["total_cost"] / existing["total_qty"]
                    existing["note"] = row.note
                # If different action, keep the more expensive one (likely MAKE)
                elif row.unit_cost > existing["unit_cost"]:
                    existing["action"] = row.action
                    existing["unit_cost"] = row.unit_cost
                    existing["total_qty"] = row.quantity
                    existing["total_cost"] = row.extended_cost
                    existing["note"] = row.note

        return component_data

    def _extract_top_cost_drivers(
        self, rows: List[CostRow], total_cost: Decimal
    ) -> List[TopCostDriver]:
        """
        Extract top 5 cost drivers from cost breakdown rows.

        Returns list of TopCostDriver sorted by extended cost descending.
        Includes MAKE sub-assemblies which appear as header rows.
        """
        if total_cost <= Decimal("0"):
            return []

        # Collect component costs (level >= 1)
        # Include MAKE headers since they represent sub-assembly costs
        component_costs: List[Dict[str, object]] = []
        seen_items: Set[str] = set()

        for row in rows:
            if row.level < 1:
                continue
            if row.extended_cost <= Decimal("0"):
                continue

            # Include MAKE headers (sub-assemblies) and regular rows
            # Skip other headers
            if row.is_header and row.action != "MAKE":
                continue

            # Avoid duplicates (MAKE header + its components)
            if row.item_code in seen_items:
                continue
            seen_items.add(row.item_code)

            component_costs.append({
                "item": row.item_code,
                "desc": row.description,
                "action": row.action,
                "unit": row.unit_cost,
                "ext": row.extended_cost,
                "note": row.note,
            })

        # Sort by extended cost descending
        component_costs.sort(key=lambda x: x["ext"], reverse=True)

        # Take top 5 and calculate percentages
        top_drivers: List[TopCostDriver] = []
        for comp in component_costs[:5]:
            pct = int((comp["ext"] / total_cost) * Decimal("100"))
            top_drivers.append(
                TopCostDriver(
                    item=comp["item"],
                    desc=comp["desc"],
                    action=comp["action"],
                    unit=comp["unit"],
                    ext=comp["ext"],
                    pct=pct,
                    note=comp["note"],
                )
            )

        return top_drivers

    def _analyze_component_cost_timeline(
        self,
        target_item: str,
        target_components: Set[str],
        all_so_lines: List[Dict[str, object]],
        current_order_index: int,
        current_so_no: str,
        current_line_key: str,
    ) -> List[CostImpactEvent]:
        """
        Analyze when component costs change across ALL orders in the queue.

        For each component used by the target item, simulates FIFO consumption
        across all orders that use that component (regardless of parent item).
        Identifies when each component's cost layer changes significantly.

        Returns list of CostImpactEvent showing when/where each cost jump occurs.
        """
        events: List[CostImpactEvent] = []
        graph = self._load_global_bom_graph()
        bom_by_parent = graph["bom_by_parent"]
        parents_by_component = graph["parents_by_component"]

        # For each component in the target item's BOM
        for comp_code in target_components:
            if comp_code == target_item:
                continue  # Skip the parent item itself

            comp_meta = self._get_item_metadata(comp_code)
            if not comp_meta["exists"]:
                continue

            # Get fresh inventory layers for this component
            comp_layers = self._get_fresh_inventory_layers(comp_code)

            # Also get fresh layers for sub-components (if this component has a BOM)
            comp_bom = bom_by_parent.get(comp_code, [])
            sub_comp_layers: Dict[str, List[Dict[str, object]]] = {}
            for sub in comp_bom:
                sub_code = sub["code"]
                sub_comp_layers[sub_code] = self._get_fresh_inventory_layers(sub_code)

            # Skip if no inventory and no sub-components to track
            if not comp_layers and not comp_bom:
                continue

            # Find all parent items that use this component
            items_using_comp = {comp_code}  # Direct orders
            items_using_comp.update(parents_by_component.get(comp_code, set()))

            # Filter SO lines to those that consume this component
            relevant_so_lines = [
                so for so in all_so_lines[:current_order_index + 1]
                if (so.get("itemcode") or "").strip().upper() in items_using_comp
            ]

            if not relevant_so_lines:
                continue

            # Simulate FIFO consumption and track cost changes
            last_unit_cost: Optional[Decimal] = None
            last_action: str = ""
            last_note: str = ""
            last_sub_comp_costs: Dict[str, Decimal] = {}
            queue_position = 0

            for so_line in relevant_so_lines:
                queue_position += 1
                so_no = (so_line.get("salesorderno") or "").strip()
                lk = (so_line.get("linekey") or "").strip()
                so_item = (so_line.get("itemcode") or "").strip().upper()
                so_item_desc = (so_line.get("itemcodedesc") or "").strip()
                so_qty = self._to_decimal(so_line.get("open_qty"))
                is_current = (so_no == current_so_no and lk == current_line_key)

                if so_qty <= Decimal("0"):
                    continue

                # Calculate how much of this component the order needs
                comp_qty_needed = Decimal("0")
                if so_item == comp_code:
                    # Direct order for the component
                    comp_qty_needed = so_qty
                else:
                    # Order for a parent item - calculate component qty from BOM
                    comp_qty_needed = self._calc_component_qty_for_parent(
                        so_item, comp_code, so_qty, bom_by_parent
                    )

                if comp_qty_needed <= Decimal("0"):
                    continue

                # Snapshot current sub-component costs before consumption
                current_sub_comp_costs: Dict[str, Decimal] = {}
                for sub in comp_bom:
                    sub_code = sub["code"]
                    sub_layers = sub_comp_layers.get(sub_code, [])
                    if sub_layers:
                        # Get current weighted average cost
                        total_qty = sum(l["qty"] for l in sub_layers)
                        if total_qty > Decimal("0"):
                            current_sub_comp_costs[sub_code] = sum(
                                l["qty"] * l["unit"] for l in sub_layers
                            ) / total_qty
                        else:
                            # No stock left - get standard cost
                            sub_meta = self._item_cache.get(sub_code, {})
                            current_sub_comp_costs[sub_code] = sub_meta.get(
                                "standard_cost", Decimal("0")
                            )
                    else:
                        sub_meta = self._item_cache.get(sub_code, {})
                        current_sub_comp_costs[sub_code] = sub_meta.get(
                            "standard_cost", Decimal("0")
                        )

                # Simulate FIFO consumption from layers
                unit_cost, action, note = self._simulate_fifo_for_component(
                    comp_layers, comp_qty_needed, comp_meta
                )

                # Also simulate sub-component consumption (for root cause tracking)
                if action == "MAKE" and comp_bom:
                    for sub in comp_bom:
                        sub_code = sub["code"]
                        sub_qty = sub["quantity"] * comp_qty_needed
                        sub_layers = sub_comp_layers.get(sub_code, [])
                        if sub_layers:
                            # Consume from sub-component layers
                            remaining = sub_qty
                            for layer in sub_layers:
                                if remaining <= Decimal("0"):
                                    break
                                take = min(layer["qty"], remaining)
                                layer["qty"] -= take
                                remaining -= take

                # Check for significant cost change
                if last_unit_cost is not None and last_unit_cost > Decimal("0"):
                    pct_change = ((unit_cost - last_unit_cost) / last_unit_cost) * Decimal("100")
                    if pct_change > Decimal("5"):
                        # Identify root causes - which sub-components drove the change
                        root_causes: List[CostRootCause] = []

                        if comp_bom and action == "MAKE":
                            # For MAKE actions, show sub-component cost breakdown
                            # Calculate contribution of each sub-component
                            sub_contributions: List[Dict[str, object]] = []

                            for sub in comp_bom:
                                sub_code = sub["code"]
                                sub_qty = sub["quantity"]
                                sub_meta = self._item_cache.get(sub_code)
                                if not sub_meta:
                                    sub_meta = self._get_item_metadata(sub_code)
                                new_cost = current_sub_comp_costs.get(sub_code, Decimal("0"))
                                prior_cost = last_sub_comp_costs.get(sub_code, Decimal("0")) if last_sub_comp_costs else Decimal("0")

                                # Calculate this sub-component's contribution to the total
                                contribution = sub_qty * new_cost

                                # Determine if this sub-component's cost changed
                                if prior_cost > Decimal("0") and new_cost > prior_cost:
                                    sub_pct_change = ((new_cost - prior_cost) / prior_cost) * Decimal("100")
                                    sub_layers = sub_comp_layers.get(sub_code, [])
                                    total_sub_qty = sum(l["qty"] for l in sub_layers)

                                    if total_sub_qty <= Decimal("0"):
                                        reason = "Stock exhausted"
                                    elif sub_pct_change > Decimal("50"):
                                        reason = "Moved to expensive layer"
                                    else:
                                        reason = "Layer cost increased"
                                elif prior_cost <= Decimal("0") and last_action == "STOCK":
                                    # Switched from STOCK to MAKE - show current costs
                                    sub_pct_change = Decimal("0")
                                    reason = "Now using production"
                                else:
                                    sub_pct_change = Decimal("0")
                                    reason = ""

                                sub_contributions.append({
                                    "code": sub_code,
                                    "desc": sub_meta.get("description", ""),
                                    "prior_cost": prior_cost,
                                    "new_cost": new_cost,
                                    "pct_change": sub_pct_change,
                                    "contribution": contribution,
                                    "reason": reason,
                                })

                            # Sort by contribution (highest cost impact first)
                            sub_contributions.sort(key=lambda x: x["contribution"], reverse=True)

                            # Take top 3 contributors
                            for sc in sub_contributions[:3]:
                                # Only include if meaningful
                                if sc["new_cost"] > Decimal("0"):
                                    root_causes.append(
                                        CostRootCause(
                                            item=sc["code"],
                                            desc=sc["desc"],
                                            prior_cost=sc["prior_cost"],
                                            new_cost=sc["new_cost"],
                                            change_pct=sc["pct_change"],
                                            reason=sc["reason"],
                                        )
                                    )

                        events.append(
                            CostImpactEvent(
                                component_item=comp_code,
                                component_desc=comp_meta["description"],
                                trigger_order_no=so_no,
                                trigger_order_position=queue_position,
                                prior_unit_cost=last_unit_cost,
                                new_unit_cost=unit_cost,
                                cost_change_pct=pct_change,
                                prior_action=last_action,
                                new_action=action,
                                trigger_item=so_item,
                                trigger_item_desc=so_item_desc,
                                prior_note=last_note,
                                new_note=note,
                                affects_current=is_current,
                                root_causes=root_causes,
                            )
                        )

                last_unit_cost = unit_cost
                last_action = action
                last_note = note
                last_sub_comp_costs = current_sub_comp_costs.copy()

        return events

    def _get_fresh_inventory_layers(self, item_code: str) -> List[Dict[str, object]]:
        """Get a fresh copy of inventory layers for simulation."""
        filters = {"itemcode__iexact": item_code, "quantityonhand__gt": Decimal("0")}
        if self.warehouse_code != "ALL":
            filters["warehousecode__iexact"] = self.warehouse_code

        raw_layers = list(
            ImItemCost.objects.filter(**filters)
            .values("receiptdate", "receiptno", "unitcost", "quantityonhand")
            .order_by("receiptdate", "id")
        )

        layers: List[Dict[str, object]] = []
        for layer in raw_layers:
            qty = self._to_decimal(layer["quantityonhand"])
            if qty <= Decimal("0"):
                continue
            receipt_date = layer.get("receiptdate")
            date_label = receipt_date.strftime("%Y-%m-%d") if receipt_date else "No Date"
            layers.append({
                "qty": qty,
                "unit": self._to_decimal(layer["unitcost"]),
                "date_label": date_label,
                "reference": layer.get("receiptno") or "No Ref",
            })
        return layers

    def _calc_component_qty_for_parent(
        self,
        parent_item: str,
        component_item: str,
        parent_qty: Decimal,
        bom_by_parent: Dict[str, List[Dict[str, object]]],
    ) -> Decimal:
        """Calculate how much of a component is needed for a parent item order."""
        # Check direct BOM first
        for comp_info in bom_by_parent.get(parent_item, []):
            if comp_info["code"] == component_item:
                return parent_qty * comp_info["quantity"]

        # Check nested BOMs (one level deep for performance)
        for comp_info in bom_by_parent.get(parent_item, []):
            sub_parent = comp_info["code"]
            sub_qty = comp_info["quantity"]
            for sub_comp_info in bom_by_parent.get(sub_parent, []):
                if sub_comp_info["code"] == component_item:
                    return parent_qty * sub_qty * sub_comp_info["quantity"]

        return Decimal("0")

    def _simulate_fifo_for_component(
        self,
        layers: List[Dict[str, object]],
        qty_needed: Decimal,
        item_meta: Dict[str, object],
    ) -> Tuple[Decimal, str, str]:
        """
        Simulate FIFO consumption for a component and return unit cost.

        Returns (unit_cost, action, note) tuple.
        """
        remaining = qty_needed
        total_cost = Decimal("0")
        consumed_from_stock = Decimal("0")
        last_layer_note = ""
        last_layer_cost = Decimal("0")

        # Consume from inventory layers
        for layer in layers:
            if remaining <= Decimal("0"):
                break
            available = layer["qty"]
            if available <= Decimal("0"):
                continue

            take_qty = min(available, remaining)
            remaining -= take_qty
            layer["qty"] -= take_qty
            consumed_from_stock += take_qty
            total_cost += take_qty * layer["unit"]
            last_layer_cost = layer["unit"]
            last_layer_note = f"Layer: {layer['date_label']} ({layer['reference']})"

        # Determine action and handle shortfall
        if consumed_from_stock > Decimal("0") and remaining <= Decimal("0"):
            # All from stock
            action = "STOCK"
            note = last_layer_note
        elif remaining > Decimal("0"):
            # Need production or purchase for shortfall
            item_code = item_meta.get("code", "")
            bom = self._bom_cache.get(item_code, [])

            if bom:
                # Calculate actual production cost from BOM components
                production_cost = self._estimate_production_cost(item_code, bom)
                if production_cost <= Decimal("0"):
                    # Fallback: use higher of standard cost or 2x last layer cost
                    std_cost = item_meta.get("standard_cost", Decimal("0"))
                    production_cost = max(std_cost, last_layer_cost * Decimal("2"))

                shortfall_cost = remaining * production_cost
                action = "MAKE"
                note = "Production Required"
            else:
                std_cost = item_meta.get("standard_cost", Decimal("0"))
                shortfall_cost = remaining * std_cost
                action = "BUY" if item_meta.get("procurement_type") == "B" else "STD"
                note = "Std Cost"

            total_cost += shortfall_cost
        else:
            action = "STOCK"
            note = last_layer_note

        unit_cost = total_cost / qty_needed if qty_needed > Decimal("0") else Decimal("0")
        return unit_cost, action, note

    def _estimate_production_cost(
        self, item_code: str, bom: List[Dict[str, object]]
    ) -> Decimal:
        """
        Estimate production cost by summing BOM component costs.
        Uses current inventory layer costs where available, standard cost otherwise.
        """
        total_cost = Decimal("0")

        for comp in bom:
            comp_code = comp["code"]
            comp_qty = comp["quantity"]

            # Get component's current cost from inventory or standard cost
            comp_layers = self._inventory_cache.get(comp_code, [])
            if comp_layers:
                # Use weighted average of available layers
                layer_qty = sum(l["qty"] for l in comp_layers)
                if layer_qty > Decimal("0"):
                    layer_cost = sum(l["qty"] * l["unit"] for l in comp_layers) / layer_qty
                else:
                    layer_cost = comp_layers[0]["unit"] if comp_layers else Decimal("0")
                comp_unit_cost = layer_cost
            else:
                # No inventory - use standard cost or check for nested BOM
                comp_meta = self._item_cache.get(comp_code, {})
                comp_unit_cost = comp_meta.get("standard_cost", Decimal("0"))

                # If component has its own BOM, recursively estimate
                comp_bom = self._bom_cache.get(comp_code, [])
                if comp_bom and comp_unit_cost <= Decimal("0"):
                    comp_unit_cost = self._estimate_production_cost(comp_code, comp_bom)

            total_cost += comp_qty * comp_unit_cost

        return total_cost

    def _find_relevant_items_for_costing(self, item_code: str) -> Set[str]:
        """
        Find all items that could affect the cost of the target item.

        This includes:
        - The target item itself
        - All components in the target item's BOM (recursively)
        - All parent items that use any of those components

        This allows us to filter SO lines to only process relevant orders.
        """
        relevant = {item_code}

        # Get all components recursively (these are items whose inventory we need)
        components_to_check: Set[str] = {item_code}
        all_components: Set[str] = set()

        while components_to_check:
            current = components_to_check.pop()
            if current in all_components:
                continue
            all_components.add(current)

            # Get BOM for this item
            bom = self._get_bom_components(current)
            for comp in bom:
                comp_code = comp["code"]
                if comp_code not in all_components:
                    components_to_check.add(comp_code)
                    relevant.add(comp_code)

        # Find all parent items that use any of these components
        # These are items whose SO lines could consume component inventory
        if all_components:
            parent_items = set(
                BmBillDetail.objects.filter(
                    componentitemcode__in=all_components
                ).values_list("billno", flat=True).distinct()
            )
            relevant.update((p or "").strip().upper() for p in parent_items if p)

        return relevant

    def _extract_layer_consumption(
        self,
        layers_before: List[Dict[str, object]],
        item_code: str,
    ) -> List[LayerConsumption]:
        """Compare layer state before/after to extract what was consumed."""
        consumed: List[LayerConsumption] = []
        layers_after = self._get_inventory_layers(item_code)

        # Build lookup of current layer quantities
        after_by_ref: Dict[str, Decimal] = {}
        for layer in layers_after:
            key = f"{layer['date_label']}|{layer['reference']}"
            after_by_ref[key] = layer["qty"]

        for layer in layers_before:
            key = f"{layer['date_label']}|{layer['reference']}"
            qty_before = layer["qty"]
            qty_after = after_by_ref.get(key, Decimal("0"))
            qty_consumed = qty_before - qty_after

            if qty_consumed > Decimal("0"):
                consumed.append(
                    LayerConsumption(
                        date_label=layer["date_label"],
                        reference=layer["reference"],
                        quantity=qty_consumed,
                        unit_cost=layer["unit"],
                        extended_cost=qty_consumed * layer["unit"],
                    )
                )

        return consumed

    def _build_component_precedent(
        self,
        parent_item: str,
        production_qty: Decimal,
        prior_so_lines: List[Dict[str, object]],
        max_display: int,
    ) -> List[ComponentPrecedent]:
        """Build precedent demand info for components needed for production."""
        components: List[ComponentPrecedent] = []
        bom = self._get_bom_components(parent_item)

        for comp in bom:
            comp_code = comp["code"]
            qty_per = comp["quantity"]
            total_needed = production_qty * qty_per

            comp_meta = self._get_item_metadata(comp_code)
            if not comp_meta["exists"]:
                continue

            # Find all prior SO lines that consume this component
            # (either directly or via their own BOMs)
            prior_orders: List[PrecedentOrder] = []
            items_using_component = self._find_items_using_component(comp_code)

            for so_line in prior_so_lines:
                so_item = (so_line.get("itemcode") or "").strip().upper()
                if so_item not in items_using_component:
                    continue

                so_no = (so_line.get("salesorderno") or "").strip()
                so_qty = self._to_decimal(so_line.get("open_qty"))
                so_promise = so_line.get("promisedate")

                # Calculate how much of this component the SO line needs
                comp_qty_needed = Decimal("0")
                if so_item == comp_code:
                    comp_qty_needed = so_qty
                else:
                    so_bom = self._get_bom_components(so_item)
                    for c in so_bom:
                        if c["code"] == comp_code:
                            comp_qty_needed = so_qty * c["quantity"]
                            break

                if comp_qty_needed > Decimal("0") and len(prior_orders) < max_display:
                    prior_orders.append(
                        PrecedentOrder(
                            sales_order_no=f"{so_no} ({so_item})" if so_item != comp_code else so_no,
                            line_key=so_line.get("linekey") or "",
                            promise_date=so_promise,
                            open_qty=comp_qty_needed,
                            layers_consumed=[],
                            total_cost=Decimal("0"),
                            unit_cost=Decimal("0"),
                            production_qty=Decimal("0"),
                            purchase_qty=Decimal("0"),
                            is_current=False,
                        )
                    )

            # Get current available stock for component
            comp_layers = self._get_inventory_layers(comp_code)
            available_stock = sum(l["qty"] for l in comp_layers)
            prior_consumption = sum(po.open_qty for po in prior_orders)
            shortfall = max(Decimal("0"), (prior_consumption + total_needed) - available_stock)

            components.append(
                ComponentPrecedent(
                    item_code=comp_code,
                    description=comp_meta["description"],
                    qty_per_unit=qty_per,
                    total_qty_needed=total_needed,
                    queue_position=len(prior_orders) + 1,
                    total_open_orders=len(prior_orders) + 1,
                    prior_orders=prior_orders,
                    current_order=None,
                    available_stock=available_stock,
                    shortfall=shortfall,
                )
            )

        return components

    def _find_items_using_component(self, component_code: str) -> Set[str]:
        """Find all items that use a component (directly or as the item itself)."""
        result = {component_code}  # Item could be ordered directly

        parent_bills = BmBillDetail.objects.filter(
            componentitemcode__iexact=component_code
        ).values_list("billno", flat=True).distinct()

        result.update((b or "").strip().upper() for b in parent_bills)
        return result

    def _get_cost(
        self,
        item_code: str,
        quantity: Decimal,
        *,
        level: int,
        ancestry: Tuple[str, ...],
        capture_rows: bool,
    ) -> ComputationResult:
        if level > self.max_depth:
            raise CircularBomReferenceError(
                f"Maximum depth of {self.max_depth} exceeded for {item_code}."
            )

        if item_code in ancestry:
            raise CircularBomReferenceError(
                f"Circular reference detected while processing {item_code}."
            )

        ancestry_chain = ancestry + (item_code,)
        item_meta = self._get_item_metadata(item_code)
        inventory_layers = self._get_inventory_layers(item_code)

        remaining = self._to_decimal(quantity)
        total_cost = Decimal("0")
        rows: List[CostRow] = []

        for layer in inventory_layers:
            if remaining <= Decimal("0"):
                break

            available = layer["qty"]
            if available <= Decimal("0"):
                continue

            take_qty = available if available <= remaining else remaining
            remaining -= take_qty
            layer["qty"] -= take_qty

            line_cost = take_qty * layer["unit"]
            total_cost += line_cost

            if capture_rows:
                rows.append(
                    CostRow(
                        level=level,
                        item_code=item_code,
                        description=item_meta["description"],
                        action="STOCK",
                        quantity=take_qty,
                        unit_cost=layer["unit"],
                        extended_cost=line_cost,
                        note=f"Layer: {layer['date_label']} ({layer['reference']})",
                    )
                )

        if remaining > Decimal("0"):
            bom = self._get_bom_components(item_code)

            if bom:
                make_qty = remaining
                remaining = Decimal("0")
                make_cost = Decimal("0")
                child_rows: List[CostRow] = []

                for component in bom:
                    component_qty = make_qty * component["quantity"]
                    if component_qty <= Decimal("0"):
                        continue

                    child_result = self._get_cost(
                        component["code"],
                        component_qty,
                        level=level + 1,
                        ancestry=ancestry_chain,
                        capture_rows=capture_rows,
                    )
                    make_cost += child_result.total_cost
                    if capture_rows:
                        child_rows.extend(child_result.rows)

                unit_make_cost = (
                    make_cost / make_qty if make_qty > Decimal("0") else Decimal("0")
                )
                if capture_rows:
                    rows.append(
                        CostRow(
                            level=level,
                            item_code=item_code,
                            description=item_meta["description"],
                            action="MAKE",
                            quantity=make_qty,
                            unit_cost=unit_make_cost,
                            extended_cost=make_cost,
                            note="Production Required",
                            is_header=True,
                        )
                    )
                    rows.extend(child_rows)
                total_cost += make_cost
            else:
                purchase_qty = remaining
                remaining = Decimal("0")
                cost_entry = self.purchasing_costs.get(item_code)
                if cost_entry:
                    unit_price = self._to_decimal(cost_entry.get("cost"))
                    note = cost_entry.get("source") or "Purchasing Override"
                    action = "BUY"
                else:
                    unit_price = item_meta["standard_cost"]
                    note = "Std Cost" if unit_price > Decimal("0") else "No Cost Data"
                    action = (
                        "BUY"
                        if item_meta["procurement_type"] == "B" and unit_price > Decimal("0")
                        else "STD"
                    )
                line_cost = purchase_qty * unit_price
                total_cost += line_cost
                if capture_rows:
                    rows.append(
                        CostRow(
                            level=level,
                            item_code=item_code,
                            description=item_meta["description"],
                            action=action,
                            quantity=purchase_qty,
                            unit_cost=unit_price,
                            extended_cost=line_cost,
                            note=note,
                        )
                    )

        return ComputationResult(total_cost=total_cost, rows=rows)

    def _get_inventory_layers(self, item_code: str) -> List[Dict[str, object]]:
        """Lazily load and cache inventory tiers for the requested item."""
        if item_code in self._inventory_cache:
            return self._inventory_cache[item_code]

        filters = {"itemcode__iexact": item_code, "quantityonhand__gt": Decimal("0")}
        if self.warehouse_code != "ALL":
            filters["warehousecode__iexact"] = self.warehouse_code

        raw_layers = list(
            ImItemCost.objects.filter(**filters)
            .values(
                "id",
                "receiptdate",
                "receiptno",
                "unitcost",
                "quantityonhand",
                "warehousecode",
            )
            .order_by("receiptdate", "id")
        )

        layers: List[Dict[str, object]] = []
        for layer in raw_layers:
            qty = self._to_decimal(layer["quantityonhand"])
            unit_cost = self._to_decimal(layer["unitcost"])
            if qty <= Decimal("0"):
                continue

            receipt_date = layer.get("receiptdate")
            date_label = (
                receipt_date.strftime("%Y-%m-%d") if receipt_date else "No Date"
            )
            layers.append(
                {
                    "qty": qty,
                    "unit": unit_cost,
                    "date_label": date_label,
                    "reference": layer.get("receiptno") or "No Ref",
                    "warehouse": layer.get("warehousecode") or "",
                }
            )

        self._inventory_cache[item_code] = layers
        return layers

    def _get_bom_components(self, item_code: str) -> List[Dict[str, Decimal]]:
        """Return BOM component definitions for the provided item."""
        if item_code in self._bom_cache:
            return self._bom_cache[item_code]

        # Try global cache first (loaded once per process)
        if self._global_bom_graph_loaded and self._global_bom_graph:
            components = self._global_bom_graph["bom_by_parent"].get(item_code, [])
            self._bom_cache[item_code] = components
            return components

        # Fallback to DB query if global cache not loaded
        components: List[Dict[str, Decimal]] = []
        for component in BmBillDetail.objects.filter(billno__iexact=item_code).values(
            "componentitemcode", "quantityperbill"
        ):
            quantity = self._to_decimal(component["quantityperbill"])
            if quantity <= Decimal("0"):
                continue

            components.append(
                {
                    "code": (component["componentitemcode"] or "").strip().upper(),
                    "quantity": quantity,
                }
            )

        self._bom_cache[item_code] = components
        return components

    def _get_item_metadata(self, item_code: str) -> Dict[str, object]:
        """Load item metadata for descriptions and fallbacks."""
        key = item_code.upper()
        if key in self._item_cache:
            return self._item_cache[key]

        record = (
            CiItem.objects.filter(itemcode__iexact=key)
            .values("itemcodedesc", "standardunitcost", "procurementtype")
            .first()
        )

        if record:
            metadata = {
                "code": key,
                "description": record.get("itemcodedesc") or key,
                "standard_cost": self._to_decimal(record.get("standardunitcost")),
                "procurement_type": (record.get("procurementtype") or "").strip(),
                "exists": True,
            }
        else:
            metadata = {
                "code": key,
                "description": key,
                "standard_cost": Decimal("0"),
                "procurement_type": "",
                "exists": False,
            }

        self._item_cache[key] = metadata
        return metadata

    @staticmethod
    def _to_decimal(value) -> Decimal:
        """Coerce raw values to Decimal for consistent arithmetic."""
        if value is None:
            return Decimal("0")
        if isinstance(value, Decimal):
            return value
        try:
            return Decimal(str(value))
        except (InvalidOperation, ValueError, TypeError):
            return Decimal("0")
