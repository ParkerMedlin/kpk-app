import datetime as dt
from typing import Dict, Optional

from core.models import ProductionHistory


def _serialize_production_history(record: ProductionHistory) -> Dict:
    return {
        'id': record.id,
        'item_code': record.item_code,
        'po_number': record.po_number,
        'product_description': record.product_description,
        'blend': record.blend,
        'case_size': record.case_size,
        'scheduled_qty': record.scheduled_qty,
        'produced_qty': record.produced_qty,
        'bottle': record.bottle,
        'cap': record.cap,
        'runtime_estimate': float(record.runtime_estimate) if record.runtime_estimate is not None else None,
        'carton': record.carton,
        'pallet': record.pallet,
        'po_due_date': record.po_due_date,
        'line_name': record.line_name,
        'run_date': record.run_date.isoformat() if record.run_date else None,
        'runtime_minutes': record.runtime_minutes,
        'num_employees': record.num_employees,
        'notes': record.notes,
        'created_at': record.created_at.isoformat() if record.created_at else None,
    }


def create_production_history(
    *,
    item_code: str,
    produced_qty: int,
    line_name: str,
    run_date: dt.date,
    po_number: str = '',
    product_description: str = '',
    blend: str = '',
    case_size: str = '',
    scheduled_qty: Optional[int] = None,
    bottle: str = '',
    cap: str = '',
    runtime_estimate: Optional[float] = None,
    carton: str = '',
    pallet: str = '',
    po_due_date: str = '',
    runtime_minutes: Optional[int] = None,
    num_employees: Optional[int] = None,
    notes: str = '',
) -> Dict:
    record = ProductionHistory.objects.create(
        item_code=item_code,
        po_number=po_number,
        product_description=product_description,
        blend=blend,
        case_size=case_size,
        scheduled_qty=scheduled_qty,
        produced_qty=produced_qty,
        bottle=bottle,
        cap=cap,
        runtime_estimate=runtime_estimate,
        carton=carton,
        pallet=pallet,
        po_due_date=po_due_date,
        line_name=line_name,
        run_date=run_date,
        runtime_minutes=runtime_minutes,
        num_employees=num_employees,
        notes=notes,
    )
    return _serialize_production_history(record)
