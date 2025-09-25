from core.models import LotNumRecord, HxBlendthese
from core.kpkapp_utils.dates import _is_date_string

def get_orphaned_lots():
    """
    Filters LotNumRecord objects based on the specified conditions.
    
    Args:
        None

    Returns:
        QuerySet of filtered LotNumRecord objects
    """

    # Filter LotNumRecord based on the specified conditions
    unentered_lots = LotNumRecord.objects.filter(
        sage_entered_date__isnull=True,
        line__in=['Dm', 'Totes', 'Hx']
    )

    hx_blendthese = HxBlendthese.objects.filter(
        prod_line__in=['Dm', 'Totes', 'Hx']
    )


    hx_blendthese_list = []
    for item in hx_blendthese:
        current_item = {'item_code' : item.component_item_code, 'prod_line' : item.prod_line}
        if _is_date_string(item.run_date):
            current_item['run_date'] = item.run_date.strftime('%Y-%m-%d')
        else:
            current_item['run_date'] = None
        hx_blendthese_list.append(current_item)

    unentered_lots_list = []
    for item in unentered_lots:
        current_item = {
            'lot_id' : item.pk,
            'item_code' : item.item_code, 
            'prod_line' : item.line,
            'item_description' : item.item_description,
            'lot_number' : item.lot_number
        }
        if _is_date_string(item.run_date):
            current_item['run_date'] = item.run_date.strftime('%Y-%m-%d')
        else:
            current_item['run_date'] = None
        unentered_lots_list.append(current_item)
    
    for lot_to_test in unentered_lots_list:
        for item in hx_blendthese_list:
            if lot_to_test['item_code'] == item['item_code']:
                print('itemcode match!')
                if lot_to_test['run_date'] == item['run_date']:
                    print('run date match!')
                    if lot_to_test['prod_line'] == item['prod_line']:
                        print('prod line match!')
                        print(f"found a match! {lot_to_test['item_code']} {lot_to_test['run_date']} {lot_to_test['prod_line']}")
                        unentered_lots_list.remove(lot_to_test)
                        hx_blendthese_list.remove(item)
                        break
            else:
                print(f"no match found! {lot_to_test['item_code']} {lot_to_test['run_date']} {lot_to_test['prod_line']}")

    return unentered_lots_list