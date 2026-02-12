#!/usr/bin/env python
# coding: utf-8

# # Production Line Capacity Analysis
# 
# **Goal:** Assign every produced item to a production line (Inline, PD Line, JB Line, Fogg, Blister) based on item code and bottle type, then analyze capacity by line.
# 
# **How this notebook works:**
# - Each gray box below is a "cell" you can run
# - Click a cell, then press **Shift+Enter** to run it and move to the next
# - Or press **Ctrl+Enter** to run it and stay on it
# - Run cells top to bottom — later cells depend on earlier ones
# - Green text starting with `#` are comments (notes to yourself, not code)

# ## 1. Setup & Load Data

# In[1]:


import polars as pl
from datetime import date
from pathlib import Path
import subprocess
import sys

def _find_repo_root(start: Path) -> Path:
    for p in [start, *start.parents]:
        if (p / 'local_machine_scripts' / 'sage100sqlite').exists():
            return p
    raise RuntimeError('Could not find repo root (expected local_machine_scripts/sage100sqlite).')

ROOT = _find_repo_root(Path.cwd())
SAGE_DIR = ROOT / 'local_machine_scripts' / 'sage100sqlite'
DB_DIR = SAGE_DIR / 'db'

# Prefer @sage_data.db if present, else sage_data.db
DB_PATH = DB_DIR / '@sage_data.db'
if not DB_PATH.exists():
    DB_PATH = DB_DIR / 'sage_data.db'

YEAR = date.today().year - 1  # default: last year (e.g. 2025)
CSV_PATH = DB_DIR / f'line_capacity_sales_{YEAR}.csv'
EXTRACT_PY = SAGE_DIR / 'line_capacity_sales_extract.py'

if not CSV_PATH.exists():
    print(f'Missing base dataset: {CSV_PATH}')
    print('Generating it now from SQLite...')
    subprocess.run(
        [sys.executable, str(EXTRACT_PY), '--db', str(DB_PATH), '--year', str(YEAR)],
        check=True,
    )

if not CSV_PATH.exists():
    raise FileNotFoundError(
        f'Base dataset still missing after generation attempt: {CSV_PATH}\n'
        f'Try running: python "{EXTRACT_PY}" --db "{DB_PATH}" --year {YEAR}'
    )

so_txns = pl.read_csv(CSV_PATH)

# Keep the extractor's line assignment for comparison.
if 'line' in so_txns.columns:
    so_txns = so_txns.rename({'line': 'line_script'})

# Notebook later does so_txns.drop('line'); add a placeholder if needed.
if 'line' not in so_txns.columns:
    so_txns = so_txns.with_columns(pl.lit(None).alias('line'))

# Rule 1 item codes (Fogg)
fogg_path = SAGE_DIR / 'fogg_item_codes.csv'
fogg_codes = [c.strip() for c in fogg_path.read_text(encoding='utf-8').splitlines() if c.strip()]
existing_rules = pl.DataFrame({'itemcode': fogg_codes, 'line': ['Fogg'] * len(fogg_codes)})

print(f'DB:           {DB_PATH}')
print(f'Dataset CSV:  {CSV_PATH}')
print(f'SO rows:      {so_txns.shape[0]:,} ({so_txns["itemcode"].n_unique()} unique items)')
print(f'Rule 1 codes: {existing_rules.shape[0]} item codes (Fogg)')


# ## 2. Line Assignment Rules
# 
# Rules are applied in priority order:
# 1. **Item code lookup** — explicit item-to-line mapping (currently Fogg aerosol items)
# 2. **Product description overrides** — keywords in `itemcodedesc` force a line regardless of bottle:
#    - "water shock" or "water treatment" → **PD Line**
#    - "teak oil" in gallon/64oz+ → **Inline** (overrides the normal JB Line gallon rule)
# 3. **Bottle type lookup** — bottle name maps to a line
# 4. **Fallback** — anything left gets `"UNASSIGNED"`

# In[2]:


# ============================================================
# RULE 2: Pattern + size overrides
# ============================================================
# Applied AFTER item code lookup, BEFORE bottle-type map.
# Later entries in this list take priority over earlier ones,
# so put general rules first and specific exceptions after.
#
# Each entry: (column, pattern, line, size_expr)
#   - column: "itemcodedesc", "Bottle", or None (match everything)
#   - pattern: substring to match (lowercased), ignored if column is None
#   - line: which production line
#   - size_expr: None = all sizes, or a native Polars expression

