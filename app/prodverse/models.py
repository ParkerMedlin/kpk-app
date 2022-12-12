from django.db import models

class IssueSheetNeeded(models.Model):
    id = models.IntegerField(primary_key=True)
    id2 = models.DecimalField(max_digits=50, decimal_places=1, blank=True, null=True)
    bill_no = models.TextField(blank=True, null=True)
    blend_pn = models.TextField(blank=True, null=True)
    blend_desc = models.TextField(blank=True, null=True)
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