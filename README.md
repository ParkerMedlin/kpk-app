# Blendverse App - KPK Manufacturing Management System

A Django-based manufacturing management system for Kinpak, Inc., a chemical blending facility. This application replaces legacy spreadsheet systems with integrated MRP (Material Requirements Planning), real-time inventory tracking, production scheduling, and quality control capabilities.

---

## Quick Reference

| Component | Technology | Version |
|-----------|------------|---------|
| Backend | Django | 3.2.x LTS |
| Database | PostgreSQL | 18-alpine |
| Cache/Broker | Redis | alpine |
| ASGI Server | Daphne | 3.0.2 |
| WebSockets | Django Channels | 4.0.0 |
| Frontend | Bootstrap 5 + jQuery | 5 / 3.6.0 |
| Container | Docker Compose | Multi-stage |
| ERP Integration | Sage 100 (ODBC) | MAS 90 4.0 |

---

## Architecture Overview

```
                                   [Sage 100 ERP]
                                        |
                                   [ODBC Driver]
                                        |
    [SharePoint Excel] ─────┬──────────────────────┬───── [IOT Tank Sensors]
                            |                      |
                            v                      v
                    ┌──────────────────────────────────┐
                    │     DATA LOOPER (background)     │
                    │  local_machine_scripts/          │
                    │  python_db_scripts/data_looper.py│
                    └──────────────┬───────────────────┘
                                   |
                                   v
┌─────────────────────────────────────────────────────────────────────────────┐
│                         PostgreSQL (blendversedb)                            │
├─────────────────────────────────────────────────────────────────────────────┤
│  Source Tables (Sage sync):     │  Calculated Tables:                       │
│  - ci_item                      │  - bill_of_materials                      │
│  - im_itemwarehouse             │  - component_usage / component_shortage   │
│  - im_itemcost                  │  - blend_subcomponent_usage/shortage      │
│  - im_itemtransactionhistory    │  - timetable_run_data                     │
│  - bm_billheader/detail         │  - weekly_blend_totals                    │
│  - po_purchaseorderheader/detail│  - adjustment_statistic                   │
│  - so_salesorderdetail          │  - upcoming_blend_count/component_count   │
│  - prodmerge_run_data           │                                           │
│  - hx_blendthese                │  User-Managed Tables:                     │
│  - core_tanklevel               │  - core_lotnumrecord                      │
│                                 │  - core_deskoneschedule/desktwoschedule   │
│                                 │  - core_blendcountrecord                  │
│                                 │  - core_checklistlog                      │
└─────────────────────────────────────────────────────────────────────────────┘
                                   |
                                   v
┌─────────────────────────────────────────────────────────────────────────────┐
│                           Django Application                                 │
├─────────────────────────────────────────────────────────────────────────────┤
│  Apps:                                                                       │
│  ├── core/          - Main business logic (blending, inventory, scheduling) │
│  ├── prodverse/     - Production specs, warehouse counts, carton tracking   │
│  ├── kpklauncher/   - Desktop launcher interface                            │
│  └── nav3d/         - 3D navigation interface (placeholder)                 │
│                                                                              │
│  Layer Pattern:                                                              │
│  Views (web.py, api.py) → Services (business logic) → Selectors (queries)  │
└─────────────────────────────────────────────────────────────────────────────┘
                                   |
              ┌────────────────────┼────────────────────┐
              v                    v                    v
        [HTTP/HTTPS]         [WebSocket]          [Redis PubSub]
              |                    |                    |
              v                    v                    v
┌─────────────────────────────────────────────────────────────────────────────┐
│                              Nginx Reverse Proxy                             │
│  - SSL termination (internal CA)                                            │
│  - Blue-green deployment (app_blue:8001 / app_green:8002)                   │
│  - WebSocket proxying with 24h timeout                                      │
│  - HLS streaming proxy to external cameras                                  │
└─────────────────────────────────────────────────────────────────────────────┘
                                   |
                                   v
                            [Client Browsers]
                      (Desktop, Tablets, Mobile)
```

