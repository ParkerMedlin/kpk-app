from django.db import connection
import logging

logger = logging.getLogger(__name__)

def get_excess_blends():
    sql = """
        SELECT
            ci.itemcode,
            ci.itemcodedesc,
            COALESCE(ct.total_demand, 0) AS total_demand,
            w.quantityonhand AS quantity_on_hand,
            COALESCE(ct.total_demand, 0) - w.quantityonhand AS excess_inventory,
            ci.averageunitcost,
            abs(ci.averageunitcost * (COALESCE(ct.total_demand, 0) - w.quantityonhand)) as excess_inventory_value
            FROM ci_item ci
            -- First, cull by description and limit to MTG warehouse stock > 0
            JOIN im_itemwarehouse w
                ON w.itemcode       = ci.itemcode
            AND w.warehousecode  = 'MTG'
            AND w.quantityonhand >  0
            -- Then aggregate demand only for surviving items
            LEFT JOIN (
                SELECT
                component_item_code AS itemcode,
                MAX(cumulative_component_run_qty) AS total_demand
                FROM component_usage
                GROUP BY component_item_code
            ) ct
                ON ct.itemcode = ci.itemcode
            WHERE
            ci.itemcodedesc LIKE 'BLEND%'
            and ci.procurementtype = 'M'
            and ci.itemcode not in ('100501K','841BLK.B','841WHT.B')
            AND COALESCE(ct.total_demand, 0) < w.quantityonhand;
        """

    excess_blends = []
    with connection.cursor() as cursor:
        cursor.execute(sql)
        result = cursor.fetchall()
        for item in result:
            excess_blends.append({
                'item_code': item[0],
                'item_description': item[1],
                'total_demand': item[2],
                'quantity_on_hand': item[3],
                'excess_inventory': item[4],
                'average_unit_cost': item[5],
                'excess_inventory_value': item[6]
            })
    
    excess_blends.sort(key=lambda x: x['excess_inventory_value'], reverse=True)
    total_excess_inventory_value = sum(item['excess_inventory_value'] for item in excess_blends)

    return {'query_results' : excess_blends, 'total_excess_inventory_value' : total_excess_inventory_value}


def get_blend_costing_report_data(item_code_filter=None):
    """
    Return blend costing rows comparing actual labor hours to standard blend cost and labor cost.

    Args:
        item_code_filter (str | None): optional blend item code to filter results (currently unused).

    Returns:
        dict: {
            'rows': list of row dicts
        }
    """
    params = ['/BLD%']
    data_sql = """
        SELECT
            lr.lot_number,
            lr.lot_quantity,
            lr.item_code,
            ci.standardunitcost AS standard_unit_cost,
            (ci.standardunitcost * lr.lot_quantity) AS extended_lot_cost,
            EXTRACT(EPOCH FROM (lr.stop_time - lr.start_time)) / 3600.0 AS hours,
            dlr.hourly_rate AS desk_hourly_rate,
            (dlr.hourly_rate * (EXTRACT(EPOCH FROM (lr.stop_time - lr.start_time)) / 3600.0)) AS labor_cost
        FROM core_lotnumrecord lr
        LEFT JOIN bill_of_materials bom
            ON lr.item_code = bom.item_code
        LEFT JOIN ci_item ci
            ON bom.component_item_code = ci.itemcode
        LEFT JOIN core_desklaborrate dlr
            ON lr.desk = dlr.desk_name
        WHERE bom.component_item_code LIKE %s
          AND lr.start_time IS NOT NULL
          AND lr.stop_time IS NOT NULL
    """

    data_sql += " ORDER BY lr.lot_number DESC"

    rows = []

    with connection.cursor() as cursor:
        cursor.execute(data_sql, params)
        for (
            lot_number,
            lot_quantity,
            item_code,
            standard_unit_cost,
            extended_lot_cost,
            hours,
            desk_hourly_rate,
            labor_cost,
        ) in cursor.fetchall():
            rows.append({
                'lot_number': lot_number,
                'lot_quantity': lot_quantity,
                'item_code': item_code,
                'standard_unit_cost': standard_unit_cost,
                'extended_lot_cost': extended_lot_cost,
                'hours': hours,
                'desk_hourly_rate': desk_hourly_rate,
                'labor_cost': labor_cost,
            })
    return {'rows': rows}
