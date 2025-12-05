from __future__ import annotations
from collections import defaultdict
from dataclasses import dataclass
from decimal import Decimal, InvalidOperation
from typing import Dict, Iterable, List, Optional, Set, Tuple

from core.models import BmBillDetail, CiItem, ImItemCost


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


class BomCostingService:
    """FIFO costing engine backed by the application's PostgreSQL database."""

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

        bom_rows = BmBillDetail.objects.filter(billno__in=missing).values(
            "billno", "componentitemcode", "quantityperbill"
        )
        lookup: Dict[str, List[Dict[str, Decimal]]] = defaultdict(list)
        new_components: Set[str] = set()

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