---

## Directory Structure

```
kpk-app/
├── app/                              # Django project root
│   ├── app/                          # Django settings & ASGI config
│   │   ├── settings.py               # Main configuration
│   │   ├── urls.py                   # Root URL routing
│   │   ├── asgi.py                   # ASGI application entry
│   │   └── customMiddleware.py       # Request middleware
│   │
│   ├── core/                         # Main application (blending operations)
│   │   ├── models.py                 # 50+ models for inventory, production, etc.
│   │   ├── views/
│   │   │   ├── web.py                # Template-rendering views
│   │   │   └── api.py                # JSON API endpoints
│   │   ├── selectors/                # Data retrieval layer (9 modules)
│   │   ├── services/                 # Business logic layer (19 modules)
│   │   ├── websockets/               # WebSocket consumers
│   │   │   ├── blend_schedule/       # Real-time schedule updates
│   │   │   └── count_list/           # Real-time inventory counts
│   │   ├── static/core/              # Frontend assets
│   │   │   ├── js/
│   │   │   │   ├── objects/          # Reusable JS classes
│   │   │   │   ├── pageModules/      # Page-specific initialization
│   │   │   │   ├── requestFunctions/ # API client functions
│   │   │   │   └── websockets/       # WebSocket client classes
│   │   │   └── css/
│   │   ├── templates/core/           # Django templates
│   │   └── kpkapp_utils/             # Utility functions
│   │
│   ├── prodverse/                    # Production & specification management
│   │   ├── models.py                 # Warehouse counts, spec sheets
│   │   ├── views.py                  # Spec sheet detail, production schedule
│   │   └── websockets/               # Carton print, pull status, spec sheet
│   │
│   ├── websockets/                   # Shared WebSocket infrastructure
│   │   ├── base_consumer.py          # Redis-backed mixin & helpers
│   │   └── routing.py                # WebSocket URL aggregation
│   │
│   ├── kpklauncher/                  # Desktop launcher app
│   └── nav3d/                        # 3D navigation (placeholder)
│
├── host-services/                    # Windows host-level background services
│   ├── workers/                      # Long-running data processing
│   │   ├── data_sync.py              # Core ETL (Sage, SharePoint → PostgreSQL)
│   │   ├── excel_worker.py           # Excel macro service (port 9998)
│   │   └── stream_relay.py           # Hikvision camera stream
│   ├── watchdogs/                    # Health monitoring services
│   │   └── looper_health.py          # Data looper health/restart (port 9999)
│   └── logs/                         # Centralized service logs
│
├── local_machine_scripts/            # ETL modules and legacy services
│   ├── python_db_scripts/
│   │   ├── data_looper.py            # Main ETL orchestrator (4 parallel processes)
│   │   ├── app_db_mgmt/
│   │   │   ├── sage_to_postgres.py   # Sage ERP → PostgreSQL sync
│   │   │   ├── prod_sched_to_postgres.py  # Production schedule import
│   │   │   ├── horix_sched_to_postgres.py # Horix line schedule import
│   │   │   ├── table_builder.py      # Calculated table generation
│   │   │   ├── table_updates.py      # Cross-table updates
│   │   │   └── tank_level_reading.py # IOT tank sensor polling
│   │   └── app_monitor/              # Terminal-based status display
│   └── python_systray_scripts/       # Legacy pystray services (deprecated)
│
├── nginx/                            # Reverse proxy configuration
│   ├── nginx.conf                    # Main config with upstream routing
│   ├── ssl/                          # TLS certificates (internal CA)
│   └── Dockerfile                    # Nginx container build
│
├── scripts/tls/                      # Certificate generation scripts
├── control-panel/                    # Go-based service management GUI
│   ├── commands.go                   # Docker/host service commands
│   ├── ui.go                         # Fyne GUI implementation
│   └── bin/                          # Compiled executables
├── ws4kp/                            # WeatherStar 4000+ weather display
│   ├── Dockerfile                    # Static nginx deployment
│   ├── server/music/default/         # Background music (26 tracks)
│   └── src/                          # Frontend source
├── docker-compose-DEV.yml            # Development environment
├── docker-compose-PROD.yml           # Production (blue-green)
├── Dockerfile                        # Application container
└── requirements.txt                  # Python dependencies
```