DESCRIPTION_OVERRIDES = [
    # --- General size rules (lowest priority, listed first) ---
    (None,           None,              "JB Line", pl.col("bottle_oz") == 64),   # all 64oz -> JB

    # --- Product-specific exceptions (override the general rules above) ---
    ("itemcodedesc", "water shock",     "PD Line", None),                        # any size
    ("itemcodedesc", "water treatment", "PD Line", None),                        # any size
    ("itemcodedesc", "water freshener", "PD Line", None),                        # any size
    ("itemcodedesc", "salt off",        "PD Line", None),                        # any size
    ("itemcodedesc", "salt remov",      "PD Line", None),                        # any size (Seachoice)
    ("itemcodedesc", "salt rmv",        "PD Line", None),                        # any size (Australia)
    ("itemcodedesc", "salt off",        "JB Line", pl.col("bottle_oz") >= 64),   # 64oz+ Salt Off runs on JB
    ("itemcodedesc", "salt remov",      "JB Line", pl.col("bottle_oz") >= 64),   # 64oz+ Salt Remover runs on JB
    ("itemcodedesc", "salt rmv",        "JB Line", pl.col("bottle_oz") >= 64),   # 64oz+ Salt Rmv runs on JB
    ("itemcodedesc", "teak oil",        "Inline",  pl.col("bottle_oz") >= 64),   # 64oz+ only
    ("Bottle",       "startron",        "Inline",  pl.col("bottle_oz") < 128),   # non-gallon
]

# ============================================================
# RULE 1: Item code -> Line  (explicit overrides, highest priority)
# ============================================================
EXTRA_ITEM_RULES = {
    # "SOME-ITEMCODE": "JB Line",
}

item_to_line = dict(zip(
    existing_rules["itemcode"].to_list(),
    existing_rules["line"].to_list()
))
item_to_line.update(EXTRA_ITEM_RULES)

# Build the override as a single Polars expression chain.
# Later entries wrap earlier ones, so they take priority.
desc_override_expr = pl.lit(None).cast(pl.Utf8)
for _col, _pat, _line, _size in DESCRIPTION_OVERRIDES:
    if _col is not None:
        _cond = pl.col(_col).str.to_lowercase().str.contains(_pat)
    else:
        _cond = pl.lit(True)
    if _size is not None:
        _cond = _cond & _size
    desc_override_expr = pl.when(_cond).then(pl.lit(_line)).otherwise(desc_override_expr)
desc_override_expr = desc_override_expr.alias("line_from_desc")

print(f"Item-level rules: {len(item_to_line)} total")
print(f"Override patterns: {len(DESCRIPTION_OVERRIDES)} (later entries win)")

# Preview matches
for _col, _pat, _line, _size in DESCRIPTION_OVERRIDES:
    q = so_txns.lazy()
    if _col is not None:
        q = q.filter(pl.col(_col).str.to_lowercase().str.contains(_pat))
    if _size is not None:
        q = q.filter(_size)
    result = q.select(pl.col("itemcode").n_unique().alias("items"), pl.len().alias("rows")).collect()
    col_label = f'{_col} ~ "{_pat}"' if _col else "all items"
    size_label = f" + size filter" if _size is not None else ""
    print(f"  {col_label}{size_label} -> {_line}: {result['items'][0]} items, {result['rows'][0]} rows")


# In[3]:


# ============================================================
# RULE 3: Bottle type -> Line
# ============================================================
# Fallback after item codes and pattern/size overrides.
# 64oz bottles are handled by the size override (Rule 2) so
# they don't appear here.
#
# PD Line = spray triggers ONLY. All other cap types
# (flip top, pump top, screw cap, tip-and-pour, vent) → Inline.

