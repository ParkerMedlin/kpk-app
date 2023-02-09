from django.db import models

class IssueSheetNeeded(models.Model):
    id = models.IntegerField(primary_key=True)
    id2 = models.DecimalField(max_digits=50, decimal_places=1, blank=True, null=True)
    item_code = models.TextField(blank=True, null=True)
    component_item_code = models.TextField(blank=True, null=True)
    component_item_description = models.TextField(blank=True, null=True)
    adjustedrunqty = models.DecimalField(max_digits=50, decimal_places=5, blank=True, null=True)
    qtyonhand = models.DecimalField(max_digits=50, decimal_places=5, blank=True, null=True)
    starttime = models.DecimalField(max_digits=50, decimal_places=7, blank=True, null=True)
    prodline = models.TextField(blank=True, null=True)
    oh_after_run = models.DecimalField(max_digits=50, decimal_places=5, blank=True, null=True)
    week_calc = models.DecimalField(max_digits=50, decimal_places=1, blank=True, null=True)
    batchnum1 = models.TextField(blank=True, null=True)
    batchqty1 = models.TextField(blank=True, null=True)
    batchnum2 = models.TextField(blank=True, null=True)
    batchqty2 = models.TextField(blank=True, null=True)
    batchnum3 = models.TextField(blank=True, null=True)
    batchqty3 = models.TextField(blank=True, null=True)
    batchnum4 = models.TextField(blank=True, null=True)
    batchqty4 = models.TextField(blank=True, null=True)
    batchnum5 = models.TextField(blank=True, null=True)
    batchqty5 = models.TextField(blank=True, null=True)
    batchnum6 = models.TextField(blank=True, null=True)
    batchqty6 = models.TextField(blank=True, null=True)
    uniqchek = models.TextField(blank=True, null=True)

    class Meta:
        managed = False
        db_table = 'issue_sheet_needed'

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