---

## Nav3D Rendering Notes

These guardrails keep glow effects stable and readable in `app/nav3d/static/nav3d/js/nav3d-interface.js`.

- Use planes for wall-aligned glow elements instead of sprites to avoid camera-facing tilt.
- For glow textures, prefer stable sampling: `LinearFilter` for min/mag, `generateMipmaps = false`, and `ClampToEdge` wrapping.
- Avoid z-fighting shimmer on glow planes with `polygonOffset` (or a small positional offset when needed).
- Keep glow materials additive, transparent, and non-shadowing so they read as light, not geometry.

## Django Apps

### Core (`app/core/`)
The primary application handling blend operations, inventory, and production planning.

**Key URL Patterns:**
| Pattern | Purpose |
|---------|---------|
| `/core/lot-num-records/` | Lot number management with pagination |
| `/core/blend-schedule/` | Real-time blend scheduling (WebSocket-enabled) |
| `/core/blend-shortages/` | Component shortage analysis |
| `/core/chemical-shortages/` | Chemical inventory forecasting |
| `/core/count-list/display/` | Physical inventory counts (WebSocket-enabled) |
| `/core/tank-levels/` | Real-time tank monitoring |
| `/core/issue-sheets/{line}/{date}` | Production batch issue sheets |
| `/core/bom-cost-tool/` | FIFO costing calculator |

### Prodverse (`app/prodverse/`)
Production specification management and warehouse operations.

**Key URL Patterns:**
| Pattern | Purpose |
|---------|---------|
| `/prodverse/spec-sheet/{item}/{po}/{julian}/` | Product specification sheets |
| `/prodverse/production-schedule/` | Production schedule view |
| `/prodverse/pick-ticket/{item}/` | Pick ticket with BOM details |

---

## Data Models

### Core Domain Entities

#### LotNumRecord (`core_lotnumrecord`)
Central tracking for blend batches. Links production to Sage inventory receipts.
```
Fields: item_code, lot_number (unique), lot_quantity, desk, line,
        start_time, stop_time, sage_entered_date, sage_qty_on_hand, run_date
Relations: BlendSheet (1:1), BlendSheetPrintLog (1:many)
```

#### BlendCountRecord / BlendComponentCountRecord
Physical inventory count records with variance tracking.
```
Fields: item_code, expected_quantity, counted_quantity, variance,
        counted_date, count_type, collection_id, containers (JSON)
```

#### ComponentShortage / SubComponentShortage (calculated, unmanaged)
Shortage forecasting based on production schedule vs. inventory.
```
Fields: component_item_code, component_onhand_after_run, total_shortage,
        one_wk_short, two_wk_short, three_wk_short, next_order_due
```

#### DeskOneSchedule / DeskTwoSchedule / LetDeskSchedule
Production station scheduling with blend assignments and tank allocations.
```
Fields: order, item_code, lot, blend_area, tank
```

### Sage-Synced Tables (Unmanaged)
These tables mirror Sage 100 ERP data and are read-only from Django:
- `ci_item` - Item master (100+ fields)
- `im_itemwarehouse` - Warehouse inventory levels
- `im_itemcost` - FIFO cost layers by lot
- `im_itemtransactionhistory` - 52-week transaction audit trail
- `bm_billheader` / `bm_billdetail` - Bill of materials
- `po_purchaseorderheader` / `po_purchaseorderdetail` - Purchase orders
- `so_salesorderdetail` - Sales orders

