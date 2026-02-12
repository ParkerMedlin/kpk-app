"""
Line capacity dataset builder (sales-side).

Goal:
- Use Sage 100 extracted SQLite data to approximate "sold production" volume by line.
- Start from inventory transaction history where TransactionCode == 'SO' (sales order/shipment)
  and TransactionQty != 0 for a given calendar year (default: last year).
- Explode BOM recursively to find bottle components (CI_Item.ItemCodeDesc like 'BOTTLE-%'),
  including multi-packs/kits where the top-level sold item contains other items that contain bottles.
- Infer bottle size in ounces from the bottle description and compute:
    qty_in_oz = abs(TransactionQty) * bottles_per_unit * bottle_oz
    gallons   = qty_in_oz / 128
- Assign each row to a production line using the user's notebook rules.

This is an approximation: it assumes filled volume corresponds to bottle size, and that 'SO' in
IM_ItemTransactionHistory represents shipped/sold quantities. If you need invoiced/reconciled
amounts, consider extracting invoice history tables instead.
"""

from __future__ import annotations

import argparse
import csv
import re
import sqlite3
from collections import defaultdict
from dataclasses import dataclass
from datetime import date, datetime
from pathlib import Path
from typing import DefaultDict, Dict, Iterable, List, Optional, Tuple


# === Notebook rules (ported from line_capacity_analysis.ipynb) ===

DESCRIPTION_OVERRIDES = [
    # (column, pattern, line, size_predicate)
    # size_predicate is a callable: (bottle_oz: Optional[float]) -> bool
    (None, None, "JB Line", lambda oz: oz == 64),
    ("itemcodedesc", "water shock", "PD Line", None),
    ("itemcodedesc", "water treatment", "PD Line", None),
    ("itemcodedesc", "salt off", "PD Line", None),
    ("itemcodedesc", "salt remov", "PD Line", None),
    ("itemcodedesc", "salt rmv", "PD Line", None),
    ("itemcodedesc", "teak oil", "Inline", lambda oz: oz is not None and oz >= 64),
    ("Bottle", "startron", "Inline", lambda oz: oz is not None and oz < 128),
]


