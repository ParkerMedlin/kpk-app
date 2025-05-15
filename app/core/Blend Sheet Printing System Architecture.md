# Blend Sheet Printing System Architecture

## System Overview
The application implements a remote blend sheet printing system where a user interface action triggers a server-side process to locate, populate, print, and close a blend sheet document without persisting changes.

## Data Flow
1. User initiates print request via application interface
2. Request transmits critical parameters to server:
   - Item Code (product identifier)
   - Lot Number (batch tracking)
   - Lot Quantity (production volume)
3. Server-side automation executes the following workflow:
   - Locates the appropriate blend sheet template using the item code
   - Opens the document in the appropriate application
   - Populates the template with lot number and quantity data
   - Allows formula recalculation to update dependent values
   - Sends the document to the default printer
   - Terminates the document session without saving modifications

## Reference Implementations
- PYSTRAY_data_looper_restart_service.pyw (HTTP request handling)
- BlndSheetGen.vbs (Document automation)

## Required Components
1. Backend API endpoint (Django view function)
2. Frontend interface template (HTML/CSS)
3. URL routing configuration
4. Client-side request handler (JavaScript function)
5. JavaScript module for response processing
6. Server-side Python Windows service (.pyw)
7. Document automation script (VBScript or batch file)