### Calculated Tables (Unmanaged)
Generated by `table_builder.py` during ETL:
- `bill_of_materials` - Joined BOM with warehouse quantities
- `component_usage` - Cumulative component demand per run
- `component_shortage` - Components with negative post-run inventory
- `blend_subcomponent_usage` / `blend_subcomponent_shortage` - Multi-level BOM analysis
- `timetable_run_data` - Timeline view of all production
- `weekly_blend_totals` - Weekly production aggregates

---

## Service Layer Architecture

### Selectors (`core/selectors/`)
Data retrieval functions returning querysets or dictionaries:

| Module | Purpose |
|--------|---------|
| `inventory_selectors.py` | Count dates, item quantities, audit groups, BOM variance checks |
| `production_planning_selectors.py` | Blend shortages, component demand forecasting |
| `lot_numbers_selectors.py` | Orphaned lots, schedule assignments, lot quantities |
| `blend_count_selectors.py` | Upcoming blend usage, shortage mapping |
| `component_count_selectors.py` | Component items, adjustments, count history |
| `batch_issue_selectors.py` | Batch issue runs, positive lot numbers |
| `reports_selectors.py` | Excess blend inventory analysis |

### Services (`core/services/`)
Business logic and side effects:

| Module | Purpose |
|--------|---------|
| `lot_numbers_services.py` | Lot creation (sequential numbering), updates, deletion |
| `blend_scheduling_services.py` | Schedule management with WebSocket broadcasts |
| `inventory_services.py` | Count lists, audit groups, variance analysis |
| `bom_costing_service.py` | FIFO costing engine with caching |
| `label_printing_services.py` | Zebra printer integration (ZPL commands) |
| `tank_levels_services.py` | Tank usage logging, remote sensor polling |
| `production_planning_services.py` | Shortage forecasting, schedule snapshots |
| `reports_services.py` | 15+ report generators (lot history, transactions, what-if) |

---

## WebSocket Architecture

### Channel Groups
```
blend_schedule_unique_{context}    # Desk_1, Desk_2, LET_Desk, Hx, Dm, Totes, all
count_list_unique_{list_id}        # Per count collection
spec_sheet_unique_{spec_id}        # Per specification sheet
carton_print_unique_{prod_line}    # Per production line
pull_status_unique_{prod_line}     # Per production line
count_collection_unique_{context}  # Collection lifecycle
```

### Redis Key Patterns
```
blend_schedule:{area}              # Event history (50 events max)
count_list:{id}                    # Event history (25 events default)
spec_sheet_events:{id}             # State snapshots (5 events)
carton_print:{line}                # Redis Set of printed items
pull_status:{line}                 # Redis Set of pulled items
```

### Message Flow
```
User Action → Django View/Service → broadcast_*_update()
    → channel_layer.group_send() → All connected consumers
    → persist_event() to Redis → Client reconnect replay
```

---

## Frontend Architecture

### JavaScript Organization
```
js/
├── objects/                      # Reusable classes
│   ├── pageObjects.js            # CountListPage, DeskSchedulePage, etc.
│   ├── modalObjects.js           # DeleteLotNumModal, AddLotNumModal
│   ├── buttonObjects.js          # CreateCountListButton, LabelPrintSender
│   └── webSocketObjects.js       # Legacy CountCollectionWebSocket
│
├── pageModules/                  # Page initialization (47 modules)
│   ├── countList.js              # WebSocket + CountListPage
│   ├── blendSchedule.js          # WebSocket + DeskSchedulePage
│   └── ...
│
├── requestFunctions/             # API clients
│   └── requestFunctions.js       # getItemInfo, getBlendSheet, etc.
│
└── websockets/                   # WebSocket clients
    ├── countListSocket.js        # Extends BaseSocket
    └── blendScheduleSocket.js    # Context-aware routing
```

### Key Third-Party Libraries
- **BrowserPrint-3.1.250.js** - Zebra printer integration
- **html2canvas-1.14.js** - Client-side label rendering
- **pdfmake.min.js** - PDF generation for reports
- **DataTables** - Advanced table filtering/sorting

---

## Data Pipeline (ETL)

### Data Looper (`data_looper.py`)
Four parallel processes running continuously:

