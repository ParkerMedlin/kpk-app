import datetime as dt
import base64
from core.models import CiItem

def get_unencoded_item_code(search_parameter, lookup_type='itemCode'):
    """Get the unencoded item code from the search parameter and lookup type.
    
    1. Direct item code lookup (lookup_type='itemCode'): 
       Decodes a base64-encoded item code string
    
    2. Item description lookup (lookup_type='itemDescription'):
       Decodes a base64-encoded item description and finds its corresponding item code
       
    Args:
        search_parameter (str): The encoded item code/description, awaiting your divine interpretation
        lookup_type (str): 'itemCode' or 'itemDescription', as your grace commands
        
    Returns:
        str: The decoded item code, presented for your noble consideration
        
    *bows deeply* I live to serve, my liege.
    """
    if lookup_type == 'itemCode':
        item_code_bytestr = base64.b64decode(search_parameter)
        item_code = item_code_bytestr.decode().replace('"', "")
    elif lookup_type == 'itemDescription':
        item_description_encoded = search_parameter
        item_description_bytestr = base64.b64decode(item_description_encoded)
        item_description = item_description_bytestr.decode().replace('"', "")
        item_code = CiItem.objects.filter(itemcodedesc__iexact=item_description).first().itemcode
    return item_code
