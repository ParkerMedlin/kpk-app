from core.kpkapp_utils.zebrafy_image import ZebrafyImage
from core.kpkapp_utils.string_utils import get_unencoded_item_code
from core.models import PartialContainerLabelLog
import requests
import json
from django.views.decorators.csrf import csrf_exempt
import logging
from django.http import JsonResponse

logger = logging.getLogger(__name__)

class ZebraDevice:
    """A class representing a Zebra printer or scanner device.
    
    Encapsulates device information and communication with Zebra devices via HTTP.
    
    Attributes:
        name (str): Device name
        uid (str): Unique device identifier
        connection (str): Connection type (USB, Network, etc)
        deviceType (str): Type of device (printer, scanner)
        version (str): Device firmware version
        provider (str): Device provider/driver
        manufacturer (str): Device manufacturer
    """
    def __init__(self, info):
       self.name = info.get('name')
       self.uid = info.get('uid')
       self.connection = info.get('connection')
       self.deviceType = info.get('deviceType')
       self.version = info.get('version')
       self.provider = info.get('provider')
       self.manufacturer = info.get('manufacturer')

    def get_device_info(self):
        return {
            "name": self.name,
            "uid": self.uid,
            "connection": self.connection,
            "deviceType": self.deviceType,
            "version": self.version,
            "provider": self.provider,
            "manufacturer": self.manufacturer
        }
   
    def send(self, data):
           base_url = "http://host.docker.internal:9100/"
           url = base_url + "write"
           payload = {
               "device" : self.get_device_info(),
               "data": data
           }
           response = requests.post(url, json=payload)
           if response.status_code != 200:
               print(f"Error sending data: {response.text}")

def get_default_zebra_device(device_type="printer", success_callback=None, error_callback=None):
   """Get the default Zebra device of the specified type.
   
   Retrieves the default Zebra printer or scanner device from the Zebra service.
   Makes an HTTP request to get device info and creates a ZebraDevice instance.
   
   Args:
       device_type (str, optional): Type of device to get ("printer" or "scanner"). 
           Defaults to "printer".
       success_callback (callable, optional): Function to call on successful device retrieval.
           Called with the ZebraDevice instance.
       error_callback (callable, optional): Function to call if device retrieval fails.
           Called with error message string.
           
   Returns:
       ZebraDevice: The default device if found, None if not found or error occurs
   """
   base_url = "http://host.docker.internal:9100/"
   url = base_url + "default"
   if device_type is not None:
       url += "?type=" + device_type
   response = requests.get(url)
   if response.status_code == 200:
       device_info = json.loads(response.text)
       this_zebra_device = ZebraDevice(device_info)
       if success_callback is not None:
           success_callback(this_zebra_device)
       return this_zebra_device
   else:
       if error_callback is not None:
           error_callback("Error: Unable to get the default device")
       return None

def print_config_label(this_zebra_device):
   """Print a configuration label using the provided Zebra device.
   
   Sends a ~WC command to print a configuration label if a valid device is provided.
   
   Args:
       this_zebra_device (ZebraDevice): The Zebra printer device to use
   """
   print(this_zebra_device)
   if this_zebra_device is not None:
       this_zebra_device.send("~WC")

def success_callback(this_zebra_device):
   """Handle successful Zebra device retrieval.
   
   Callback function that executes when a Zebra device is successfully retrieved.
   Prints device info to console for debugging/logging purposes.
   
   Args:
       this_zebra_device (ZebraDevice): The successfully retrieved Zebra device
   """
   print("Success callback called with device info:")
   print(this_zebra_device)

def error_callback(error_message):
   """Handle error retrieving Zebra device.
   
   Callback function that executes when Zebra device retrieval fails.
   Prints error message to console for debugging/logging purposes.
   
   Args:
       error_message (str): Description of the error that occurred
   """
   print("Error callback called with message:")
   print(error_message)