**Process 1: `clone_sage_tables()`**
- Syncs Sage 100 tables via ODBC (BM_Bill*, CI_Item, IM_Item*, PO_*, SO_*)
- 52-week rolling window for transaction history
- Exports to CSV then bulk loads to PostgreSQL

**Process 2: `update_xlsb_tables()`**
Sequential execution of 15 functions:
1. Tank level updates
2. Production schedule import (SharePoint Excel)
3. Horix line blend schedule import
4. BOM table generation
5. Component usage/shortage calculations
6. Sub-component analysis
7. Timetable and weekly totals
8. Spec sheet auditing
9. Lot number Sage linking
10. Desk assignment updates

**Process 3: `log_tank_levels_table()`**
- 5-minute interval tank level history logging

**Process 4: `check_latest_table_updates()`**
- Heartbeat monitor (6-minute interval)
- Sends timeout alerts if any function stale >5 minutes

### Function Toggle System
Database-driven enable/disable for any ETL function:
```sql
SELECT status FROM core_functiontoggle WHERE function_name = 'get_prod_schedule';
-- Returns 'on' or 'off'
```
UI: `/core/function-toggles/`

---

## Deployment

### Development
```bash
docker compose -f docker-compose-DEV.yml up -d
# Access at http://localhost:1337
```
- Hot-reload enabled via `watch_and_reload.sh`
- Direct volume mount: `./app:/app`

### Production
```bash
# Generate TLS certificates
bash scripts/tls/generate-internal-certs.sh

# Build and deploy
docker compose -f docker-compose-PROD.yml build
docker compose -f docker-compose-PROD.yml up -d
```

### Blue-Green Switching
```nginx
# In nginx/nginx.conf
upstream app {
    server app_blue:8001;   # Current active
    # server app_green:8002; # Standby
}
```
Switch by editing upstream and `nginx -s reload`.

### Container Services
| Service | Port | Purpose |
|---------|------|---------|
| nginx | 80/443 | Reverse proxy, SSL termination |
| app_blue | 8001 | Active Daphne instance |
| app_green | 8002 | Standby Daphne instance |
| db | 5432 | PostgreSQL |
| redis | 6379 | Cache, WebSocket broker |
| ws4kp | 8080 | WeatherStar 4000+ weather display |

---

## Required Background Services (Windows Host)

These Python systray services **must be running** on the Windows host machine for full functionality. Located in `host-services/`.

> **Note:** Legacy versions remain in `local_machine_scripts/python_systray_scripts/` for backward compatibility but are deprecated.

### Critical Services

| Service | Location | Port | Purpose |
|---------|----------|------|---------|
| Data Sync Worker | `host-services/workers/data_sync.py` | N/A | Core ETL engine (Sage, SharePoint → PostgreSQL) |
| Excel Worker | `host-services/workers/excel_worker.py` | 9998 | Excel macro automation (blend sheets, GHS labels) |
| Stream Relay | `host-services/workers/stream_relay.py` | N/A | Hikvision camera WebSocket relay |
| Looper Health | `host-services/watchdogs/looper_health.py` | 9999 | Health monitoring and auto-restart |

#### 1. Data Sync Worker (`host-services/workers/data_sync.py`)
**Purpose:** Core ETL engine - synchronizes Sage ERP, SharePoint schedules, and calculated tables.

**Must Run:** Yes - without this, all data goes stale.

```
Processes:
- clone_sage_tables() - Sage ODBC imports
- update_xlsb_tables() - 17 sequential ETL functions
```

#### 2. Looper Health Watchdog (`host-services/watchdogs/looper_health.py`)
**Purpose:** Monitors data looper health, provides restart capability via HTTP/email, runs UV/Freeze audits.

**Must Run:** Yes - enables remote restart and health checks.

| Port | Endpoint | Purpose |
|------|----------|---------|
| 9999 (HTTPS) | `GET /trigger-restart` | Restart data looper |
| 9999 (HTTPS) | `GET /run-uv-freeze-audit` | Execute UV/Freeze audit |
| 9999 (HTTPS) | `GET /service-status` | Health check (JSON) |