BOTTLE_TO_LINE: Dict[str, str] = {
    # Blister (1oz)
    "BOTTLE-1oz Startron teal blue": "Blister",
    # Inline
    "BOTTLE-4oz Round transblue pvc": "Inline",
    "BOTTLE-4oz round trans orange": "Inline",
    "BOTTLE-8oz STARTRON TRNSBLUE": "Inline",
    "BOTTLE-8oz ST Trans-Org PVC": "Inline",
    "BOTTLE-8oz PVC OVAL WHITE": "Inline",
    "BOTTLE-8oz ST TRANS BLACK PVC": "Inline",
    "BOTTLE-8oz STARTRON WHITE PVC": "Inline",
    "BOTTLE-8oz STARTRON CLEAR": "Inline",
    "BOTTLE-8oz KPK Amsoil clear pv": "Inline",
    "BOTTLE-16oz ST Trans-Org PVC": "Inline",
    "BOTTLE-16oz STARTRN TRNSBLUE P": "Inline",
    "BOTTLE-16oz Stron Trans Black": "Inline",
    "BOTTLE-16oz PVC, WHITE": "Inline",
    "BOTTLE-16oz PVC, CLEAR": "Inline",
    "BOTTLE-16oz BLACK OVAL PVC": "Inline",
    "BOTTLE-16oz PVC, SIKA BLUE": "Inline",
    "BOTTLE-16oz TRANSBLUE OVAL PVC": "Inline",
    "BOTTLE-32oz STARTR TRNS BLUE P": "Inline",
    "BOTTLE-32oz PVC, CLEAR": "Inline",
    "BOTTLE-32oz PVC, WHITE OVAL": "Inline",
    "BOTTLE-32oz White PET Oval": "Inline",
    "BOTTLE-32oz Natural hd round": "Inline",
    "BOTTLE-32oz NAT handled round": "Inline",
    "BOTTLE-32oz Nat HD Tip/Pour": "Inline",
    "BOTTLE-32oz PVC, SIKA BLUE": "Inline",
    "BOTTLE-32oz TRANSBLUE OVAL PVC": "Inline",
    # PD Line
    "BOTTLE-2oz round white PET": "PD Line",
    "BOTTLE-16oz SIKA BLUE PVC SPRY": "PD Line",
    "BOTTLE-16oz WHITE PVC SPRAYER": "PD Line",
    "BOTTLE-16oz BLACK PVC SPRYR": "PD Line",
    "BOTTLE-22oz White pvc": "PD Line",
    "BOTTLE-22oz White PET NO S spr": "PD Line",
    "BOTTLE-22oz Sika Blue": "PD Line",
    "BOTTLE-22oz Black": "PD Line",
    "BOTTLE-22oz Cyan C": "PD Line",
    "BOTTLE-22oz Clear pvc": "PD Line",
    "BOTTLE-22oz Green375C": "PD Line",
    "BOTTLE-22oz RED 185C": "PD Line",
    "BOTTLE-32oz spray White": "PD Line",
    "BOTTLE-32oz sprayer Sika": "PD Line",
    "BOTTLE-32oz sprayer Clear": "PD Line",
    'BOTTLE-32oz White NO "S" spray': "PD Line",
    "BOTTLE-32oz OIL QUART-BLUE": "PD Line",
    "BOTTLE-32oz OIL QUART-BLACK": "PD Line",
    "BOTTLE-32oz OIL QUART-NATURAL": "PD Line",
    # JB Line
    "BOTTLE-F-STYLE WHITE/WHITE": "JB Line",
    "BOTTLE-F-STYLE BLACK GALLON": "JB Line",
    "BOTTLE-F-STYLE BLUE GALLON": "JB Line",
    "BOTTLE-F-STYLE NATURAL": "JB Line",
    "BOTTLE-RIG NATURAL 180 GR": "JB Line",
    "BOTTLE-RIG White Gallon 140gra": "JB Line",
    "BOTTLE-RIGS NATURAL  120gm": "JB Line",
    "BOTTLE-GAL TRANSP BLUE PVC": "JB Line",
    "BOTTLE-GAL SIKA BLUE PVC (38/4": "JB Line",
    "BOTTLE-GAL CLEAR PVC": "JB Line",
    "BOTTLE-GAL WHITE PVC (38/400)": "JB Line",
    "BOTTLE-GAL Orange 165C PVC (38": "JB Line",
    "BOTTLE-2.5 GAL BLACK": "JB Line",
    "BOTTLE-32oz Fstyle WHITE PVC 3": "JB Line",
}


_RE_OZ = re.compile(r"(?P<oz>\d+(?:\.\d+)?)\s*oz\b", re.IGNORECASE)
_RE_GAL = re.compile(r"(?P<gal>\d+(?:\.\d+)?)\s*gal\b", re.IGNORECASE)


def normalize_bottle_desc(bottle_desc: str) -> str:
    """
    Normalize a bottle description for line assignment matching.

    Observed data sometimes appends a trailing numeric identifier (e.g. "... 28").
    For matching against BOTTLE_TO_LINE we strip that suffix.
    """
    s = (bottle_desc or "").strip()
    # Strip trailing numeric token(s) used as identifiers (e.g. " ... 28").
    s = re.sub(r"\s+\d+(?:\.\d+)?\s*$", "", s)
    return s


def _safe_float(v: object) -> Optional[float]:
    if v is None:
        return None
    if isinstance(v, (int, float)):
        return float(v)
    s = str(v).strip()
    if not s:
        return None
    try:
        return float(s)
    except ValueError:
        return None


