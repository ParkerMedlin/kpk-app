# Bill of Materials Table Documentation

## Table Overview
**Table Name:** `bill_of_materials`  
**Purpose:** Maintains the hierarchical relationships between manufactured items and their component parts, tracking specifications, quantities, and inventory metrics for production planning.

## Schema Definition

### Primary Identifiers
- `id` - Unique identifier for each BOM record
- `item_code` - Finished good identifier
- `component_item_code` - Component/raw material identifier

### Component Details
- `component_item_description` - Descriptive text for the component
- `item_description` - Descriptive text for the finished good
- `procurementtype` - Method of procurement/sourcing
- `foam_factor` - Foam characteristics specification
- `standard_uom` - Standard unit of measure

### Quantity Metrics
- `qtyperbill` - Quantity required per bill of materials
- `qtyonhand` - Current quantity available in inventory
- `scrap_percent` - Expected material loss percentage
- `weightpergal` - Weight per gallon measurement

### Additional Information
- `comment_text` - Notes and additional specifications

## Usage Notes
This table serves as the foundation for:
- Production planning and material requirements
- Component relationship mapping
- Inventory requirement calculations
- Manufacturing specifications reference
- Bill of materials explosion/implosion analysis

The structure supports multi-level bills of material, enabling complex product structures while maintaining detailed component specifications and quantity requirements. 