**Features:**
- Polls `/core/get-refresh-status/` every 5 minutes
- Auto-restarts looper if status is "down"
- Monitors Gmail for "restart loop" commands from authorized senders
- Executes `C:\Users\pmedlin\Desktop\4. Update the database.bat`

**SSL:** Uses `nginx/ssl/kpkapp.lan.pem` and `nginx/ssl/kpkapp.lan.key`

#### 3. Excel Worker (`host-services/workers/excel_worker.py`)
**Purpose:** Processes Excel macro jobs (blend sheets, production packages) via Redis queue.

**Must Run:** Yes - without this, blend sheet printing fails.

| Port | Endpoint | Method | Purpose |
|------|----------|--------|---------|
| 9998 (HTTP) | `/run-excel-macro` | POST | Submit macro job |
| 9998 (HTTP) | `/job-status` | POST | Check job status |

**Job Types:**
- `generateProductionPackage` - Full package with GHS labels and pick sheets
- `blndSheetGen` - Blend sheet only

**Integration:**
- Django POSTs to `http://127.0.0.1:9998/run-excel-macro`
- Jobs queued in Redis `excel_macro_queue`
- Completion events published to Redis `excel_macro_completions`
- Executes `Invoke-DirectExcelEdit.ps1` PowerShell script
- Up to 10 concurrent Excel jobs via ThreadPoolExecutor

#### 4. Stream Relay Worker (`host-services/workers/stream_relay.py`)
**Purpose:** Manages WebSocket streaming for palletizer camera feed.

**Must Run:** Yes - required for `/prodverse/palletizer-camera/` to work.

**Features:**
- Launches `realtime_stream_server.pyw` subprocess
- Auto-restarts if stream server exits
- Provides feed to Django at port 8890 (proxied through nginx)

### Optional Services (Legacy Location)

These remain in `local_machine_scripts/python_systray_scripts/`:

| Service | Purpose |
|---------|---------|
| `PYSTRAY_automated_countlist.pyw` | Creates daily inventory count lists at 04:00 AM |
| `PYSTRAY_qty_oh_level_email_service.pyw` | Monitors item quantities, sends alerts when below threshold |
| `PYSTRAY_tank_level_email_service.pyw` | Monitors tank levels for railcar unloading capacity |
| `PYSTRAY_nginx_reload_service.py` | Blue-green deployment helper for nginx config switching |
| `pystray_service_launcher.pyw` | GUI launcher for all pystray services |

### Starting Services
```powershell
# From kpk-app root directory

# Core ETL (required)
python host-services/workers/data_sync.py

# Excel automation (required for blend sheet generation)
python host-services/workers/excel_worker.py

# Camera stream relay (required for palletizer camera view)
pythonw host-services/workers/stream_relay.py

# Health watchdog (recommended)
pythonw host-services/watchdogs/looper_health.py
```

### Log Locations
```
host-services/logs/looper_health.log
host-services/logs/excel_worker.log
host-services/logs/stream_relay.log
```

---

## Environment Variables

```env
# Database
DB_NAME=blendversedb
DB_USER=postgres
DB_PASS=<password>
DB_HOST=localhost

# Django
SECRET_KEY=<production-key>
DEBUG=0
ALLOWED_HOSTS=kpkapp.lan,192.168.178.169

# Application
KPKAPP_BASE_URL=https://kpkapp.lan
KPKAPP_HOST=kpkapp.lan

# Sage 100 ERP
SAGE_USER=<user>
SAGE_PW=<password>
SAGE_CONNECTION_STRING=<odbc-string>

# Azure AD (SharePoint access)
AZURE_TENANT_ID=<tenant>
AZURE_CLIENT_ID=<client>
AZURE_CLIENT_SECRET=<secret>

# Notifications
NOTIF_EMAIL_ADDRESS=<email>
NOTIF_PW=<app-password>
```

