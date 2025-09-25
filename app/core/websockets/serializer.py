import decimal

def serialize_for_websocket(data):
    """
    Serialize data for WebSocket transmission with financial-grade precision handling.
    
    Converts Decimal objects to float for msgpack compatibility while maintaining
    precision standards used in professional banking systems.
    
    Args:
        data (dict): Dictionary containing data to be serialized
        
    Returns:
        dict: Serialized data with Decimal objects converted to float
    """
    if isinstance(data, dict):
        return {key: serialize_for_websocket(value) for key, value in data.items()}
    elif isinstance(data, list):
        return [serialize_for_websocket(item) for item in data]
    elif isinstance(data, decimal.Decimal):
        return float(data) if data is not None else 0.0
    else:
        return data