def infer_bottle_oz(bottle_desc: str) -> Optional[float]:
    """
    Infer bottle size in ounces from the bottle description.
    Handles typical patterns found in CI_Item.ItemCodeDesc.
    """
    if not bottle_desc:
        return None
    s = bottle_desc.strip()

    # Known bottle families whose descriptions omit the size but are gallon containers.
    # Keep this tight: only the patterns we've observed in BOM bottle descriptions.
    if s in {
        "BOTTLE-F-STYLE NATURAL",
        "BOTTLE-F-STYLE WHITE/WHITE",
        "BOTTLE-RIG NATURAL 180 GR",
        "BOTTLE-RIGS NATURAL  120gm",
    }:
        return 128.0

    m = _RE_GAL.search(s)
    if m:
        gal = _safe_float(m.group("gal"))
        if gal is not None:
            return gal * 128.0

    # Common text patterns without explicit "1 gal"
    if re.search(r"\bgallon\b", s, re.IGNORECASE) or re.search(r"\bgal\b", s, re.IGNORECASE):
        # If it didn't match a numeric 'X gal', assume 1 gallon.
        return 128.0

    if re.search(r"\bquart\b", s, re.IGNORECASE):
        return 32.0

    m = _RE_OZ.search(s)
    if m:
        oz = _safe_float(m.group("oz"))
        if oz is not None:
            return oz

    return None
def assign_line(
    itemcode: str,
    itemcodedesc: str,
    bottle_desc: str,
    bottle_oz: Optional[float],
    *,
    fogg_item_codes: Optional[set[str]] = None,
) -> str:
    # Rule 1 (highest priority): explicit itemcode -> line mapping (Fogg list)
    if fogg_item_codes is not None and itemcode in fogg_item_codes:
        return "Fogg"

    itemcodedesc_l = (itemcodedesc or "").lower()
    bottle_l = (bottle_desc or "").lower()

    # Rule 2 (description overrides), applied before bottle map.
    # Later overrides win: we keep scanning and replace when matched.
    override: Optional[str] = None
    for col, pat, line, size_pred in DESCRIPTION_OVERRIDES:
        if size_pred is not None and not size_pred(bottle_oz):
            continue

        if col is None:
            matched = True
        elif col == "itemcodedesc":
            matched = pat in itemcodedesc_l
        elif col == "Bottle":
            matched = pat in bottle_l
        else:
            matched = False

        if matched:
            override = line

    if override:
        return override

    # Rule 3 (bottle map fallback)
    line = BOTTLE_TO_LINE.get(bottle_desc)
    if not line:
        line = BOTTLE_TO_LINE.get(normalize_bottle_desc(bottle_desc))
    if line:
        return line

    return "UNASSIGNED"


def load_fogg_item_codes(path: Path) -> set[str]:
    """
    Loads item codes (one per line). File may be a "real csv" or just a newline list.
    """
    if not path.exists():
        return set()

    # Try CSV first; if there's just one column of raw codes, this still works.
    codes: set[str] = set()
    with path.open("r", encoding="utf-8-sig", newline="") as f:
        sample = f.read(2048)
        f.seek(0)
        # Heuristic: if there's a comma in first line, use csv.reader; otherwise line-split.
        first_line = sample.splitlines()[0] if sample.splitlines() else ""
        if "," in first_line:
            reader = csv.reader(f)
            for row in reader:
                if not row:
                    continue
                code = (row[0] or "").strip().strip('"').strip("'")
                if code:
                    codes.add(code)
        else:
            for line in f:
                code = line.strip().strip('"').strip("'")
                if code:
                    codes.add(code)
    return codes


@dataclass(frozen=True)
class Txn:
    transaction_date: str
    transaction_code: str
    item_code: str
    item_desc: str
    warehouse_code: str
    qty: float  # Sage convention: often negative for issues (sales shipments)
    unit_cost: float
    extended_cost: float


def load_ci_item_descriptions(cur: sqlite3.Cursor) -> Dict[str, str]:
    cur.execute("select ItemCode, ItemCodeDesc from CI_Item")
    return {code: (desc or "") for code, desc in cur.fetchall()}