BOTTLE_TO_LINE = {
    # --- Blister (1oz) ---
    "BOTTLE-1oz Startron teal blue":       "Blister",

    # --- Inline (small bottles + all non-sprayer 16oz/32oz) ---
    "BOTTLE-4oz Round transblue pvc":       "Inline",
    "BOTTLE-4oz round trans orange":        "Inline",
    "BOTTLE-8oz STARTRON TRNSBLUE":         "Inline",
    "BOTTLE-8oz ST Trans-Org PVC":          "Inline",
    "BOTTLE-8oz ROUND PVC Clear":           "Inline",
    "BOTTLE-8oz ROUND natural HDPE":        "Inline",
    "BOTTLE-8oz PVC OVAL WHITE":            "Inline",
    "BOTTLE-8oz ST TRANS BLACK PVC":        "Inline",
    "BOTTLE-8oz STARTRON WHITE PVC":        "Inline",
    "BOTTLE-8oz STARTRON CLEAR":            "Inline",
    "BOTTLE-8oz KPK Amsoil clear pv":       "Inline",
    "BOTTLE-16oz ST Trans-Org PVC":         "Inline",
    "BOTTLE-16oz STARTRN TRNSBLUE P":       "Inline",
    "BOTTLE-16oz Stron Trans Black":        "Inline",
    "BOTTLE-16oz PVC, WHITE":               "Inline",
    "BOTTLE-16oz PVC, CLEAR":               "Inline",
    "BOTTLE-16oz BLACK OVAL PVC":           "Inline",
    "BOTTLE-16oz PVC, SIKA BLUE":           "Inline",
    "BOTTLE-16oz TRANSBLUE OVAL PVC":       "Inline",
    "BOTTLE-32oz STARTR TRNS BLUE P":       "Inline",
    "BOTTLE-32oz PVC, CLEAR":               "Inline",
    "BOTTLE-32oz PVC, WHITE OVAL":          "Inline",
    "BOTTLE-32oz White PET Oval":           "Inline",
    "BOTTLE-32oz Natural hd round":         "Inline",
    "BOTTLE-32oz NAT handled round":        "Inline",
    "BOTTLE-32oz Nat HD Tip/Pour":          "Inline",
    "BOTTLE-32oz PVC, SIKA BLUE":           "Inline",
    "BOTTLE-32oz TRANSBLUE OVAL PVC":       "Inline",

    # --- PD Line (sprayers, triggers, oil quarts) ---
    "BOTTLE-2oz round white PET":           "PD Line",
    "BOTTLE-16oz ROUND PVC Clear":          "PD Line",
    "BOTTLE-16oz NAT ROUND HDPE":           "PD Line",
    "BOTTLE-16oz SIKA BLUE PVC SPRY":       "PD Line",
    "BOTTLE-16oz WHITE PVC SPRAYER":        "PD Line",
    "BOTTLE-16oz BLACK PVC SPRYR":          "PD Line",
    "BOTTLE-22oz White pvc":                "PD Line",
    "BOTTLE-22oz White PET NO S spr":       "PD Line",
    "BOTTLE-22oz Sika Blue":                "PD Line",
    "BOTTLE-22oz Black":                    "PD Line",
    "BOTTLE-22oz Cyan C":                   "PD Line",
    "BOTTLE-22oz Clear pvc":                "PD Line",
    "BOTTLE-22oz Green375C":                "PD Line",
    "BOTTLE-22oz RED 185C":                 "PD Line",
    "BOTTLE-32oz spray White":              "PD Line",
    "BOTTLE-32oz sprayer Sika":             "PD Line",
    "BOTTLE-32oz sprayer Clear":            "PD Line",
    'BOTTLE-32oz White NO "S" spray':       "PD Line",
    "BOTTLE-32oz Fstyle CLEAR PVC":         "PD Line",
    "BOTTLE-32oz Fstyle WHITE PVC 3":       "PD Line",
    "BOTTLE-32oz OIL QUART-BLUE":           "PD Line",
    "BOTTLE-32oz OIL QUART-BLACK":          "PD Line",
    "BOTTLE-32oz OIL QUART-NATURAL":        "PD Line",

    # --- JB Line (gallons, F-style jugs) ---
    "BOTTLE-F-STYLE WHITE/WHITE":           "JB Line",
    "BOTTLE-F-STYLE BLACK GALLON":          "JB Line",
    "BOTTLE-F-STYLE BLUE GALLON":           "JB Line",
    "BOTTLE-F-STYLE NATURAL":               "JB Line",
    "BOTTLE-RIG NATURAL 180 GR":            "JB Line",
    "BOTTLE-RIG White Gallon 140gra":       "JB Line",
    "BOTTLE-RIGS NATURAL  120gm":           "JB Line",
    "BOTTLE-GAL TRANSP BLUE PVC":           "JB Line",
    "BOTTLE-GAL SIKA BLUE PVC (38/4":       "JB Line",
    "BOTTLE-GAL CLEAR PVC":                 "JB Line",
    "BOTTLE-GAL WHITE PVC (38/400)":        "JB Line",
    "BOTTLE-GAL Orange 165C PVC (38":       "JB Line",
    "BOTTLE-2.5 GAL BLACK":                 "JB Line",
}

