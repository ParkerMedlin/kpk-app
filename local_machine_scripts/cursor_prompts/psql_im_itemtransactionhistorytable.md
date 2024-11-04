# Item Transaction History Table Documentation

## Table Overview
**Table Name:** `im_itemtransactionhistory`  
**Purpose:** Tracks detailed history of item transactions across warehouses, including costs, pricing, and various reference information.

## Schema Definition

### Primary Identifiers
- `id` - Unique identifier for each transaction record
- `itemcode` - Item identification code
- `warehousecode` - Location identifier
- `entryno` - Entry number for the transaction
- `sequenceno` - Sequence number for ordering

### Transaction Details
- `transactiondate` - Date of the transaction
- `transactioncode` - Code indicating transaction type
- `imtransactionentrycomment` - Transaction comments/notes
- `referencedate` - Reference date for the transaction
- `formatted_time` - Formatted timestamp of the transaction

### Financial Information
- `unitcost` - Cost per unit
- `allocatedcost` - Allocated cost amount
- `unitprice` - Price per unit
- `extendedprice` - Total extended price
- `extendedcost` - Total extended cost
- `extendedstandardcost` - Standard cost calculation
- `transactionqty` - Quantity involved in transaction

### Fiscal Information
- `fiscalcalyear` - Fiscal calendar year
- `fiscalcalperiod` - Fiscal period within the year

### Reference Information
#### Vendor/Customer
- `apdivisionno` - Accounts Payable division number
- `vendorno` - Vendor identification number
- `ardivisionno` - Accounts Receivable division number
- `customerno` - Customer identification number
- `shiptocode` - Shipping destination code

#### Invoice/Receipt
- `invoicetype` - Type of invoice
- `invoicehistoryheaderseqno` - Invoice history sequence number
- `receipthistoryheaderseqno` - Receipt history sequence number
- `receipthistorypurchaseorderno` - Associated PO number

#### Work Ticket Information
- `workticketkey` - Work ticket identifier
- `workticketno` - Work ticket number
- `workticketdesc` - Work ticket description
- `workticketlinekey` - Work ticket line item key
- `workticketstepno` - Work ticket step number
- `workticketclasscode` - Classification code for work ticket
- `activitycode` - Activity identifier
- `workcenter` - Work center code
- `toolcode` - Tool identifier

### Journal Information
- `sourcejournal` - Source journal identifier
- `journalnoglbatchno` - Journal/GL batch number

### Audit Trail
- `dateupdated` - Last update date
- `timeupdated` - Last update time
- `userupdatedkey` - User who last updated the record

## Usage Notes
This table serves as a comprehensive transaction log for inventory items, capturing all movements, cost changes, and related business processes. It maintains relationships with vendors, customers, work orders, and financial journals, making it a crucial component for inventory tracking and financial reconciliation.