---

## Key Conventions

### Naming
- **Python functions:** `lowercase_with_underscores` (verb prefix)
- **Python classes:** `CamelCase`
- **URL paths:** `lowercase-with-dashes`
- **HTML templates:** `lowercasenopunctuation.html`
- **JS modules:** `camelCase.js`

### Item Code Prefixes
- `BLEND-*` - Finished blend products
- `CHEM-*` - Chemical raw materials
- `DYE-*` - Colorants
- `FRAGRANCE-*` - Fragrance additives

### Lot Number Format
`[MonthLetter][YearLastTwo][4DigitSequence]`
Example: `A2500001` = January 2025, sequence 1

### Database Patterns
- Unmanaged models (`managed=False`) for Sage-synced and calculated tables
- JSONField for flexible data: containers, blend_sheet, state_json
- Decimal precision: 50.5 for quantities, 100.2 for financial

---

## API Reference

### JSON APIs (`/core/`)

| Endpoint | Method | Purpose |
|----------|--------|---------|
| `get-json-lot-details/<id>/` | GET | Full lot record |
| `get-json-item-info/` | GET | Item lookup with lot numbers |
| `get-BOM-fields/` | GET | Item code/description lists |
| `api/bom-cost/` | GET/POST | FIFO cost calculation |
| `get-max-producible-quantity/<item>` | GET | Production capacity analysis |
| `get-tank-specs/` | GET | Tank configuration |
| `api/get-single-tank-level/<tank>/` | GET | Current tank level |
| `get-refresh-status/` | GET | ETL health check |

### WebSocket Endpoints

| Path | Consumer | Events |
|------|----------|--------|
| `ws/blend_schedule/{context}/` | BlendScheduleConsumer | blend_schedule_update, ping/pong |
| `ws/count_list/{id}/` | CountListConsumer | count_updated, count_added, count_deleted |
| `ws/spec_sheet/{id}/` | SpecSheetConsumer | spec_sheet_update |
| `ws/carton-print/{line}/` | CartonPrintConsumer | carton_print_update |
| `ws/pull-status/{line}/` | PullStatusConsumer | pull_status_update |

---

## Tables Requiring Backup

User-managed tables that are NOT programmatically regenerated:
```
auth_user
core_lotnumrecord
core_blendinstruction
core_blendingstep
core_blendsheet
core_blendsheetprintlog
core_checklistlog
core_checklistsubmissionrecord
core_deskoneschedule
core_desktwoschedule
core_letdeskschedule
core_blendcountrecord
core_blendcomponentcountrecord
core_countcollectionlink
core_itemlocation
core_storagetank
core_manualgauge
core_tankusagelog
core_foamfactor
core_forklift
core_functiontoggle
core_purchasingalias
core_blendcontainerclassification
core_blendprotection
core_formulachangealert
prodverse_warehousecountrecord
prodverse_specsheetstate
```

---

## Troubleshooting

### ETL Not Running
1. Check `core_loopstatus` for recent timestamps
2. Check `/core/display-loop-status` in UI
3. Verify data looper process is running
4. Check function toggles at `/core/function-toggles/`

### WebSocket Disconnections
1. Verify Redis is running: `docker compose ps redis`
2. Check Daphne logs for errors
3. Nginx WebSocket timeout is 86400s (24h)

### Sage Sync Issues
1. Verify ODBC driver installed and configured
2. Check `SAGE_CONNECTION_STRING` in .env
3. Ensure server is on trusted network
4. Review exception emails (sent after 11 consecutive failures)

### Certificate Errors
1. Regenerate: `bash scripts/tls/generate-internal-certs.sh`
2. Rebuild nginx: `docker compose -f docker-compose-PROD.yml build nginx`
3. Distribute root CA to clients
4. Verify: `curl -Ik https://kpkapp.lan/`

---

## Development Workflow

