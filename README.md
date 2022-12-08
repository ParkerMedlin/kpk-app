# Blendverse App 

This app provides one place for reporting and record-keeping for the blending department at chemical manufacturing facility Kinpak, Inc. We are working to replace a collection of spreadsheets that interface with our ERP system to enhance our MRP, inventory tracking, and production analysis capabilities.



## Current Live Functions:

### Forklift Safety Checklist 
 - Forklift drivers are able to fill out a checklist certifying that they have completed daily safety inspection of their vehicle.
 - Safety manager receives two emailed reports every day:
    - First report contains all daily inspection forms which include comments/safety concerns.
    - Second report contains a list of all forklifts which are missing a checklist submission.

### Lot Number Records 
 - Database contains our batch history, each batch being designated by a lot number.
 - Admin users can create new lot number records using the app as well. 

### Materials & Resource Planning
 - Database contains continuously updated copies of all Sage 100 ERP tables with inventory, purchasing, and accounting information.
 - Database also contains continuously updated tables containing the sequence of production orders.
 - App calculates shortages of blends needed to fulfill production orders.
 - App also calculates shortages of raw materials needed to satisfy blend needs for production orders.
     - Chem Shortages report allows for precise prediction of the final production run we can make before running out of a given chemical.

### Blend Scheduling 
 - Rudimentary scheduling of blends and tracking their completion.

### Production Batch Issue Sheets 
 - App renders paperwork showing which batches of blend are being issued to production lines for bottling. 



## Functions Still In Development:

### Blend Sheets
Display the formula to blend crew and then track the steps taken when making a batch. 
 - Our blend formulae are currently stored in Excel spreadsheets which are printed and distributed to blend crew as needed. 
 - A module is in development that will replace this system and store all information about blends as they are made.

### Blend Inventory Counts
Display the list of all blends which need to be manually counted and allow for entry of those counts into a database.  
 - We currently use a spreadsheet that shows us a list of all upcoming blends used in production runs. This table also shows the recent transaction history and most recent count date of each blend, so that we can make a decision as to whether the blend should be counted today. Blending manager currently filters the list and then prints it out so inventory personnel can record their counts. Blending manager enters counts back into the spreadsheet and emails the production manager those numbers. Production manager then enters those up-to-date inventory figures into ERP system.
 - Module will be developed to display this list, allow for inventory crew to view the list and enter data, and then display results to the production manager. Goal is to cut down on all these intermediary steps that are currently needed to get our inventory info where it needs to go. 










## Hardware required

Machine with 8GB of RAM will struggle to keep up but can run this application in a pinch. 2.4gHz+ processor with 4+ cores also seems to be a minimum but we have not performed a wide range of tests.

This application will not function as designed if it is set up on a server off-site--we are serving the app over our local network. Additionally, the pyodbc connections that update the Sage 100 tables in our database will only work on a machine that is a trusted member of our local network. Test runs could theoretically be completed by scanning all the table information in the csv files located in db_imports. 



## Specs etc

### Versions:
 - Bootstrap 5
 - jQuery 3.6.0
 - Python 3.9
 - Postgres 13


### Naming:
Conventions follow PEP 8 (https://peps.python.org/pep-0008/#naming-conventions):
 - Functions: all lowercase words, separated by underscore
	- Include a verb at the beginning to indicate what the function does
 - Variables: all lowercase words, separated by underscore
 - Classes (including Models): CamelCase
 - the 'name' parameter of each url path is lowercase words separated by dashes
 - all html template names are lowercase, words not separated by punctuation
 - script files are named all lowercase, separated by underscore



### Misc internal 


List of tables which must be preserved because they are not programmatically updated by scripts:

 - auth_user
 - core_blendingstep
 - core_blendinstruction
 - core_checklistlog
 - core_checklistsubmissionrecord
 - core_chemlocation
 - core_countrecord
 - core_deskoneschedule
 - core_desktwoschedule
 - core_foamfactor
 - core_forklift
 - core_storagetank
 - core_lotnumrecord