print(f"Bottle-level rules: {len(BOTTLE_TO_LINE)}")


# ## 3. Apply Rules

# In[4]:


def assign_line(df: pl.DataFrame) -> pl.DataFrame:
    """Apply line assignment rules in priority order:
    1. Item code exact match
    2. Description overrides (keyword + optional size filter)
    3. Bottle type map
    4. UNASSIGNED fallback
    """
    item_map = pl.LazyFrame({
        "itemcode": list(item_to_line.keys()),
        "line_from_item": list(item_to_line.values()),
    })
    bottle_map = pl.LazyFrame({
        "Bottle": list(BOTTLE_TO_LINE.keys()),
        "line_from_bottle": list(BOTTLE_TO_LINE.values()),
    })

    return (
        df.lazy()
        .join(item_map, on="itemcode", how="left")
        .join(bottle_map, on="Bottle", how="left")
        .with_columns(desc_override_expr)
        .with_columns(
            pl.coalesce("line_from_item", "line_from_desc", "line_from_bottle")
              .fill_null("UNASSIGNED")
              .alias("line")
        )
        .drop("line_from_item", "line_from_desc", "line_from_bottle")
        .collect()
    )

so = assign_line(so_txns.drop("line"))

print("=== SO Transactions ===")
print(so.group_by("line").len().sort("len", descending=True))

# If the base dataset came from line_capacity_sales_extract.py, compare its line assignment
# (line_script) to what the notebook rules produce.
if "line_script" in so.columns:
    mismatches = so.filter(pl.col("line_script") != pl.col("line"))
    if mismatches.height:
        print()
        print("=== Notebook vs Extractor Line Differences ===")
        print(f"Mismatched rows: {mismatches.height:,}")
        print(
            mismatches
            .group_by(["line_script", "line"])
            .len()
            .sort("len", descending=True)
        )
    else:
        print()
        print("Notebook line assignments match extractor (no mismatches).")


# Quick sanity check: Salt Off 64oz+ should be JB Line
salt_off_large = (
    so.lazy()
    .filter(
        pl.col("itemcodedesc").str.to_lowercase().str.contains("salt off")
        & (pl.col("bottle_oz") >= 64)
    )
    .select(["itemcode", "itemcodedesc", "Bottle", "bottle_oz", "line_script", "line"])
    .unique()
    .collect()
)

if salt_off_large.height:
    print()
    print("=== Salt Off (64oz+/gallon) Line Check ===")
    print(salt_off_large.group_by(["line_script", "line"]).len().sort("len", descending=True))
    not_jb = salt_off_large.filter(pl.col("line") != "JB Line")
    if not_jb.height:
        print()
        print("Items NOT on JB Line (per notebook rules):")
        with pl.Config(tbl_rows=50, tbl_width_chars=200):
            print(not_jb.sort(["bottle_oz", "itemcode"]))
else:
    print()
    print("No Salt Off 64oz+ rows found in dataset.")


# ## 4. Find the Gaps
# 
# These are items still marked `UNASSIGNED`. Use this to figure out what rules to add.

# In[5]:


# Unassigned SO items grouped by bottle type
so_gaps = (
    so.lazy()
    .filter(pl.col("line") == "UNASSIGNED")
    .group_by("Bottle")
    .agg(
        pl.len().alias("rows"),
        pl.col("itemcode").n_unique().alias("unique_items"),
        pl.col("transactionqty").sum().alias("total_qty"),
    )
    .sort("rows", descending=True)
    .collect()
)