def load_bom_edges(cur: sqlite3.Cursor) -> Dict[str, List[Tuple[str, float]]]:
    # Note: types are stored as TEXT in this extracted DB.
    cur.execute("select BillNo, ComponentItemCode, QuantityPerBill from BM_BillDetail")
    edges: Dict[str, List[Tuple[str, float]]] = defaultdict(list)
    for bill_no, comp_code, qty_per_bill in cur.fetchall():
        if not bill_no or not comp_code:
            continue
        qty = _safe_float(qty_per_bill)
        if qty is None or qty == 0:
            continue
        edges[str(bill_no)].append((str(comp_code), float(qty)))
    return edges


def load_sales_transactions(
    cur: sqlite3.Cursor,
    year: int,
    warehouse: Optional[str] = None,
    *,
    only_inventory_issues: bool = True,
) -> List[Txn]:
    where = [
        "TransactionCode = 'SO'",
        "TransactionDate >= ?",
        "TransactionDate < ?",
        "cast(TransactionQty as real) != 0",
    ]
    if only_inventory_issues:
        # In this dataset, SO issues (shipments/invoiced) are negative; positive is return-like.
        where.append("cast(TransactionQty as real) < 0")
    params: List[object] = [f"{year:04d}-01-01", f"{year+1:04d}-01-01"]
    if warehouse:
        where.append("WarehouseCode = ?")
        params.append(warehouse)

    cur.execute(
        f"""
        select TransactionDate, TransactionCode, ItemCode, WarehouseCode, TransactionQty, UnitCost, ExtendedCost
        from IM_ItemTransactionHistory
        where {' and '.join(where)}
        """,
        params,
    )
    rows = cur.fetchall()

    # We'll join CI_Item separately for descriptions (faster overall for repeated use).
    return [
        Txn(
            transaction_date=str(d),
            transaction_code=str(code),
            item_code=str(item),
            item_desc="",
            warehouse_code=str(wh),
            qty=float(_safe_float(qty) or 0.0),
            unit_cost=float(_safe_float(unit_cost) or 0.0),
            extended_cost=float(_safe_float(ext_cost) or 0.0),
        )
        for (d, code, item, wh, qty, unit_cost, ext_cost) in rows
    ]


def explode_bottles_for_item(
    top_item: str,
    bom_edges: Dict[str, List[Tuple[str, float]]],
    item_desc_by_code: Dict[str, str],
    *,
    max_depth: int = 12,
) -> Dict[str, float]:
    """
    Returns mapping: bottle_desc -> bottles_per_top_item (can be fractional in odd BOMs).
    """
    out: DefaultDict[str, float] = defaultdict(float)

    # Depth-limited DFS; also avoid obvious cycles.
    stack: List[Tuple[str, float, int, Tuple[str, ...]]] = [(top_item, 1.0, 0, (top_item,))]
    while stack:
        code, mult, depth, path = stack.pop()
        if depth >= max_depth:
            continue
        comps = bom_edges.get(code)
        if not comps:
            continue

        for comp_code, qty_per in comps:
            mult2 = mult * qty_per
            if mult2 == 0:
                continue
            desc = item_desc_by_code.get(comp_code, "")
            if desc.startswith("BOTTLE-"):
                out[desc] += mult2
                continue

            # Recurse only if the component itself has a BOM.
            if comp_code in bom_edges:
                if comp_code in path:
                    continue
                stack.append((comp_code, mult2, depth + 1, path + (comp_code,)))

    return dict(out)


def _iso_week(d: date) -> int:
    # Python's isocalendar week
    return int(d.isocalendar().week)


def _parse_yyyy_mm_dd(s: str) -> date:
    return datetime.strptime(s, "%Y-%m-%d").date()


def _excel_serial(d: date) -> int:
    # Excel's day 0 is 1899-12-30 (due to Excel's historical date system quirks).
    return (d - date(1899, 12, 30)).days


