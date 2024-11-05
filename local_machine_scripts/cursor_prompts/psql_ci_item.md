# CI_ITEM Table Documentation

## Table Overview
**Table Name:** `ci_item`
**Purpose:** Maintains comprehensive item master data including identification, classification, financial attributes, usage parameters, and various tracking metrics.

## Schema Definition

### Primary Identifiers
- `id` - Unique internal identifier for each item record
- `itemcode` - Unique product code/SKU used to identify the item 
- `itemtype` - Classification of item type (e.g. Finished Good, Raw Material)
- `itemcodedesc` - Human-readable description of the item

### Classification Hierarchy
- `category1` - Primary category classification
- `category2` - Secondary category classification
- `category3` - Tertiary category classification
- `category4` - Quaternary category classification
- `productline` - Product line grouping
- `producttype` - Specific product category
- `commoditycode` - Standard commodity code
- `templateno` - Template reference number

### Financial Information
#### GL Account Keys
- `salesacctkey` - Sales transactions account key
- `costofgoodssoldacctkey` - COGS account key
- `inventoryacctkey` - Inventory valuation account key
- `purchaseacctkey` - Purchasing transactions account key
- `manufacturingcostacctkey` - Manufacturing costs account key

#### Cost & Pricing
- `pricecode` - Pricing tier code
- `standardunitcost` - Standard per unit cost
- `standardunitprice` - Standard selling price
- `commissionrate` - Sales commission percentage
- `basecommamt` - Base commission amount
- `setupcharge` - One-time setup fee
- `lasttotalunitcost` - Latest total unit cost
- `averageunitcost` - Rolling average unit cost
- `salespromotionprice` - Promotional price
- `suggestedretailprice` - MSRP
- `salespromotiondiscountpercent` - Promotional discount
- `totalinventoryvalue` - Total on-hand inventory value

### System Usage Controls
- `useinar` - AR usage flag
- `useinso` - Sales order usage flag
- `useinpo` - Purchase order usage flag
- `useinbm` - BOM usage flag
- `calculatecommission` - Commission calculation flag
- `dropship` - Dropship eligibility flag
- `ebmenabled` - Engineering BOM flag
- `allowbackorders` - Backorder permission flag
- `allowreturns` - Returns permission flag
- `allowtradediscount` - Trade discount permission flag
- `inactiveitem` - Item status flag

### Units & Measurements
- `salesunitofmeasure` - Sales UOM
- `purchaseunitofmeasure` - Purchasing UOM
- `standardunitofmeasure` - Inventory UOM
- `purchaseumconvfctr` - Purchase unit conversion factor
- `salesumconvfctr` - Sales unit conversion factor
- `shipweight` - Shipping weight
- `volume` - Storage/shipping volume

### Inventory Control
- `valuation` - Inventory valuation method
- `defaultwarehousecode` - Primary warehouse
- `restockingmethod` - Restock methodology
- `restockingcharge` - Returns restocking fee
- `procurementtype` - Procurement method (Buy/Make)
- `inventorycycle` - Count cycle assignment
- `routingno` - Manufacturing routing reference
- `plannercode` - Inventory planner ID
- `buyercode` - Purchasing buyer ID
- `lowlevelcode` - Lowest BOM level
- `plannedbymrp` - MRP planning inclusion flag
- `totalquantityonhand` - Current inventory quantity

### Temporal Tracking
- `datecreated` - Record creation date
- `timecreated` - Record creation time
- `dateupdated` - Last update date
- `timeupdated` - Last update time
- `lastsolddate` - Last sale date
- `lastreceiptdate` - Last receipt date
- `salestartingdate` - Promotion start date
- `saleendingdate` - Promotion end date
- `lastphysicalcountdate` - Last physical count date

### Expiration Management
- `tracklotserialexpirationdates` - Expiration tracking flag
- `requireexpirationdate` - Required expiration flag
- `calculateexpdatebasedon` - Expiration calculation basis
- `numberuntilexpiration` - Expiration timeline units
- `calculatesellbybasedon` - Sell-by calculation basis
- `numbertosellbybefore` - Pre sell-by units
- `numbertosellbyafter` - Post sell-by units
- `calculateusebybasedon` - Use-by calculation basis
- `numbertousebybefore` - Pre use-by units
- `numbertousebyafter` - Post use-by units
- `calculatereturnsbasedon` - Returns calculation basis
- `numbertoreturnafter` - Post-return acceptance units

### Vendor References
- `primaryapdivisionno` - Primary AP division
- `primaryvendorno` - Primary vendor ID
- `vendoritemcode` - Vendor's item code

### Additional Attributes
- `extendeddescriptionkey` - Extended description reference
- `printreceiptlabels` - Receipt label printing flag
- `allocatelandedcost` - Landed cost allocation flag
- `warrantycode` - Warranty type reference
- `posttoglbydivision` - Divisional GL posting flag
- `taxclass` - Tax classification code
- `purchasestaxclass` - Purchase tax classification
- `imagefile` - Image reference path
- `explodekititems` - Kit component expansion flag
- `commenttext` - General comments field
- `confirmcostincrinrcptofgoods` - Cost increase confirmation flag
- `salespromotioncode` - Promotion identifier
- `salemethod` - Sales methodology
- `nextlotserialno` - Next lot/serial number
- `attachmentfilename` - Document attachment reference
- `itemimagewidthinpixels` - Image width specification
- `itemimageheightinpixels` - Image height specification
- `averagebackorderfilldays` - Average backorder fulfillment days
- `lastallocatedunitcost` - Latest allocated unit cost

## Usage Notes
This table serves as the central repository for item master data, supporting:
- Product identification and classification
- Financial tracking and costing
- Inventory control and planning
- Expiration and lot tracking
- Vendor relationship management
- System integration and processing rules

The comprehensive attribute set enables detailed item management across all business functions while maintaining relationships with various operational and financial processes.