print("Unassigned SO rows by bottle type:")
with pl.Config(tbl_rows=50):
    print(so_gaps)


# In[6]:


# Drill into a specific bottle type to see the actual items
# Change the string below to explore different bottle types
BOTTLE_TO_INSPECT = "BOTTLE-16oz NAT ROUND HDPE"

detail = (
    so.lazy()
    .filter(
        (pl.col("line") == "UNASSIGNED") &
        (pl.col("Bottle") == BOTTLE_TO_INSPECT)
    )
    .group_by("itemcode", "itemcodedesc", "Bottle", "bottle_oz")
    .agg(pl.col("transactionqty").sum().alias("total_qty"))
    .sort("total_qty", descending=True)
    .collect()
)

with pl.Config(tbl_rows=100, tbl_width_chars=200):
    print(detail)


# ### Blend & Cap Investigation
# 
# For bottle types where the line depends on the blend, this shows the blend and cap components from the BOM for each unassigned item.

# In[7]:


import sqlite3

# Load BOM from SQLite (BM_BillDetail joined to CI_Item for component descriptions)
con = sqlite3.connect(str(DB_PATH))
cur = con.cursor()
cur.execute(
    """
    select
        bd.BillNo as item_code,
        bd.ComponentItemCode as component_item_code,
        ci.ItemCodeDesc as component_item_description
    from BM_BillDetail bd
    left join CI_Item ci
        on ci.ItemCode = bd.ComponentItemCode
    """
)
rows = cur.fetchall()
con.close()

bom = pl.DataFrame(
    rows,
    schema=['item_code', 'component_item_code', 'component_item_description'],
    orient="row",
)

print(f'BOM rows: {bom.shape[0]:,}')


# ## 6. Line Capacity Analysis
# 
# Once your rules are solid, these cells give you production volume by line.

# ## 5. Preview Assigned Data
# 
# Spot-check the assignments before doing any analysis. Nothing is written to disk — this is just output in your browser.

# In[8]:


# Preview: sample of assigned rows per line
for line_name in ["Inline", "PD Line", "JB Line", "Fogg", "Blister"]:
    sample = (
        so.filter(pl.col("line") == line_name)
        .select(["itemcode", "itemcodedesc", "Bottle", "bottle_oz", "line"])
        .unique()
        .head(5)
    )
    print(f"\n--- {line_name} (sample) ---")
    with pl.Config(tbl_width_chars=200):
        print(sample)

# Show assignment coverage
total = so.height
assigned = so.filter(pl.col("line") != "UNASSIGNED").height
pct = assigned / total * 100
print(f"\nCoverage: {assigned:,} / {total:,} rows assigned ({pct:.1f}%)")
print(f"Remaining: {total - assigned:,} rows need rules")


# In[9]:


# SO data summary by line
line_summary = (
    so.lazy()
    .filter(pl.col("line") != "UNASSIGNED")
    .group_by("line")
    .agg(
        pl.len().alias("total_txns"),
        pl.col("itemcode").n_unique().alias("unique_items"),
        pl.col("transactionqty").sum().alias("total_units"),
        pl.col("extendedcost").sum().round(2).alias("total_cost"),
    )
    .sort("total_units", descending=True)
    .collect()
)

print("Production by line (SO transactions, 2025):")
print(line_summary)


# In[10]:


# Monthly SO volume by line
monthly_pivot = (
    so.lazy()
    .filter(pl.col("line") != "UNASSIGNED")
    .with_columns(
        (pl.col("transactiondate") % 10000 // 100).cast(pl.Int32).alias("month")
    )
    .group_by("line", "month")
    .agg(
        pl.col("transactionqty").sum().alias("units"),
    )
    .collect()
    .pivot(on="line", index="month", values="units")
    .fill_null(0)
    .sort("month")
)

print("Monthly units by line:")
with pl.Config(tbl_width_chars=200):
    print(monthly_pivot)


# In[11]:


# What bottle sizes run on each line?
size_mix = (
    so.lazy()
    .filter(pl.col("line") != "UNASSIGNED")
    .group_by("line", "bottle_oz")
    .agg(pl.col("transactionqty").sum().alias("units"))
    .sort("line", "bottle_oz")
    .collect()
)

with pl.Config(tbl_rows=60):
    print(size_mix)


# ## 6b. Gallon Volume Analysis
# 
# Convert `qty_in_oz` to gallons (128 oz/gal) and look at overall, monthly, and weekly averages per line.

# In[11]:


from datetime import date

so_gal = (
    so.lazy()
    .with_columns(
        ((pl.col("transactiondate").cast(pl.Int32) - 25569) * 86_400_000_000)
            .cast(pl.Datetime("us")).cast(pl.Date).alias("date"),
        (pl.col("qty_in_oz") / 128).alias("gallons"),
    )
    .with_columns(
        pl.col("date").dt.month().alias("month"),
        pl.col("date").dt.iso_year().alias("yr"),
        pl.col("date").dt.week().alias("week"),
    )
    .collect()
)

# Overall totals by line
line_totals = (
    so_gal.lazy()
    .group_by("line")
    .agg(
        pl.len().alias("records"),
        pl.col("gallons").sum().round(0).alias("total_gal"),
    )
    .sort("total_gal", descending=True)
    .with_columns(
        (pl.col("total_gal") / pl.col("total_gal").sum() * 100).round(1).alias("pct"),
    )
    .collect()
)

grand_total = line_totals["total_gal"].sum()
print(f"=== 2025 Total Volume: {grand_total:,.0f} gallons ===\n")
with pl.Config(tbl_width_chars=120, thousands_separator=","):
    print(line_totals)


# In[12]:


# Monthly gallons by line
monthly_gal = (
    so_gal.lazy()
    .group_by("line", "month")
    .agg(pl.col("gallons").sum().round(0).alias("gal"))
    .collect()
    .pivot(on="line", index="month", values="gal")
    .fill_null(0)
    .sort("month")
)

n_months = monthly_gal.height

print("=== Monthly Gallons by Line ===")
with pl.Config(tbl_width_chars=200, tbl_rows=n_months, thousands_separator=","):
    print(monthly_gal)

# Monthly averages
print(f"\n=== Monthly AVERAGE ({n_months} months) ===")
avg_row = {col: f"{monthly_gal[col].mean():,.0f}" for col in monthly_gal.columns if col != "month"}
for line, avg in sorted(avg_row.items(), key=lambda x: -float(x[1].replace(",",""))):
    print(f"  {line:12s}  {avg:>10s} gal/month")


# In[14]:


# Weekly gallons by line
weekly_gal = (
    so_gal.lazy()
    .group_by("line", "week")
    .agg(pl.col("gallons").sum().round(0).alias("gal"))
    .collect()
    .pivot(on="line", index="week", values="gal")
    .fill_null(0)
    .sort("week")
)

print("=== Weekly Gallons by Line (first 12 weeks shown) ===")
with pl.Config(tbl_width_chars=200, tbl_rows=12, thousands_separator=","):
    print(weekly_gal.head(12))

# Weekly averages
n_weeks = weekly_gal.height
print(f"\n=== Weekly AVERAGE ({n_weeks} weeks) ===")
avg_row = {col: f"{weekly_gal[col].mean():,.0f}" for col in weekly_gal.columns if col != "week"}
for line, avg in sorted(avg_row.items(), key=lambda x: -float(x[1].replace(",",""))):
    print(f"  {line:12s}  {avg:>10s} gal/week")

# Grand summary
print(f"\n=== Overall Averages ===")
print(f"  {'':12s}  {'gal/week':>10s}  {'gal/month':>10s}  {'gal/year':>12s}")
for line in sorted(avg_row.keys(), key=lambda x: -float(avg_row[x].replace(",",""))):
    wk = weekly_gal[line].mean()
    mo = monthly_gal[line].mean()
    yr = line_totals.filter(pl.col("line") == line)["total_gal"][0]
    print(f"  {line:12s}  {wk:>10,.0f}  {mo:>10,.0f}  {yr:>12,.0f}")


# ## 7. Export Results
# 
# Write the enriched data back to Excel when you're happy with the assignments.

# In[15]:


OUT = r"C:\OD\OneDrive - Kinpak, Inc\Desktop\line_capacity_results.xlsx"

so.write_excel(OUT, worksheet="SO_with_lines")

print(f"Exported to {OUT}")