def main() -> int:
    # Prefer a local working copy name if present, but fall back to the default.
    default_db = Path(__file__).parent / "db" / "@sage_data.db"
    if not default_db.exists():
        default_db = Path(__file__).parent / "db" / "sage_data.db"

    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--db",
        default=str(default_db),
        help="Path to sage_data.db (or @sage_data.db)",
    )
    parser.add_argument(
        "--year",
        type=int,
        default=(date.today().year - 1),
        help="Calendar year to extract (default: last year)",
    )
    parser.add_argument(
        "--warehouse",
        default=None,
        help="Optional WarehouseCode filter (e.g. MTG)",
    )
    parser.add_argument(
        "--out",
        default=None,
        help="Output CSV path (default: ./db/line_capacity_sales_<year>.csv)",
    )
    parser.add_argument(
        "--fogg-csv",
        default=str(Path(__file__).parent / "fogg_item_codes.csv"),
        help="Path to fogg_item_codes.csv (item codes that should be forced to line=Fogg)",
    )
    args = parser.parse_args()

    db_path = Path(args.db)
    if not db_path.exists():
        raise SystemExit(f"DB not found: {db_path}")

    out_path = Path(args.out) if args.out else (db_path.parent / f"line_capacity_sales_{args.year}.csv")

    con = sqlite3.connect(str(db_path))
    con.row_factory = sqlite3.Row
    cur = con.cursor()

    item_desc_by_code = load_ci_item_descriptions(cur)
    bom_edges = load_bom_edges(cur)
    txns = load_sales_transactions(cur, args.year, warehouse=args.warehouse)
    fogg_codes = load_fogg_item_codes(Path(args.fogg_csv))

    # Fill item descriptions (top-level)
    txns = [
        Txn(
            transaction_date=t.transaction_date,
            transaction_code=t.transaction_code,
            item_code=t.item_code,
            item_desc=item_desc_by_code.get(t.item_code, ""),
            warehouse_code=t.warehouse_code,
            qty=t.qty,
            unit_cost=t.unit_cost,
            extended_cost=t.extended_cost,
        )
        for t in txns
    ]

    bottle_cache: Dict[str, Dict[str, float]] = {}

    out_rows: List[Dict[str, object]] = []
    missing_bottle = 0
    missing_bottle_by_item: DefaultDict[str, Dict[str, object]] = defaultdict(lambda: {"rows": 0, "ship_units": 0.0})
    for t in txns:
        bottle_map = bottle_cache.get(t.item_code)
        if bottle_map is None:
            bottle_map = explode_bottles_for_item(t.item_code, bom_edges, item_desc_by_code)
            bottle_cache[t.item_code] = bottle_map

        if not bottle_map:
            missing_bottle += 1
            rec = missing_bottle_by_item[t.item_code]
            rec["rows"] = int(rec["rows"]) + 1
            rec["ship_units"] = float(rec["ship_units"]) + (-t.qty)
            continue

        # Shipment units (positive scalar).
        qty_units = -t.qty

        d = _parse_yyyy_mm_dd(t.transaction_date)
        for bottle_desc, bottles_per_unit in bottle_map.items():
            oz = infer_bottle_oz(bottle_desc)
            if oz is None:
                continue
            bottle_units = qty_units * bottles_per_unit
            qty_in_oz = bottle_units * oz
            gallons = qty_in_oz / 128.0
            line = assign_line(
                t.item_code,
                t.item_desc,
                bottle_desc,
                oz,
                fogg_item_codes=fogg_codes,
            )

            out_rows.append(
                {
                    "itemcode": t.item_code,
                    "itemcodedesc": t.item_desc,
                    "Bottle": bottle_desc,
                    "bottle_oz": oz,
                    "qtyperbill": bottles_per_unit,
                    "qty_in_oz": qty_in_oz,
                    "transactiondate": _excel_serial(d),
                    "transactioncode": t.transaction_code,
                    "transactionqty": t.qty,  # signed
                    "unitcost": t.unit_cost,
                    "extendedcost": t.extended_cost,
                    "line": line,
                    # Keep a few computed fields for rollups only (not written to main CSV)
                    "_iso_week": _iso_week(d),
                    "_month": d.month,
                    "_gallons": gallons,
                    "_warehouse": t.warehouse_code,
                    "_bottle_units": bottle_units,
                }
            )

    con.close()

    out_path.parent.mkdir(parents=True, exist_ok=True)
    cols = [
        "itemcode",
        "itemcodedesc",
        "Bottle",
        "bottle_oz",
        "qtyperbill",
        "qty_in_oz",
        "transactiondate",
        "transactioncode",
        "transactionqty",
        "unitcost",
        "extendedcost",
        "line",
    ]
    with out_path.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=cols)
        w.writeheader()
        for r in out_rows:
            w.writerow({k: r.get(k) for k in cols})

    # Rollups
    weekly_by_line: DefaultDict[Tuple[str, int], float] = defaultdict(float)
    monthly_by_line: DefaultDict[Tuple[str, int], float] = defaultdict(float)
    yearly_by_line: DefaultDict[str, float] = defaultdict(float)
    for r in out_rows:
        line = str(r["line"])
        wk = int(r["_iso_week"])
        mo = int(r["_month"])
        gal = float(r["_gallons"])
        weekly_by_line[(line, wk)] += gal
        monthly_by_line[(line, mo)] += gal
        yearly_by_line[line] += gal

    weekly_path = out_path.with_name(out_path.stem + "_weekly.csv")
    with weekly_path.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=["line", "iso_week", "gallons"])
        w.writeheader()
        for (line, wk), gal in sorted(weekly_by_line.items(), key=lambda kv: (kv[0][0], kv[0][1])):
            w.writerow({"line": line, "iso_week": wk, "gallons": gal})

    monthly_path = out_path.with_name(out_path.stem + "_monthly.csv")
    with monthly_path.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=["line", "month", "gallons"])
        w.writeheader()
        for (line, mo), gal in sorted(monthly_by_line.items(), key=lambda kv: (kv[0][0], kv[0][1])):
            w.writerow({"line": line, "month": mo, "gallons": gal})

    missing_path = out_path.with_name(out_path.stem + "_missing_bottle.csv")
    with missing_path.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=["itemcode", "itemcodedesc", "txn_rows", "ship_units"])
        w.writeheader()
        # Sort by shipped units descending
        rows = []
        for itemcode, rec in missing_bottle_by_item.items():
            rows.append(
                (
                    float(rec["ship_units"]),
                    {
                        "itemcode": itemcode,
                        "itemcodedesc": item_desc_by_code.get(itemcode, ""),
                        "txn_rows": int(rec["rows"]),
                        "ship_units": float(rec["ship_units"]),
                    },
                )
            )
        for _, row in sorted(rows, key=lambda x: x[0], reverse=True):
            w.writerow(row)

    # Lightweight rollups to stderr/stdout
    totals_by_line: DefaultDict[str, float] = defaultdict(float)
    for r in out_rows:
        totals_by_line[str(r["line"])] += float(r["_gallons"])

    total_gal = sum(totals_by_line.values())
    print(f"Wrote: {out_path}")
    print(f"Wrote: {weekly_path}")
    print(f"Wrote: {monthly_path}")
    print(f"Wrote: {missing_path}")
    print(f"Source txns: {len(txns):,} (SO, qty<0, year={args.year}, warehouse={args.warehouse or 'ANY'})")
    print(f"Txns skipped (no bottle mapping): {missing_bottle:,}")
    print(f"Output rows (txn exploded by bottle): {len(out_rows):,}")
    print(f"Total gallons (approx): {total_gal:,.0f}")
    print("Gallons by line:")
    for line, gal in sorted(totals_by_line.items(), key=lambda kv: kv[1], reverse=True):
        pct = (gal / total_gal * 100.0) if total_gal else 0.0
        print(f"  {line:12s}  {gal:12,.0f}  ({pct:5.1f}%)")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