### Adding a New Model
1. Define in `app/core/models.py`
2. Run `python manage.py makemigrations core`
3. Run `python manage.py migrate`
4. If Sage-synced: Add to `sage_to_postgres.py`
5. If calculated: Add to `table_builder.py`

### Adding a New API Endpoint
1. Add view function to `app/core/views/api.py`
2. Add URL pattern to `app/core/urls.py`
3. Add client function to `requestFunctions.js`

### Adding WebSocket Functionality
1. Create consumer in `app/core/websockets/{feature}/consumer.py`
2. Add routes in `app/core/websockets/{feature}/routes.py`
3. Register in `app/websockets/routing.py`
4. Create client class in `js/websockets/`
5. Import in page module

---

## Performance Notes

- **Sage Sync:** ODBC connection ~8s startup; uses dirty reads for speed
- **Tank Levels:** 0.9s cache TTL to reduce polling
- **BOM Costing:** Warm caches before batch processing
- **WebSocket Events:** 25-50 event history limit per channel
- **Transaction History:** 52-week rolling window (~2M rows)

---

## Security Considerations

- TLS certificates use internal CA (distribute root cert to clients)
- CSRF protection on all form submissions
- WebSocket origin validation via `AllowedHostsOriginValidator`
- Database credentials in .env (should use secrets manager)
- Sage ODBC requires trusted network membership

---

## KPK Control Panel

A Go-based GUI application for managing all KPK services from a single interface. Located in `control-panel/`.

### Features

- **Container Management:** View status, start/stop/restart Docker containers, view logs, open shell
- **Host Service Management:** Start/stop Python background services, view logs
- **Health Monitoring:** Real-time status of all 7 containers and 4 host services
- **Crash Loop Detection:** Warns when containers restart repeatedly (4+ times in 5 minutes)
- **Quick Actions:**
  - Create/restore database backups
  - Start missing services or restart all
  - Stop all services
  - Reload Nginx config (copies local `nginx/nginx.conf` to container and restarts)

### Building

```powershell
cd control-panel
go build -o bin/kpk-control-panel.exe .
```

### Usage

Run the executable and either:
- **Connect via SSH:** Enter server credentials for remote management
- **Run Locally:** Manage services on the current machine

The panel auto-refreshes status every 5 seconds.

### Reload Nginx Config

The "Reload Nginx Config" button:
1. Copies `kpk-app/nginx/nginx.conf` to the nginx container at `/etc/nginx/conf.d/nginx.conf`
2. Restarts the nginx container to apply changes

This allows quick nginx configuration updates without rebuilding the container.

---

## WeatherStar 4000+ (KPK Weather)

A nostalgic weather display in the style of The Weather Channel's 90s local forecast. Accessible via **Tools → KPK Weather** in the navigation menu.

### Features

- Real-time weather data from NOAA's Weather API (US locations only)
- Retro blue and orange graphics with scan line effects
- Background smooth jazz music (26 tracks included)
- Configurable displays: hazards, current conditions, hourly forecast, radar, almanac, etc.
- Kiosk mode for plant floor displays

### Source

Located in `ws4kp/`, built from [netbymatt/ws4kp](https://github.com/netbymatt/ws4kp).

### Default Configuration

The nav link opens with these defaults:
- Location: Montgomery, AL
- All weather displays enabled
- Kiosk mode enabled
- Scan lines enabled

### Nginx Proxy Routes

The following paths are proxied to the ws4kp container:
- `/weather/` - Main application
- `/data/` - Weather data JSON files
- `/images/` - Radar maps and graphics
- `/music/` - Background music MP3 files

### Customization

To change the default location or displays, edit the URL in:
`app/templates/navbars/tools-group-navbar-items.html`

Available query parameters (from ws4kp README):
- `latLonQuery` - Location search string
- `*-checkbox=true/false` - Enable/disable specific displays
- `kiosk=true` - Fullscreen kiosk mode
- `settings-scanLines-checkbox=true` - Retro scan line effect
- `settings-mediaPlaying-boolean=true` - Auto-play music (browser restrictions may apply)
