from django.db import models

class WarehouseCountRecord(models.Model):
    item_code = models.TextField(blank=True, null=True)
    item_description = models.TextField(blank=True, null=True)
    expected_quantity = models.DecimalField(max_digits=50, decimal_places=5, blank=True, null=True)
    counted_quantity = models.DecimalField(max_digits=50, decimal_places=5, blank=True, null=True)
    counted_date = models.DateField(blank=True, null=True)
    variance = models.DecimalField(max_digits=50, decimal_places=5, blank=True, null=True)
    counted = models.BooleanField(default=False)
    count_type = models.TextField(blank=True, null=True)
    collection_id = models.TextField(blank=True, null=True)
    counted_by = models.TextField(blank=True, null=True)

    def __str__(self):
        return self.item_code + "; " + str(self.counted_date)

class SpecSheetData(models.Model):
    item_code = models.TextField(db_column='ItemCode', primary_key=True,)
    component_item_code = models.TextField(db_column='ComponentItemCode', blank=True)
    product_class = models.TextField(db_column='Product Class', blank=True)
    water_flush = models.TextField(db_column='Water Flush', blank=True)
    solvent_flush = models.TextField(db_column='Solvent Flush', blank=True)
    soap_flush = models.TextField(db_column='Soap Flush', blank=True)
    oil_flush = models.TextField(db_column='Oil Flush', blank=True)
    polish_flush = models.TextField(db_column='Polish Flush', blank=True)
    package_retain = models.TextField(db_column='Package Retain', blank=True)
    uv_protect = models.TextField(db_column='UV  Protection', blank=True)
    freeze_protect = models.TextField(db_column='Freeze Protection', blank=True,)
    min_weight = models.TextField(db_column='Min Weight (N)', blank=True)
    target_weight = models.TextField(db_column='TARGET WEIGHT (N)', blank=True)
    max_weight = models.TextField(db_column='Max Weight (N)', blank=True)
    upc = models.TextField(db_column='New UPC', blank=True)
    scc = models.TextField(db_column='SCC', blank=True)
    us_dot = models.TextField(db_column='US - DOT', blank=True)
    special_notes = models.TextField(db_column='Special Notes', blank=True)
    eu_case_marking = models.TextField(db_column='Europe HAZ', blank=True)
    haz_symbols = models.TextField(db_column='Haz Symbols', blank=True)
    pallet_footprint = models.TextField(db_column='Current Footprint', blank=True)
    notes = models.TextField(db_column='Notes', blank=True)

    class Meta:
        managed = False
        db_table = 'specsheet_data'


class SpecSheetLabels(models.Model):
    item_code = models.TextField(db_column='ItemCode', primary_key=True,)
    description = models.TextField(db_column='Description', blank=True,)
    weight_code = models.TextField(db_column='Weight Code', blank=True,)
    location = models.TextField(db_column='Shelf', blank=True)
    
    class Meta:
        managed = False
        db_table = 'specsheet_labels'

class SpecsheetState(models.Model):
    item_code = models.CharField(max_length=255)
    po_number = models.CharField(max_length=255)
    juliandate = models.CharField(max_length=255)
    state_json = models.JSONField(blank=True, null=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=['item_code', 'po_number', 'juliandate'], name='unique_specsheet_state')
        ]

    def __str__(self):
        return f"{self.item_code}-{self.po_number}-{self.juliandate}"
    
class AuditGroup(models.Model):
    item_code = models.TextField(blank=True, null=True)
    audit_group = models.TextField(blank=True, null=True)

    def __str__(self):
        return self.item_code + "; " + self.audit_group
    