def log_container_label_print(request):
    """Log when a partial container label is printed.
    
    Creates a PartialContainerLabelLog record to track when labels are printed
    for partial containers of specific items.
    
    Args:
        request: HTTP GET request containing:
            encodedItemCode (str): Base64 encoded item code
            
    Returns:
        JsonResponse containing:
            result (str): 'success' if log created, 'error: <message>' if failed
    """
    encoded_item_code = request.GET.get("encodedItemCode", "")
    item_code = get_unencoded_item_code(encoded_item_code, "itemCode")
    response_json = {'result' : 'success'}
    try: 
        new_log = PartialContainerLabelLog(item_code=item_code)
        new_log.save()
    except Exception as e:
        response_json = { 'result' : 'error: ' + str(e)}
    return JsonResponse(response_json, safe=False)


# ------------ TEST TOGGLE ------------
SEND_TEST_ZEBRA_PATTERN = False # Set to False to print actual image, True for test pattern
# ------------------------------------
@csrf_exempt
def print_blend_label(request):
    """Print a blend label using Zebra printer.
    # ... (docstring remains the same) ...
    """
    def success_callback_device_only(device):
        logger.info(f"Zebra device acquired: {device}")

    def error_callback_flexible(device_or_error_msg, error_msg_if_two_args=None):
        if error_msg_if_two_args is not None:
            logger.error(f"Zebra device error: {device_or_error_msg}, {error_msg_if_two_args}")
        else:
            logger.error(f"Zebra device/setup error: {device_or_error_msg}")

    this_zebra_device = get_default_zebra_device("printer", 
                                                 success_callback_device_only, 
                                                 error_callback_flexible)

    if not this_zebra_device:
        logger.error("Failed to get default Zebra printer device (returned None).")
        return JsonResponse({'error': 'Printer device not available'}, status=500)
        
    this_zebra_device.send("~JSB") # When in TEAR OFF MODE, we will backfeed the very first label, and only the first label. We will then print the balance of the batch with no backfeed.
    
    zpl_string_to_send = ""

    if SEND_TEST_ZEBRA_PATTERN:
        test_zpl_string = """^XA
            ^LT0
            ^PW1200
            ^FO0,0^GB1200,100,4^FS
            ^XZ"""
        zpl_string_to_send = test_zpl_string
        logger.info(">>> SENDING TEST ZPL PATTERN <<<")
    else:
        label_blob = request.FILES.get('labelBlob')
        if not label_blob:
            logger.error("labelBlob not found in the request (SEND_TEST_ZEBRA_PATTERN is False).")
            return JsonResponse({'error': 'No image blob provided'}, status=400)
            
        image_data = label_blob.read()
        try:
            generated_zpl = ZebrafyImage(image_data, invert=True).to_zpl()
            if "^XA" in generated_zpl:
                if "^LT0" not in generated_zpl:
                    generated_zpl = generated_zpl.replace("^XA", "^XA^LT0", 1)
                if "^PW1200" not in generated_zpl:
                    if "^LT0" in generated_zpl:
                         generated_zpl = generated_zpl.replace("^LT0", "^LT0^PW1200", 1)
                    else:
                         generated_zpl = generated_zpl.replace("^XA", "^XA^PW1200", 1)
            else:
                generated_zpl = f"^XA^LT0^PW1200{generated_zpl}^XZ"

            zpl_string_to_send = generated_zpl

        except Exception as e:
            logger.error(f"Error during ZPL conversion for image: {e}", exc_info=True)
            return JsonResponse({'error': f'ZPL conversion failed: {str(e)}'}, status=500)
        
    label_quantity = int(request.POST.get('labelQuantity', 1)) 
    
    try:
        for i in range(label_quantity):
            this_zebra_device.send(zpl_string_to_send)
        
        log_message_type = "TEST label(s)" if SEND_TEST_ZEBRA_PATTERN else "image label(s)"
        logger.info(f"Successfully sent {label_quantity} {log_message_type} to the printer.")

    except Exception as e:
        logger.error(f"Error sending ZPL to printer: {e}", exc_info=True)
        return JsonResponse({'error': f'Failed to send ZPL to printer: {str(e)}'}, status=500)

    return JsonResponse({'message': f'{label_quantity} {log_message_type} sent to printer successfully.'})