# Count System Enhancement Plan

## Core Requirements Checklist

### Database Schema Modifications
- [ ] Add `counting_unit` field to `AuditGroup` model
  - [ ] Field type: CharField with choices ("weight", "tote_gauge", "radar")
  - [ ] Include default value ("weight" recommended)
  - [ ] Add appropriate validation
- [ ] Add `sage_quantity` field to count record models:
  - [ ] `BlendComponentCountRecord`
  - [ ] `BlendCountRecord`
  - [ ] `WarehouseCountRecord`
  - [ ] Field type: DecimalField (matching precision of existing quantity fields)
  - [ ] Allow null/blank values

### Form Modifications
- [ ] Update `AuditGroupForm` to include `counting_unit` field
  - [ ] Add appropriate widget (Select/ChoiceField)
  - [ ] Update validation logic
  - [ ] Ensure proper display in admin interface

### Backend Logic Implementation
- [ ] Create conversion system between counting methods and standard units
  - [ ] Function to retrieve counting method information asynchronously
  - [ ] Comparison logic between counting method and CiItem.standardunitofmeasure
  - [ ] Conversion algorithm implementation
  - [ ] Storage mechanism for converted values in sage_quantity field
- [ ] API endpoint for counting method retrieval
  - [ ] Error handling
  - [ ] Response formatting
  - [ ] Performance optimization
- [ ] Signal handlers to automatically update sage_quantity when quantity changes

### Frontend Implementation
- [ ] Enhance CountList page
  - [ ] UI elements for counting method display
  - [ ] JavaScript for asynchronous counting method retrieval
  - [ ] Client-side conversion logic
  - [ ] WebSocket handling for sage_quantity field
  - [ ] Visual indicators for conversion status

## Additional Requirements

### Testing
- [ ] Unit tests for models
- [ ] Unit tests for conversion logic
- [ ] Integration tests for form submission
- [ ] UI/Frontend tests
- [ ] Conversion accuracy verification tests

### Deployment
- [ ] Database migrations
- [ ] Backward compatibility strategy
- [ ] Data backfill plan for existing records
- [ ] Feature flag implementation (if needed)
- [ ] Phased rollout plan
- [ ] Monitoring strategy
- [ ] Conversion error alerting system

### Documentation & Training
- [ ] Update API documentation
- [ ] User documentation for counting methods
- [ ] Document conversion formulas and logic
- [ ] Prepare training materials
- [ ] Schedule training sessions
- [ ] Create troubleshooting guide for conversion issues

## Implementation Timeline
- [ ] Phase 1: Database schema modifications
- [ ] Phase 2: Backend logic implementation
- [ ] Phase 3: Frontend implementation
- [ ] Phase 4: Testing
- [ ] Phase 5: Documentation and training
- [ ] Phase 6: Deployment

## Risk Assessment
- [ ] Identify potential conversion errors
- [ ] Plan for handling edge cases
- [ ] Data integrity verification process
- [ ] Rollback strategy
- [ ] Performance impact analysis
- [ ] User adoption challenges