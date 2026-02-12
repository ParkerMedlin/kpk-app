"""
Bottle receipt dataset builder (supply-side).

Goal:
- Use Sage 100 extracted SQLite data to measure bottle production receipts into inventory.
- Start from IM_ItemTransactionHistory where TransactionCode == 'BR' for a given ItemCode
  and calendar year.
- Write row-level receipts plus daily/weekly/monthly aggregates as CSVs in ./db.

Notes:
- In this extracted DB, most numeric fields are stored as TEXT; we cast to REAL in queries.
- TransactionDate is stored as YYYY-MM-DD in the extracted DB.
"""

from __future__ import annotations

import argparse
import csv
import sqlite3
from dataclasses import dataclass
from datetime import date, datetime
from pathlib import Path
from typing import List, Optional


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


def _parse_yyyy_mm_dd(s: str) -> date:
    return datetime.strptime(s, "%Y-%m-%d").date()


def _excel_serial(d: date) -> int:
    # Excel's day 0 is 1899-12-30 (due to Excel's historical date system quirks).
    return (d - date(1899, 12, 30)).days


@dataclass(frozen=True)
class BottleReceipt:
    item_code: str
    item_desc: str
    warehouse_code: str
    txn_date: date
    txn_code: str
    qty: float


def _find_repo_root(start: Path) -> Path:
    for p in [start, *start.parents]:
        if (p / "local_machine_scripts" / "sage100sqlite").exists():
            return p
    raise RuntimeError("Could not find repo root (expected local_machine_scripts/sage100sqlite).")


def load_item_desc(cur: sqlite3.Cursor, item_code: str) -> str:
    cur.execute("select ItemCodeDesc from CI_Item where ItemCode = ?", (item_code,))
    row = cur.fetchone()
    return (row[0] or "") if row else ""


def load_bottle_receipts(
    cur: sqlite3.Cursor,
    *,
    year: int,
    item_code: str,
    txn_code: str = "BR",
    warehouse: Optional[str] = None,
    only_positive: bool = True,
) -> List[BottleReceipt]:
    where = [
        "TransactionCode = ?",
        "ItemCode = ?",
        "TransactionDate >= ?",
        "TransactionDate < ?",
        "cast(TransactionQty as real) != 0",
    ]
    params: List[object] = [txn_code, item_code, f"{year:04d}-01-01", f"{year+1:04d}-01-01"]

    if only_positive:
        where.append("cast(TransactionQty as real) > 0")

    if warehouse:
        where.append("WarehouseCode = ?")
        params.append(warehouse)

    cur.execute(
        f"""
        select TransactionDate, TransactionCode, ItemCode, WarehouseCode, TransactionQty
        from IM_ItemTransactionHistory
        where {' and '.join(where)}
        order by TransactionDate
        """,
        params,
    )
    rows = cur.fetchall()
    desc = load_item_desc(cur, item_code=item_code)

    out: List[BottleReceipt] = []
    for txn_date, code, item, wh, qty in rows:
        q = _safe_float(qty)
        if q is None:
            continue
        d = _parse_yyyy_mm_dd(str(txn_date))
        out.append(
            BottleReceipt(
                item_code=str(item),
                item_desc=str(desc),
                warehouse_code=str(wh or ""),
                txn_date=d,
                txn_code=str(code),
                qty=float(q),
            )
        )
    return out


def _write_csv(path: Path, headers: List[str], rows: List[List[object]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(headers)
        w.writerows(rows)


def main(argv: Optional[List[str]] = None) -> int:
    parser = argparse.ArgumentParser(description="Extract bottle receipt (BR) history to CSVs.")
    parser.add_argument("--year", type=int, default=date.today().year - 1)
    parser.add_argument("--item", dest="item_code", default="022001")
    parser.add_argument("--txn-code", default="BR")
    parser.add_argument("--warehouse", default=None)
    parser.add_argument("--db", default=None, help="Path to extracted SQLite db (default: ./db/@sage_data.db or ./db/sage_data.db)")
    parser.add_argument("--include-nonpositive", action="store_true", help="Include non-positive TransactionQty rows.")
    args = parser.parse_args(argv)

    root = _find_repo_root(Path.cwd())
    sage_dir = root / "local_machine_scripts" / "sage100sqlite"
    db_dir = sage_dir / "db"

    db_path: Path
    if args.db:
        db_path = Path(args.db)
    else:
        db_path = db_dir / "@sage_data.db"
        if not db_path.exists():
            db_path = db_dir / "sage_data.db"

    year = int(args.year)
    item_code = str(args.item_code)
    txn_code = str(args.txn_code)

    con = sqlite3.connect(str(db_path))
    cur = con.cursor()
    try:
        receipts = load_bottle_receipts(
            cur,
            year=year,
            item_code=item_code,
            txn_code=txn_code,
            warehouse=args.warehouse,
            only_positive=not args.include_nonpositive,
        )
    finally:
        con.close()

    base = f"bottle_receipts_{item_code}_{year}"
    out_row = db_dir / f"{base}.csv"
    out_daily = db_dir / f"{base}_daily.csv"
    out_weekly = db_dir / f"{base}_weekly.csv"
    out_monthly = db_dir / f"{base}_monthly.csv"

    # Row-level
    _write_csv(
        out_row,
        headers=[
            "itemcode",
            "itemcodedesc",
            "warehousecode",
            "transactiondate_iso",
            "transactiondate",
            "transactioncode",
            "transactionqty",
            "bottles",
        ],
        rows=[
            [
                r.item_code,
                r.item_desc,
                r.warehouse_code,
                r.txn_date.isoformat(),
                _excel_serial(r.txn_date),
                r.txn_code,
                r.qty,
                r.qty,
            ]
            for r in receipts
        ],
    )

    # Daily / weekly / monthly aggregates
    daily: dict[date, float] = {}
    weekly: dict[tuple[int, int], float] = {}
    monthly: dict[tuple[int, int], float] = {}
    for r in receipts:
        daily[r.txn_date] = daily.get(r.txn_date, 0.0) + r.qty
        iso = r.txn_date.isocalendar()
        weekly[(int(iso.year), int(iso.week))] = weekly.get((int(iso.year), int(iso.week)), 0.0) + r.qty
        monthly[(r.txn_date.year, r.txn_date.month)] = monthly.get((r.txn_date.year, r.txn_date.month), 0.0) + r.qty

    _write_csv(
        out_daily,
        headers=["date", "bottles"],
        rows=[[d.isoformat(), q] for d, q in sorted(daily.items())],
    )
    _write_csv(
        out_weekly,
        headers=["iso_year", "iso_week", "bottles"],
        rows=[[y, w, q] for (y, w), q in sorted(weekly.items())],
    )
    _write_csv(
        out_monthly,
        headers=["year", "month", "bottles"],
        rows=[[y, m, q] for (y, m), q in sorted(monthly.items())],
    )

    print(f"DB:      {db_path}")
    print(f"Item:    {item_code} ({txn_code})")
    print(f"Rows:    {len(receipts):,}")
    print(f"Wrote:   {out_row}")
    print(f"Wrote:   {out_daily}")
    print(f"Wrote:   {out_weekly}")
    print(f"Wrote:   {out_monthly}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

