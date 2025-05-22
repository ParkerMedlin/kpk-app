for blend in queryset:
    blend.lot_number = 'Not found.'
    blend.lot_num_record_obj = None # Initialize lot_num_record_obj
    blend.lot_id = None             # Initialize lot_id
    # blend.lot_quantity will be set if a match is found

    for item_index, item_data in enumerate(matching_lot_numbers):
        # item_data is [item_code, lot_number_str, run_date_obj, lot_quantity_val]
        if blend.component_item_code == item_data[0] and blend.run_date == item_data[2]:
            blend.lot_number = item_data[1]
            blend.lot_quantity = item_data[3]
            
            # Attempt to fetch and assign the LotNumRecord object and its pk
            try:
                lot_record = LotNumRecord.objects.get(lot_number=item_data[1])
                blend.lot_num_record_obj = lot_record
                blend.lot_id = lot_record.pk
            except LotNumRecord.DoesNotExist:
                # If not found, these remain as initialized (None)
                pass
            except LotNumRecord.MultipleObjectsReturned:
                # Mirror Desk area behavior (pass), obj and id remain as initialized (None)
                pass
            except Exception:
                # Mirror Desk area behavior (pass), obj and id remain as initialized (None)
                pass
            
            matching_lot_numbers.pop(item_index)
            break 

    return queryset 