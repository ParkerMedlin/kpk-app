# Tank Level Log Table Documentation

## Table Overview
**Table Name:** `core_tanklevellog`  
**Purpose:** Records temporal measurements of tank fill levels, volumes, and capacity metrics for monitoring and analysis purposes.

## Schema Definition

### Primary Identifier
- `id` - Unique identifier for each tank level log entry

### Temporal Information
- `timestamp` - Precise datetime of the tank level measurement. Records a new record every 5 minutes.

### Tank Identification
- `tank_name` - Unique identifier/name of the monitored tank

### Measurement Metrics
- `fill_percentage` - Current tank fill level expressed as a percentage
- `fill_height_inches` - Current fill height measured in inches
- `height_capacity_inches` - Maximum height capacity of the tank in inches
- `filled_gallons` - Current volume of liquid in the tank measured in gallons

## Usage Notes
This table serves as a time-series record of tank levels, enabling:
- Historical analysis of tank fill patterns
- Capacity utilization monitoring
- Volume tracking over time
- Tank level trend analysis
- Operational monitoring and alerting

The combination of percentage, height, and volume measurements provides comprehensive insight into tank status at any given timestamp. 