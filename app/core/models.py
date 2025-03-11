from pickle import TRUE
from xml.etree.ElementTree import TreeBuilder
from django.db import models
from django.utils import timezone
import os
from django.contrib.postgres.fields import ArrayField

class AdjustmentStatistic(models.Model):
    id = models.IntegerField(primary_key=True)
    item_code = models.TextField(blank=True, null=True)
    item_description = models.TextField(blank=True, null=True)
    adjustment_sum = models.DecimalField(max_digits=30, decimal_places=2, blank=True, null=True)
    run_sum = models.DecimalField(max_digits=30, decimal_places=2, blank=True, null=True)
    max_adjustment = models.DecimalField(max_digits=30, decimal_places=2, blank=True, null=True)
    adj_percentage_of_run = models.DecimalField(max_digits=30, decimal_places=4, blank=True, null=True)    
    expected_quantity = models.DecimalField(max_digits=10, decimal_places=5, blank=True, null=True)
    last_count_quantity = models.DecimalField(max_digits=10, decimal_places=5, blank=True, null=True)
    last_count_date = models.DateField(blank=True, null=True)
    procurement_type = models.TextField(blank=True, null=True)
    standard_uom = models.TextField(blank=True, null=True)

    class Meta:
        managed = False
        db_table = 'adjustment_statistic'

class AttendanceRecord(models.Model):
    employee_name = models.CharField(max_length=100)
    adp_employee_id = models.CharField(max_length=10)
    day = models.CharField(max_length=3)
    punch_date = models.DateField()
    time_in = models.TimeField(blank=True, null=True)
    time_out = models.TimeField(blank=True, null=True)
    hours = models.DecimalField(max_digits=6, decimal_places=4, blank=True, null=True) 
    pay_code = models.CharField(max_length=10, blank=True, null=True)
    absent = models.BooleanField(blank=True, null=True)
    tardy = models.BooleanField(blank=True, null=True)
    excused = models.BooleanField(blank=True, null=True)

    def __str__(self):
        return f"{self.employee} - {self.date}"

class BillOfMaterials(models.Model):
    id = models.IntegerField(primary_key=True)
    item_code = models.TextField(blank=True, null=True)
    component_item_code = models.TextField(blank=True, null=True)
    component_item_description = models.TextField(blank=True, null=True)
    item_description = models.TextField(blank=True, null=True)
    procurementtype = models.TextField(blank=True, null=True)
    foam_factor = models.DecimalField(max_digits=100, decimal_places=2, blank=True, null=True)
    standard_uom = models.TextField(blank=True, null=True)
    qtyperbill = models.DecimalField(max_digits=30, decimal_places=5, blank=True, null=True)
    weightpergal = models.TextField(blank=True, null=True)
    qtyonhand = models.DecimalField(max_digits=10, decimal_places=5, blank=True, null=True)
    comment_text = models.TextField(blank=True, null=True)

    class Meta:
        managed = False
        db_table = 'bill_of_materials'

class FoamFactor(models.Model):
    item_code = models.TextField(blank=True, null=True)
    item_description = models.TextField(blank=True, null=True)
    factor = models.DecimalField(max_digits=100, decimal_places=2, blank=True, null=True)

    def __str__(self):
        return self.item_code
    
class PartialContainerLabelLog(models.Model):
    item_code = models.TextField(blank=True, null=True)
    log_timestamp = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.item_code

class BlendProtection(models.Model):
    item_code = models.TextField(db_column='ItemCode', primary_key=True)
    uv_protection = models.TextField(db_column='UV  Protection', blank=True, null=True)
    freeze_protection = models.TextField(db_column='Freeze Protection', blank=True, null=True)

    class Meta:
        managed = False
        db_table = 'blend_protection'

class BlendTankRestriction(models.Model):
    item_code = models.TextField(db_column='ItemCode', primary_key=True)
    range_one_minimum = models.DecimalField(max_digits=50, decimal_places=1, blank=True, null=True)
    range_one_maximum = models.DecimalField(max_digits=50, decimal_places=1, blank=True, null=True)
    range_two_minimum = models.DecimalField(max_digits=50, decimal_places=1, blank=True, null=True)
    range_two_maximum = models.DecimalField(max_digits=50, decimal_places=1, blank=True, null=True)

    class Meta:
        managed = True

# Sage table
class BmBillDetail(models.Model):
    id = models.IntegerField(primary_key=True)
    billno = models.TextField(blank=True, null=True)
    revision = models.TextField(blank=True, null=True)
    linekey = models.TextField(blank=True, null=True)
    lineseqno = models.TextField(blank=True, null=True)
    componentitemcode = models.TextField(blank=True, null=True)
    componentrevision = models.TextField(blank=True, null=True)
    itemtype = models.TextField(blank=True, null=True)
    componentdesc = models.TextField(blank=True, null=True)
    engineeringdrawingfindno = models.TextField(blank=True, null=True)
    engineeringchangeaddno = models.TextField(blank=True, null=True)
    engineeringchangeadddate = models.DateField(blank=True, null=True)
    engineeringchangedelno = models.TextField(blank=True, null=True)
    engineeringchangedeldate = models.DateField(blank=True, null=True)
    workorderstepno = models.TextField(blank=True, null=True)
    billtype = models.TextField(blank=True, null=True)
    commenttext = models.TextField(blank=True, null=True)
    miscchargeglacctkey = models.TextField(blank=True, null=True)
    setupcharge = models.TextField(blank=True, null=True)
    unitofmeasure = models.TextField(blank=True, null=True)
    quantityperbill = models.DecimalField(max_digits=50, decimal_places=5, blank=True, null=True)
    standardunitcost = models.DecimalField(max_digits=50, decimal_places=5, blank=True, null=True)
    scrappercent = models.DecimalField(max_digits=50, decimal_places=5, blank=True, null=True)
    workticketstepno = models.TextField(blank=True, null=True)

    class Meta:
        managed = False
        db_table = 'bm_billdetail'

# Sage table
class BmBillHeader(models.Model):
    id = models.IntegerField(primary_key=True)
    billno = models.TextField(blank=True, null=True)
    revision = models.TextField(blank=True, null=True)
    billtype = models.TextField(blank=True, null=True)
    drawingno = models.TextField(blank=True, null=True)
    drawingrevision = models.TextField(blank=True, null=True)
    datelastused = models.DateField(blank=True, null=True)
    routingno = models.TextField(blank=True, null=True)
    billhasoptions = models.TextField(blank=True, null=True)
    currentbillrevision = models.TextField(blank=True, null=True)
    optioninteractions = models.TextField(blank=True, null=True)
    optioncategories = models.TextField(blank=True, null=True)
    printcomponentdetail = models.TextField(blank=True, null=True)
    maximumlotsize = models.DecimalField(max_digits=50, decimal_places=5, blank=True, null=True)
    yieldpercent = models.DecimalField(max_digits=50, decimal_places=5, blank=True, null=True)
    billdesc1 = models.TextField(blank=True, null=True)
    billdesc2 = models.TextField(blank=True, null=True)
    datecreated = models.DateField(blank=True, null=True)
    timecreated = models.TextField(blank=True, null=True)
    usercreatedkey = models.TextField(blank=True, null=True)
    dateupdated = models.DateField(blank=True, null=True)
    timeupdated = models.TextField(blank=True, null=True)
    userupdatedkey = models.TextField(blank=True, null=True)
    templateno = models.TextField(blank=True, null=True)
    templaterevisionno = models.TextField(blank=True, null=True)

    class Meta:
        managed = False
        db_table = 'bm_billheader'

class ItemLocation(models.Model):
    item_code = models.TextField(blank=True, null=True)
    item_description = models.TextField(blank=True, null=True)
    unit = models.TextField(blank=True, null=True)
    storage_type = models.TextField(blank=True, null=True)
    zone = models.TextField(blank=True, null=True)
    bin = models.TextField(blank=True, null=True)
    item_type = models.TextField(blank=True, null=True)

    def __str__(self):
        return self.item_code

class AuditGroup(models.Model):
    item_code = models.TextField(blank=True, null=True)
    item_description = models.TextField(blank=True, null=True)
    audit_group = models.TextField(blank=True, null=True)
    item_type = models.TextField(blank=True, null=True)

    def __str__(self):
        return self.item_code + "; " + self.audit_group

class BlendCountRecord(models.Model):
    item_code = models.TextField(blank=True, null=True)
    item_description = models.TextField(blank=True, null=True)
    expected_quantity = models.DecimalField(max_digits=50, decimal_places=5, blank=True, null=True)
    counted_quantity = models.DecimalField(max_digits=50, decimal_places=5, blank=True, null=True)
    counted_date = models.DateField(blank=True, null=True)
    variance = models.DecimalField(max_digits=50, decimal_places=5, blank=True, null=True)
    counted = models.BooleanField(default=False)
    count_type = models.TextField(blank=True, null=True)
    collection_id = models.TextField(blank=True, null=True)
    comment = models.TextField(blank=True, null=True)
    containers = models.JSONField(default=list, blank=True, null=True)

    def __str__(self):
        return self.item_code + "; " + str(self.counted_date)
    
class BlendComponentCountRecord(models.Model):
    item_code = models.TextField(blank=True, null=True)
    item_description = models.TextField(blank=True, null=True)
    expected_quantity = models.DecimalField(max_digits=50, decimal_places=5, blank=True, null=True)
    counted_quantity = models.DecimalField(max_digits=50, decimal_places=5, blank=True, null=True)
    counted_date = models.DateField(blank=True, null=True)
    variance = models.DecimalField(max_digits=50, decimal_places=5, blank=True, null=True)
    counted = models.BooleanField(default=False)
    count_type = models.TextField(blank=True, null=True)
    collection_id = models.TextField(blank=True, null=True)
    comment = models.TextField(blank=True, null=True)
    containers = models.JSONField(default=list, blank=True, null=True)

    def __str__(self):
        return self.item_code + "; " + str(self.counted_date)

class ContainerData(models.Model):
    container_name = models.TextField()
    container_tare_weight = models.DecimalField(max_digits=10, decimal_places=2, blank=True, null=True)

    def __str__(self):
        return self.container_name

class CountRecordSubmissionLog(models.Model):
    record_id = models.TextField(blank=True, null=True)
    count_type = models.TextField(blank=True, null=True)
    updated_by = models.TextField(blank=True, null=True)
    update_timestamp = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.record_id + "; " + str(self.update_timestamp) + "; " + self.count_type

class CountCollectionLink(models.Model):
    link_order = models.IntegerField(blank=False, default=0)
    collection_name = models.TextField(blank=True, null=True)
    collection_id = models.TextField(blank=True, null=True)
    count_id_list = models.JSONField(default=list)
    record_type = models.TextField(blank=True, null=True)

    def __str__(self):
        return self.collection_id 

class Forklift(models.Model):
    unit_number = models.TextField(blank=True, null=True, unique=True)
    make = models.TextField(blank=True, null=True)
    dept = models.TextField(blank=True, null=True)
    normal_operator = models.TextField(blank=True, null=True)
    forklift_type = models.TextField(blank=True, null=True)
    model_no = models.TextField(blank=True, null=True)
    serial_no = models.TextField(blank=True, null=True)

    def __str__(self):
        return self.unit_number

class ChecklistSubmissionRecord(models.Model):
    unit_number = models.TextField(blank=True, null=True)
    submission_status = models.BooleanField()
    normal_operator = models.TextField(blank=True, null=True)
    this_operator = models.TextField(blank=True, null=True)
    date_checked = models.DateField(auto_now_add=True)

    def __str__(self):
        return self.date_checked
 
class ChecklistLog(models.Model):
    submitted_date = models.DateTimeField(auto_now_add=True)
    operator_name = models.CharField(max_length=100, null=True)
    forklift = models.ForeignKey(Forklift, on_delete=models.SET('FORKLIFT DELETED'))
    serial_number = models.CharField(max_length=100)
    engine_oil = models.CharField(max_length=5)
    engine_oil_comments = models.TextField(blank=True)
    propane_tank = models.CharField(max_length=5)
    propane_tank_comments = models.TextField(blank=True)
    radiator_leaks = models.CharField(max_length=5)
    radiator_leaks_comments = models.TextField(blank=True)
    tires = models.CharField(max_length=5)
    tires_comments = models.TextField(blank=True)
    mast_and_forks = models.CharField(max_length=5)
    mast_and_forks_comments = models.TextField(blank=True)
    leaks = models.CharField(max_length=5)
    leaks_comments = models.TextField(blank=True)
    horn = models.CharField(max_length=5)
    horn_comments = models.TextField(blank=True)
    driver_compartment = models.CharField(max_length=5)
    driver_compartment_comments = models.TextField(blank=True)
    seatbelt = models.CharField(max_length=5)
    seatbelt_comments = models.TextField(blank=True)
    battery = models.CharField(max_length=5)
    battery_comments = models.TextField(blank=True)
    safety_equipment = models.CharField(max_length=5)
    safety_equipment_comments = models.TextField(blank=True)
    steering = models.CharField(max_length=5)
    steering_comments = models.TextField(blank=True)
    brakes = models.CharField(max_length=5)
    brakes_comments = models.TextField(blank=True)

    def __str__(self):
        return self.operator_name

# Sage table
class CiItem(models.Model):
    id = models.IntegerField(primary_key=True)
    itemcode = models.TextField(blank=True, null=True)
    itemtype = models.TextField(blank=True, null=True)
    itemcodedesc = models.TextField(blank=True, null=True)
    extendeddescriptionkey = models.TextField(blank=True, null=True)
    useinar = models.TextField(blank=True, null=True)
    useinso = models.TextField(blank=True, null=True)
    useinpo = models.TextField(blank=True, null=True)
    useinbm = models.TextField(blank=True, null=True)
    calculatecommission = models.TextField(blank=True, null=True)
    dropship = models.TextField(blank=True, null=True)
    ebmenabled = models.TextField(blank=True, null=True)
    pricecode = models.TextField(blank=True, null=True)
    printreceiptlabels = models.TextField(blank=True, null=True)
    allocatelandedcost = models.TextField(blank=True, null=True)
    warrantycode = models.TextField(blank=True, null=True)
    salesunitofmeasure = models.TextField(blank=True, null=True)
    purchaseunitofmeasure = models.TextField(blank=True, null=True)
    standardunitofmeasure = models.TextField(blank=True, null=True)
    posttoglbydivision = models.TextField(blank=True, null=True)
    salesacctkey = models.TextField(blank=True, null=True)
    costofgoodssoldacctkey = models.TextField(blank=True, null=True)
    inventoryacctkey = models.TextField(blank=True, null=True)
    purchaseacctkey = models.TextField(blank=True, null=True)
    manufacturingcostacctkey = models.TextField(blank=True, null=True)
    taxclass = models.TextField(blank=True, null=True)
    purchasestaxclass = models.TextField(blank=True, null=True)
    productline = models.TextField(blank=True, null=True)
    producttype = models.TextField(blank=True, null=True)
    valuation = models.TextField(blank=True, null=True)
    defaultwarehousecode = models.TextField(blank=True, null=True)
    primaryapdivisionno = models.TextField(blank=True, null=True)
    primaryvendorno = models.TextField(blank=True, null=True)
    imagefile = models.TextField(blank=True, null=True)
    category1 = models.TextField(blank=True, null=True)
    category2 = models.TextField(blank=True, null=True)
    category3 = models.TextField(blank=True, null=True)
    category4 = models.TextField(blank=True, null=True)
    explodekititems = models.TextField(blank=True, null=True)
    shipweight = models.TextField(blank=True, null=True)
    commenttext = models.TextField(blank=True, null=True)
    restockingmethod = models.TextField(blank=True, null=True)
    standardunitcost = models.DecimalField(max_digits=50, decimal_places=5, blank=True, null=True)
    standardunitprice = models.DecimalField(max_digits=50, decimal_places=5, blank=True, null=True)
    commissionrate = models.DecimalField(max_digits=50, decimal_places=5, blank=True, null=True)
    basecommamt = models.DecimalField(max_digits=50, decimal_places=5, blank=True, null=True)
    purchaseumconvfctr = models.DecimalField(max_digits=50, decimal_places=5, blank=True, null=True)
    salesumconvfctr = models.DecimalField(max_digits=50, decimal_places=5, blank=True, null=True)
    volume = models.DecimalField(max_digits=50, decimal_places=5, blank=True, null=True)
    restockingcharge = models.DecimalField(max_digits=50, decimal_places=5, blank=True, null=True)
    procurementtype = models.TextField(blank=True, null=True)
    datecreated = models.DateField(blank=True, null=True)
    timecreated = models.TextField(blank=True, null=True)
    usercreatedkey = models.TextField(blank=True, null=True)
    dateupdated = models.DateField(blank=True, null=True)
    timeupdated = models.TextField(blank=True, null=True)
    userupdatedkey = models.TextField(blank=True, null=True)
    allowbackorders = models.TextField(blank=True, null=True)
    allowreturns = models.TextField(blank=True, null=True)
    allowtradediscount = models.TextField(blank=True, null=True)
    confirmcostincrinrcptofgoods = models.TextField(blank=True, null=True)
    lastsolddate = models.DateField(blank=True, null=True)
    lastreceiptdate = models.DateField(blank=True, null=True)
    salespromotioncode = models.TextField(blank=True, null=True)
    salestartingdate = models.DateField(blank=True, null=True)
    saleendingdate = models.DateField(blank=True, null=True)
    salemethod = models.TextField(blank=True, null=True)
    nextlotserialno = models.TextField(blank=True, null=True)
    inventorycycle = models.TextField(blank=True, null=True)
    routingno = models.TextField(blank=True, null=True)
    plannercode = models.TextField(blank=True, null=True)
    buyercode = models.TextField(blank=True, null=True)
    lowlevelcode = models.TextField(blank=True, null=True)
    plannedbymrp = models.TextField(blank=True, null=True)
    vendoritemcode = models.TextField(blank=True, null=True)
    setupcharge = models.TextField(blank=True, null=True)
    attachmentfilename = models.TextField(blank=True, null=True)
    itemimagewidthinpixels = models.DecimalField(max_digits=50, decimal_places=5, blank=True, null=True)
    itemimageheightinpixels = models.DecimalField(max_digits=50, decimal_places=5, blank=True, null=True)
    lasttotalunitcost = models.DecimalField(max_digits=50, decimal_places=5, blank=True, null=True)
    averageunitcost = models.DecimalField(max_digits=50, decimal_places=5, blank=True, null=True)
    salespromotionprice = models.DecimalField(max_digits=50, decimal_places=5, blank=True, null=True)
    suggestedretailprice = models.DecimalField(max_digits=50, decimal_places=5, blank=True, null=True)
    salespromotiondiscountpercent = models.DecimalField(max_digits=50, decimal_places=5, blank=True, null=True)
    totalquantityonhand = models.DecimalField(max_digits=50, decimal_places=5, blank=True, null=True)
    averagebackorderfilldays = models.DecimalField(max_digits=50, decimal_places=5, blank=True, null=True)
    lastallocatedunitcost = models.DecimalField(max_digits=50, decimal_places=5, blank=True, null=True)
    totalinventoryvalue = models.DecimalField(max_digits=50, decimal_places=5, blank=True, null=True)
    inactiveitem = models.TextField(blank=True, null=True)
    lastphysicalcountdate = models.DateField(blank=True, null=True)
    commoditycode = models.TextField(blank=True, null=True)
    templateno = models.TextField(blank=True, null=True)
    tracklotserialexpirationdates = models.TextField(blank=True, null=True)
    requireexpirationdate = models.TextField(blank=True, null=True)
    calculateexpdatebasedon = models.TextField(blank=True, null=True)
    numberuntilexpiration = models.DecimalField(max_digits=50, decimal_places=5, blank=True, null=True)
    calculatesellbybasedon = models.TextField(blank=True, null=True)
    numbertosellbybefore = models.DecimalField(max_digits=50, decimal_places=5, blank=True, null=True)
    numbertosellbyafter = models.DecimalField(max_digits=50, decimal_places=5, blank=True, null=True)
    calculateusebybasedon = models.TextField(blank=True, null=True)
    numbertousebybefore = models.DecimalField(max_digits=50, decimal_places=5, blank=True, null=True)
    numbertousebyafter = models.DecimalField(max_digits=50, decimal_places=5, blank=True, null=True)
    calculatereturnsbasedon = models.TextField(blank=True, null=True)
    numbertoreturnafter = models.DecimalField(max_digits=50, decimal_places=5, blank=True, null=True)

    class Meta:
        managed = False
        db_table = 'ci_item'

class ComponentUsage(models.Model):
    id = models.AutoField(primary_key=True)
    start_time = models.DecimalField(max_digits=12, decimal_places=8, null=True)
    run_component_qty = models.DecimalField(max_digits=7, decimal_places=4, null=True)
    component_on_hand_qty = models.DecimalField(max_digits=7, decimal_places=4, null=True)
    foam_factor = models.DecimalField(max_digits=3, decimal_places=2, null=True)
    cumulative_component_run_qty = models.DecimalField(max_digits=7, decimal_places=4, null=True)
    component_onhand_after_run = models.DecimalField(max_digits=7, decimal_places=4, null=True)
    item_run_qty = models.DecimalField(max_digits=7, decimal_places=4, null=True)
    qty_per_bill = models.DecimalField(max_digits=7, decimal_places=4, null=True)
    item_code = models.TextField(blank=True, null=True)
    prod_line = models.TextField(blank=True, null=True)
    po_number = models.TextField(blank=True, null=True)
    component_item_description = models.TextField(blank=True, null=True)
    component_item_code = models.TextField(blank=True, null=True)
    procurement_type = models.TextField(blank=True, null=True)

    class Meta:
        managed = False
        db_table = 'component_usage'

class ComponentShortage(models.Model):
    id = models.AutoField(primary_key=True)
    start_time = models.DecimalField(max_digits=12, decimal_places=8, null=True)
    run_component_qty = models.DecimalField(max_digits=7, decimal_places=4, null=True)
    component_on_hand_qty = models.DecimalField(max_digits=7, decimal_places=4, null=True)
    foam_factor = models.DecimalField(max_digits=3, decimal_places=2, null=True)
    cumulative_component_run_qty = models.DecimalField(max_digits=7, decimal_places=4, null=True)
    component_onhand_after_run = models.DecimalField(max_digits=7, decimal_places=4, null=True)
    item_run_qty = models.DecimalField(max_digits=7, decimal_places=4, null=True)
    qty_per_bill = models.DecimalField(max_digits=7, decimal_places=4, null=True)
    item_code = models.TextField(blank=True, null=True)
    prod_line = models.TextField(blank=True, null=True)
    po_number = models.TextField(blank=True, null=True)
    component_item_description = models.TextField(blank=True, null=True)
    component_item_code = models.TextField(blank=True, null=True)
    procurement_type = models.TextField(blank=True, null=True)
    total_shortage = models.DecimalField(max_digits=7, decimal_places=4, null=True)
    last_txn_code = models.TextField(blank=True, null=True)
    last_txn_date = models.DateField(blank=True, null=True)
    last_count_quantity = models.DecimalField(max_digits=7, decimal_places=2, null=True)
    last_count_date = models.DateField(blank=True, null=True)
    one_wk_short = models.DecimalField(max_digits=100, decimal_places=2, null=True)
    two_wk_short = models.DecimalField(max_digits=100, decimal_places=2, null=True)
    three_wk_short = models.DecimalField(max_digits=100, decimal_places=2, null=True)
    unscheduled_short = models.DecimalField(max_digits=100, decimal_places=2, null=True)
    next_order_due = models.DateField(blank=True, null=True)
    component_instance_count = models.IntegerField()
    run_component_demand = models.DecimalField(max_digits=100, decimal_places=5, null=True)

    class Meta:
        managed = False
        db_table = 'component_shortage'

class SubComponentUsage(models.Model):
    id = models.AutoField(primary_key=True)
    id2 = models.IntegerField(blank=True, null=True)
    item_run_qty = models.DecimalField(max_digits=100, decimal_places=4, null=True)
    start_time = models.DecimalField(max_digits=100, decimal_places=4, null=True)
    qty_per_bill = models.DecimalField(max_digits=100, decimal_places=10, null=True)
    subcomponent_onhand_qty = models.DecimalField(max_digits=100, decimal_places=4, null=True)
    subcomponent_run_qty = models.DecimalField(max_digits=100, decimal_places=4, null=True)
    subcomponent_onhand_after_run = models.DecimalField(max_digits=100, decimal_places=4, null=True)
    cumulative_subcomponent_run_qty = models.DecimalField(max_digits=100, decimal_places=4, null=True)
    subcomponent_item_description = models.TextField(blank=True, null=True)
    subcomponent_item_code = models.TextField(blank=True, null=True)
    po_number = models.TextField(blank=True, null=True)
    item_code = models.TextField(blank=True, null=True)
    component_item_code = models.TextField(blank=True, null=True)
    component_item_description = models.TextField(blank=True, null=True)
    prod_line = models.TextField(blank=True, null=True)
    standard_uom = models.TextField(blank=True, null=True)

    class Meta:
        managed = False
        db_table = 'blend_subcomponent_usage'

class SubComponentShortage(models.Model):
    id = models.AutoField(primary_key=True)
    id2 = models.IntegerField(blank=True, null=True)
    max_possible_blend = models.DecimalField(max_digits=100, decimal_places=4, null=True)
    subcomponent_onhand_qty = models.DecimalField(max_digits=100, decimal_places=4, null=True)
    qty_per_bill = models.DecimalField(max_digits=100, decimal_places=4, null=True)
    start_time = models.DecimalField(max_digits=100, decimal_places=4, null=True)
    item_run_qty = models.DecimalField(max_digits=100, decimal_places=4, null=True)
    item_code = models.TextField(blank=True, null=True)
    po_number = models.TextField(blank=True, null=True)
    prod_line = models.TextField(blank=True, null=True)
    component_item_code = models.TextField(blank=True, null=True)
    component_item_description = models.TextField(blank=True, null=True)
    subcomponent_item_code = models.TextField(blank=True, null=True)
    subcomponent_item_description = models.TextField(blank=True, null=True)
    standard_uom = models.TextField(blank=True, null=True)
    next_order_due = models.DateField(blank=True, null=True)
    one_wk_short = models.DecimalField(max_digits=100, decimal_places=4, null=True)
    two_wk_short = models.DecimalField(max_digits=100, decimal_places=4, null=True)
    three_wk_short = models.DecimalField(max_digits=100, decimal_places=4, null=True)
    total_short = models.DecimalField(max_digits=100, decimal_places=4, null=True)
    unscheduled_short = models.DecimalField(max_digits=100, decimal_places=4, null=True)
    subcomponent_instance_count = models.IntegerField()

    class Meta:
        managed = False
        db_table = 'blend_subcomponent_shortage'

class GHSPictogram(models.Model):
    item_code = models.CharField(max_length=100, default=None)
    item_description = models.CharField(max_length=100, default=None)
    image_reference = models.ImageField(upload_to='core/media/GHSPictograms/', default=None)

    def __str__(self):
        return self.item_code

class HxBlendthese(models.Model):
    item_code = models.TextField(blank=True, null=True)
    po_number = models.TextField(blank=True, null=True)
    item_description = models.TextField(blank=True, null=True)
    amt = models.BigIntegerField(blank=True, null=True)
    component_item_code = models.TextField(blank=True, null=True)
    run_time = models.FloatField(blank=True, null=True)
    prod_line = models.TextField(blank=True, null=True)
    item_run_qty = models.BigIntegerField(blank=True, null=True)
    run_date = models.DateTimeField(blank=True, null=True)
    id2 = models.BigIntegerField(blank=True, null=True)
    component_item_description = models.TextField(blank=True, null=True)

    class Meta:
        managed = False
        db_table = 'hx_blendthese'

# Sage table
class ImItemCost(models.Model):
    id = models.IntegerField(primary_key=True)
    itemcode = models.TextField(blank=True, null=True)
    warehousecode = models.TextField(blank=True, null=True)
    tiertype = models.TextField(blank=True, null=True)
    groupsort = models.TextField(blank=True, null=True)
    receiptdate = models.DateField(blank=True, null=True)
    receiptno = models.TextField(blank=True, null=True)
    lotserialno = models.TextField(blank=True, null=True)
    unitcost = models.DecimalField(max_digits=50, decimal_places=5, blank=True, null=True)
    quantityonhand = models.DecimalField(max_digits=50, decimal_places=5, blank=True, null=True)
    quantitycommitted = models.DecimalField(max_digits=50, decimal_places=5, blank=True, null=True)
    allocatedcost = models.DecimalField(max_digits=50, decimal_places=5, blank=True, null=True)
    transactiondate = models.DateField(blank=True, null=True)
    negativeqty = models.TextField(blank=True, null=True)
    tiergroup = models.TextField(blank=True, null=True)
    extendedcost = models.DecimalField(max_digits=50, decimal_places=5, blank=True, null=True)
    costcalcqtycommitted = models.DecimalField(max_digits=50, decimal_places=5, blank=True, null=True)
    costcalccostcommitted = models.DecimalField(max_digits=50, decimal_places=5, blank=True, null=True)
    datecreated = models.DateField(blank=True, null=True)
    timecreated = models.TextField(blank=True, null=True)
    usercreatedkey = models.TextField(blank=True, null=True)
    dateupdated = models.DateField(blank=True, null=True)
    timeupdated = models.TextField(blank=True, null=True)
    userupdatedkey = models.TextField(blank=True, null=True)
    lotserialexpirationdate = models.DateField(blank=True, null=True)

    class Meta:
        managed = False
        db_table = 'im_itemcost'

# Sage table
class ImItemTransactionHistory(models.Model):
    id = models.IntegerField(primary_key=True)
    itemcode = models.TextField(blank=True, null=True)
    warehousecode = models.TextField(blank=True, null=True)
    transactiondate = models.DateField(blank=True, null=True)
    transactioncode = models.TextField(blank=True, null=True)
    entryno = models.TextField(blank=True, null=True)
    sequenceno = models.TextField(blank=True, null=True)
    imtransactionentrycomment = models.TextField(blank=True, null=True)
    apdivisionno = models.TextField(blank=True, null=True)
    vendorno = models.TextField(blank=True, null=True)
    ardivisionno = models.TextField(blank=True, null=True)
    customerno = models.TextField(blank=True, null=True)
    referencedate = models.DateField(blank=True, null=True)
    fiscalcalyear = models.TextField(blank=True, null=True)
    fiscalcalperiod = models.TextField(blank=True, null=True)
    shiptocode = models.TextField(blank=True, null=True)
    invoicetype = models.TextField(blank=True, null=True)
    transactionqty = models.DecimalField(max_digits=50, decimal_places=5, blank=True, null=True)
    unitcost = models.DecimalField(max_digits=50, decimal_places=5, blank=True, null=True)
    allocatedcost = models.DecimalField(max_digits=50, decimal_places=5, blank=True, null=True)
    unitprice = models.DecimalField(max_digits=50, decimal_places=5, blank=True, null=True)
    extendedprice = models.DecimalField(max_digits=50, decimal_places=5, blank=True, null=True)
    extendedcost = models.DecimalField(max_digits=50, decimal_places=5, blank=True, null=True)
    extendedstandardcost = models.DecimalField(max_digits=50, decimal_places=5, blank=True, null=True)
    dateupdated = models.DateField(blank=True, null=True)
    timeupdated = models.TextField(blank=True, null=True)
    userupdatedkey = models.TextField(blank=True, null=True)
    invoicehistoryheaderseqno = models.TextField(blank=True, null=True)
    receipthistoryheaderseqno = models.TextField(blank=True, null=True)
    receipthistorypurchaseorderno = models.TextField(blank=True, null=True)
    sourcejournal = models.TextField(blank=True, null=True)
    journalnoglbatchno = models.TextField(blank=True, null=True)
    workticketkey = models.TextField(blank=True, null=True)
    workticketno = models.TextField(blank=True, null=True)
    workticketdesc = models.TextField(blank=True, null=True)
    workticketlinekey = models.TextField(blank=True, null=True)
    workticketstepno = models.TextField(blank=True, null=True)
    workticketclasscode = models.TextField(blank=True, null=True)
    activitycode = models.TextField(blank=True, null=True)
    workcenter = models.TextField(blank=True, null=True)
    toolcode = models.TextField(blank=True, null=True)

    class Meta:
        managed = False
        db_table = 'im_itemtransactionhistory'

# Sage table
class ImItemWarehouse(models.Model):
    id = models.IntegerField(primary_key=True)
    itemcode = models.TextField(blank=True, null=True)
    warehousecode = models.TextField(blank=True, null=True)
    binlocation = models.TextField(blank=True, null=True)
    reordermethod = models.TextField(blank=True, null=True)
    quantityonhand = models.DecimalField(max_digits=50, decimal_places=5, blank=True, null=True)
    quantityonpurchaseorder = models.DecimalField(max_digits=50, decimal_places=5, blank=True, null=True)
    quantityonsalesorder = models.DecimalField(max_digits=50, decimal_places=5, blank=True, null=True)
    quantityonbackorder = models.DecimalField(max_digits=50, decimal_places=5, blank=True, null=True)
    averagecost = models.DecimalField(max_digits=50, decimal_places=5, blank=True, null=True)
    quantityrequiredforwo = models.DecimalField(max_digits=50, decimal_places=5, blank=True, null=True)
    economicorderqty = models.DecimalField(max_digits=50, decimal_places=5, blank=True, null=True)
    reorderpointqty = models.DecimalField(max_digits=50, decimal_places=5, blank=True, null=True)
    minimumorderqty = models.DecimalField(max_digits=50, decimal_places=5, blank=True, null=True)
    maximumonhandqty = models.DecimalField(max_digits=50, decimal_places=5, blank=True, null=True)
    quantityonworkorder = models.DecimalField(max_digits=50, decimal_places=5, blank=True, null=True)
    quantityinshipping = models.DecimalField(max_digits=50, decimal_places=5, blank=True, null=True)
    totalwarehousevalue = models.DecimalField(max_digits=50, decimal_places=5, blank=True, null=True)
    costcalcqtycommitted = models.DecimalField(max_digits=50, decimal_places=5, blank=True, null=True)
    costcalccostcommitted = models.DecimalField(max_digits=50, decimal_places=5, blank=True, null=True)
    datecreated = models.DateField(blank=True, null=True)
    timecreated = models.TextField(blank=True, null=True)
    usercreatedkey = models.TextField(blank=True, null=True)
    dateupdated = models.DateField(blank=True, null=True)
    timeupdated = models.TextField(blank=True, null=True)
    userupdatedkey = models.TextField(blank=True, null=True)
    lastphysicalcountdate = models.DateField(blank=True, null=True)

    class Meta:
        managed = False
        db_table = 'im_itemwarehouse'

class LotNumRecord(models.Model):
    item_code = models.TextField(blank=True, null=True)
    item_description = models.TextField(blank=True, null=True)
    lot_number = models.TextField(unique=True)
    lot_quantity = models.DecimalField(max_digits=100, decimal_places=2, null=True, blank=True)
    date_created = models.DateTimeField('date_created')
    line = models.TextField(blank=True, null=True)
    desk = models.TextField(blank=True, null=True)
    sage_entered_date = models.DateTimeField('run_date', blank=True, null=True)
    sage_qty_on_hand = models.DecimalField(max_digits=100, decimal_places=2, null=True, blank=True)
    run_date = models.DateTimeField('run_date', blank=True, null=True)
    run_day = models.TextField(blank=True, null=True)

    def __str__(self):
        return self.lot_number

def set_upload_path(instance, filename):
    return os.path.join(instance.blend_lot_number, filename)

class BlendFormulaComponent(models.Model):
    formula_reference_number = models.TextField(blank=True, null=True)
    product_name = models.TextField(blank=True, null=True)
    blend_number = models.TextField(blank=True, null=True)
    product_density = models.FloatField(blank=True, null=True)
    component_item_code = models.TextField(blank=True, null=True)
    percent_weight_of_total = models.FloatField(blank=True, null=True)
    sequence = models.FloatField(blank=True, null=True)
    blend_instructions = models.TextField(blank=True, null=True)
    date = models.DateTimeField(blank=True, null=True)

    class Meta:
        managed = False
        db_table = 'blend_formula_component'

class BlendInstruction(models.Model):
    blend_item_code = models.TextField()
    step_number = models.IntegerField()
    step_description = models.TextField()
    component_item_code = models.TextField(blank=True, null=True)

    def __str__(self):
        return self.blend_item_code
    
class BlendSheet(models.Model):
    lot_number = models.ForeignKey(LotNumRecord, on_delete=models.CASCADE)
    blend_sheet = models.JSONField()

    def __str__(self):
        return self.lot_number.lot_number

# Sage table
class PoPurchaseOrderDetail(models.Model):
    id = models.IntegerField(primary_key=True)
    purchaseorderno = models.TextField(blank=True, null=True)
    linekey = models.TextField(blank=True, null=True)
    lineseqno = models.TextField(blank=True, null=True)
    itemcode = models.TextField(blank=True, null=True)
    extendeddescriptionkey = models.TextField(blank=True, null=True)
    itemtype = models.TextField(blank=True, null=True)
    itemcodedesc = models.TextField(blank=True, null=True)
    usetax = models.TextField(blank=True, null=True)
    requireddate = models.DateField(blank=True, null=True)
    vendorpricecode = models.TextField(blank=True, null=True)
    purchasesacctkey = models.TextField(blank=True, null=True)
    valuation = models.TextField(blank=True, null=True)
    unitofmeasure = models.TextField(blank=True, null=True)
    warehousecode = models.TextField(blank=True, null=True)
    productline = models.TextField(blank=True, null=True)
    masterlinekey = models.TextField(blank=True, null=True)
    reschedule = models.TextField(blank=True, null=True)
    jobno = models.TextField(blank=True, null=True)
    costcode = models.TextField(blank=True, null=True)
    costtype = models.TextField(blank=True, null=True)
    receiptofgoodsupdated = models.TextField(blank=True, null=True)
    workorderno = models.TextField(blank=True, null=True)
    stepno = models.TextField(blank=True, null=True)
    substepprefix = models.TextField(blank=True, null=True)
    substepsuffix = models.TextField(blank=True, null=True)
    workordertype = models.TextField(blank=True, null=True)
    allocatelandedcost = models.TextField(blank=True, null=True)
    vendoraliasitemno = models.TextField(blank=True, null=True)
    taxclass = models.TextField(blank=True, null=True)
    commenttext = models.TextField(blank=True, null=True)
    assetaccount = models.TextField(blank=True, null=True)
    assettemplate = models.TextField(blank=True, null=True)
    weightreference = models.TextField(blank=True, null=True)
    weight = models.DecimalField(max_digits=50, decimal_places=5, blank=True, null=True)
    quantityordered = models.DecimalField(max_digits=50, decimal_places=5, blank=True, null=True)
    quantityreceived = models.DecimalField(max_digits=50, decimal_places=5, blank=True, null=True)
    quantitybackordered = models.DecimalField(max_digits=50, decimal_places=5, blank=True, null=True)
    masteroriginalqty = models.DecimalField(max_digits=50, decimal_places=5, blank=True, null=True)
    masterqtybalance = models.DecimalField(max_digits=50, decimal_places=5, blank=True, null=True)
    masterqtyorderedtodate = models.DecimalField(max_digits=50, decimal_places=5, blank=True, null=True)
    quantityinvoiced = models.DecimalField(max_digits=50, decimal_places=5, blank=True, null=True)
    unitcost = models.DecimalField(max_digits=50, decimal_places=5, blank=True, null=True)
    originalunitcost = models.DecimalField(max_digits=50, decimal_places=5, blank=True, null=True)
    extensionamt = models.DecimalField(max_digits=50, decimal_places=5, blank=True, null=True)
    receivedamt = models.DecimalField(max_digits=50, decimal_places=5, blank=True, null=True)
    invoicedamt = models.DecimalField(max_digits=50, decimal_places=5, blank=True, null=True)
    unitofmeasureconvfactor = models.DecimalField(max_digits=50, decimal_places=5, blank=True, null=True)
    receivedallocatedamt = models.DecimalField(max_digits=50, decimal_places=5, blank=True, null=True)
    invoicedallocatedamt = models.DecimalField(max_digits=50, decimal_places=5, blank=True, null=True)
    salesorderno = models.TextField(blank=True, null=True)
    customerpono = models.TextField(blank=True, null=True)
    purchaseorderhistorydtlseqno = models.TextField(blank=True, null=True)
    workticketkey = models.TextField(blank=True, null=True)
    workticketsteplinekey = models.TextField(blank=True, null=True)
    workticketlinekey = models.TextField(blank=True, null=True)
    workticketstatus = models.TextField(blank=True, null=True)

    class Meta:
        managed = False
        db_table = 'po_purchaseorderdetail'

class PoPurchaseOrderHeader(models.Model):
    purchaseorderno = models.TextField(blank=True, null=True)
    purchaseorderdate = models.DateField(blank=True, null=True)
    ordertype = models.TextField(blank=True, null=True)
    masterrepeatingorderno = models.TextField(blank=True, null=True)
    requiredexpiredate = models.DateField(blank=True, null=True)
    apdivisionno = models.TextField(blank=True, null=True)
    vendorno = models.TextField(blank=True, null=True)
    purchasename = models.TextField(blank=True, null=True)
    purchaseaddress1 = models.TextField(blank=True, null=True)
    purchaseaddress2 = models.TextField(blank=True, null=True)
    purchaseaddress3 = models.TextField(blank=True, null=True)
    purchasecity = models.TextField(blank=True, null=True)
    purchasestate = models.TextField(blank=True, null=True)
    purchasezipcode = models.TextField(blank=True, null=True)
    purchasecountrycode = models.TextField(blank=True, null=True)
    purchaseaddresscode = models.TextField(blank=True, null=True)
    shiptocode = models.TextField(blank=True, null=True)
    shiptoname = models.TextField(blank=True, null=True)
    shiptoaddress1 = models.TextField(blank=True, null=True)
    shiptoaddress2 = models.TextField(blank=True, null=True)
    shiptoaddress3 = models.TextField(blank=True, null=True)
    shiptocity = models.TextField(blank=True, null=True)
    shiptostate = models.TextField(blank=True, null=True)
    shiptozipcode = models.TextField(blank=True, null=True)
    shiptocountrycode = models.TextField(blank=True, null=True)
    orderstatus = models.TextField(blank=True, null=True)
    usetax = models.TextField(blank=True, null=True)
    printpurchaseorders = models.TextField(blank=True, null=True)
    onhold = models.TextField(blank=True, null=True)
    batchfax = models.TextField(blank=True, null=True)
    completiondate = models.DateField(blank=True, null=True)
    shipvia = models.TextField(blank=True, null=True)
    fob = models.TextField(blank=True, null=True)
    warehousecode = models.TextField(blank=True, null=True)
    confirmto = models.TextField(blank=True, null=True)
    comment = models.TextField(blank=True, null=True)
    ardivisionno = models.TextField(blank=True, null=True)
    customerno = models.TextField(blank=True, null=True)
    termscode = models.TextField(blank=True, null=True)
    lastinvoicedate = models.DateField(blank=True, null=True)
    lastinvoiceno = models.TextField(blank=True, null=True)
    form1099 = models.TextField(blank=True, null=True)
    box1099 = models.TextField(blank=True, null=True)
    lastreceiptdate = models.DateField(blank=True, null=True)
    lastissuedate = models.DateField(blank=True, null=True)
    lastreceiptno = models.TextField(blank=True, null=True)
    lastissueno = models.TextField(blank=True, null=True)
    prepaidcheckno = models.TextField(blank=True, null=True)
    faxno = models.TextField(blank=True, null=True)
    taxschedule = models.TextField(blank=True, null=True)
    invalidtaxcalc = models.TextField(blank=True, null=True)
    prepaidamt = models.DecimalField(max_digits=65535, decimal_places=65535, blank=True, null=True)
    taxableamt = models.DecimalField(max_digits=65535, decimal_places=65535, blank=True, null=True)
    nontaxableamt = models.DecimalField(max_digits=65535, decimal_places=65535, blank=True, null=True)
    salestaxamt = models.DecimalField(max_digits=65535, decimal_places=65535, blank=True, null=True)
    freightamt = models.DecimalField(max_digits=65535, decimal_places=65535, blank=True, null=True)
    prepaidfreightamt = models.DecimalField(max_digits=65535, decimal_places=65535, blank=True, null=True)
    invoicedamt = models.DecimalField(max_digits=65535, decimal_places=65535, blank=True, null=True)
    receivedamt = models.DecimalField(max_digits=65535, decimal_places=65535, blank=True, null=True)
    freightsalestaxinvamt = models.DecimalField(max_digits=65535, decimal_places=65535, blank=True, null=True)
    backorderlostamt = models.DecimalField(max_digits=65535, decimal_places=65535, blank=True, null=True)
    datecreated = models.DateField(blank=True, null=True)
    timecreated = models.TextField(blank=True, null=True)
    usercreatedkey = models.TextField(blank=True, null=True)
    dateupdated = models.DateField(blank=True, null=True)
    timeupdated = models.TextField(blank=True, null=True)
    userupdatedkey = models.TextField(blank=True, null=True)
    batchemail = models.TextField(blank=True, null=True)
    emailaddress = models.TextField(blank=True, null=True)
    lastpurchaseorderdate = models.DateField(blank=True, null=True)
    lastpurchaseorderno = models.TextField(blank=True, null=True)
    salesorderno = models.TextField(blank=True, null=True)
    requisitorname = models.TextField(blank=True, null=True)
    requisitordepartment = models.TextField(blank=True, null=True)

    class Meta:
        managed = False
        db_table = 'po_purchaseorderheader'

class ProductionLineRun(models.Model):
    item_code = models.TextField(blank=True, null=True)
    po_number = models.TextField(blank=True, null=True)
    item_run_qty = models.DecimalField(max_digits=10, decimal_places=1, blank=True, null=True)
    run_time = models.DecimalField(max_digits=12, decimal_places=8, blank=True, null=True)
    id2 = models.DecimalField(max_digits=12, decimal_places=1, blank=True, null=True)
    start_time = models.DecimalField(max_digits=12, decimal_places=8, blank=True, null=True)
    prod_line = models.TextField(blank=True, null=True)
    item_description = models.TextField(blank=True, null=True)

    class Meta:
        managed = False
        db_table = 'prodmerge_run_data'

class SpecsheetData(models.Model):
    itemcode = models.TextField(db_column='ItemCode', blank=True, null=True)  # Field name made lowercase.
    componentitemcode = models.TextField(db_column='ComponentItemCode', blank=True, null=True)  # Field name made lowercase.
    item_description = models.TextField(db_column='Item Description', blank=True, null=True)  # Field name made lowercase. Field renamed to remove unsuitable characters.
    appearance = models.TextField(db_column='Appearance', blank=True, null=True)  # Field name made lowercase.
    spec_gravity_weight_per_gallon_20c = models.TextField(db_column='Spec. Gravity/Weight Per gallon 20C', blank=True, null=True)  # Field name made lowercase. Field renamed to remove unsuitable characters.
    comments_cont_field = models.TextField(db_column='Comments cont.', blank=True, null=True)  # Field name made lowercase. Field renamed to remove unsuitable characters. Field renamed because it ended with '_'.
    ph = models.TextField(db_column='pH', blank=True, null=True)  # Field name made lowercase.
    viscosity = models.TextField(db_column='Viscosity', blank=True, null=True)  # Field name made lowercase.
    api_gravity = models.TextField(db_column='API Gravity', blank=True, null=True)  # Field name made lowercase. Field renamed to remove unsuitable characters.
    miscellaneous = models.TextField(db_column='Miscellaneous', blank=True, null=True)  # Field name made lowercase.
    freeze_point = models.TextField(db_column='Freeze Point', blank=True, null=True)  # Field name made lowercase. Field renamed to remove unsuitable characters.
    field_water = models.TextField(db_column='% Water', blank=True, null=True)  # Field name made lowercase. Field renamed to remove unsuitable characters. Field renamed because it started with '_'.
    ir_scan_needed = models.TextField(db_column='IR Scan Needed', blank=True, null=True)  # Field name made lowercase. Field renamed to remove unsuitable characters.
    other_misc_testing = models.TextField(db_column='Other Misc. Testing', blank=True, null=True)  # Field name made lowercase. Field renamed to remove unsuitable characters.
    oil_blends = models.TextField(db_column='Oil Blends', blank=True, null=True)  # Field name made lowercase. Field renamed to remove unsuitable characters.
    comments = models.TextField(db_column='Comments', blank=True, null=True)  # Field name made lowercase.
    water_flush = models.TextField(db_column='Water Flush', blank=True, null=True)  # Field name made lowercase. Field renamed to remove unsuitable characters.
    solvent_flush = models.TextField(db_column='Solvent Flush', blank=True, null=True)  # Field name made lowercase. Field renamed to remove unsuitable characters.
    product_class = models.TextField(db_column='Product Class', blank=True, null=True)  # Field name made lowercase. Field renamed to remove unsuitable characters.
    soap_flush = models.TextField(db_column='Soap Flush', blank=True, null=True)  # Field name made lowercase. Field renamed to remove unsuitable characters.
    oil_flush = models.TextField(db_column='Oil Flush', blank=True, null=True)  # Field name made lowercase. Field renamed to remove unsuitable characters.
    polish_flush = models.TextField(db_column='Polish Flush', blank=True, null=True)  # Field name made lowercase. Field renamed to remove unsuitable characters.
    package_retain = models.TextField(db_column='Package Retain', blank=True, null=True)  # Field name made lowercase. Field renamed to remove unsuitable characters.
    blendnotes = models.TextField(db_column='BlendNotes', blank=True, null=True)  # Field name made lowercase.
    uv_protection = models.TextField(db_column='UV  Protection', blank=True, null=True)  # Field name made lowercase. Field renamed to remove unsuitable characters.
    freeze_protection = models.TextField(db_column='Freeze Protection', blank=True, null=True)  # Field name made lowercase. Field renamed to remove unsuitable characters.
    min_weight_n_field = models.TextField(db_column='Min Weight (N)', blank=True, null=True)  # Field name made lowercase. Field renamed to remove unsuitable characters. Field renamed because it ended with '_'.
    target_weight_n_field = models.TextField(db_column='TARGET WEIGHT (N)', blank=True, null=True)  # Field name made lowercase. Field renamed to remove unsuitable characters. Field renamed because it ended with '_'.
    max_weight_n_field = models.TextField(db_column='Max Weight (N)', blank=True, null=True)  # Field name made lowercase. Field renamed to remove unsuitable characters. Field renamed because it ended with '_'.
    new_upc = models.TextField(db_column='New UPC', blank=True, null=True)  # Field name made lowercase. Field renamed to remove unsuitable characters.
    scc = models.TextField(db_column='SCC', blank=True, null=True)  # Field name made lowercase.
    us_dot = models.TextField(db_column='US - DOT', blank=True, null=True)  # Field name made lowercase. Field renamed to remove unsuitable characters.
    special_notes = models.TextField(db_column='Special Notes', blank=True, null=True)  # Field name made lowercase. Field renamed to remove unsuitable characters.
    europe_haz = models.TextField(db_column='Europe HAZ', blank=True, null=True)  # Field name made lowercase. Field renamed to remove unsuitable characters.
    haz_symbols = models.TextField(db_column='Haz Symbols', blank=True, null=True)  # Field name made lowercase. Field renamed to remove unsuitable characters.
    current_footprint = models.TextField(db_column='Current Footprint', blank=True, null=True)  # Field name made lowercase. Field renamed to remove unsuitable characters.
    notes = models.TextField(db_column='Notes', blank=True, null=True)  # Field name made lowercase.

    class Meta:
        managed = False
        db_table = 'specsheet_data'

class TimetableRunData(models.Model):
    id = models.IntegerField(primary_key=True)
    id2 = models.DecimalField(max_digits=4, decimal_places=1, blank=True, null=True)
    item_code = models.TextField(blank=True, null=True)
    component_item_code = models.TextField(blank=True, null=True)
    component_item_description = models.TextField(blank=True, null=True)
    adjustedrunqty = models.DecimalField(max_digits=10, decimal_places=5, blank=True, null=True)
    qtyonhand = models.DecimalField(max_digits=10, decimal_places=5, blank=True, null=True)
    starttime = models.DecimalField(max_digits=10, decimal_places=5, blank=True, null=True)
    prodline = models.TextField(blank=True, null=True)
    oh_after_run = models.DecimalField(max_digits=10, decimal_places=5, blank=True, null=True)
    week_calc = models.DecimalField(max_digits=10, decimal_places=5, blank=True, null=True)
    procurementtype = models.TextField(blank=True, null=True)

    class Meta:
        managed = False
        db_table = 'timetable_run_data'

class UpcomingBlendCount(models.Model):
    id = models.AutoField(primary_key=True)
    item_code = models.TextField(blank=True, null=True)
    item_description = models.TextField(blank=True, null=True)
    expected_quantity = models.DecimalField(max_digits=10, decimal_places=5, blank=True, null=True)
    start_time = models.DecimalField(max_digits=10, decimal_places=5, blank=True, null=True)
    prod_line = models.TextField(blank=True, null=True)
    last_transaction_code = models.TextField(blank=True, null=True)
    last_transaction_date = models.DateField(blank=True, null=True)
    last_transaction_quantity = models.DecimalField(max_digits=10, decimal_places=5, blank=True, null=True)
    last_count_quantity = models.DecimalField(max_digits=10, decimal_places=5, blank=True, null=True)
    last_count_date = models.DateField(blank=True, null=True)
    procurement_type = models.TextField(blank=True, null=True)

    class Meta:
        managed = False
        db_table = 'upcoming_blend_count'

class UpcomingComponentCount(models.Model):
    id = models.AutoField(primary_key=True)
    item_code = models.TextField(blank=True, null=True)
    item_description = models.TextField(blank=True, null=True)
    expected_quantity = models.DecimalField(max_digits=10, decimal_places=5, blank=True, null=True)
    last_transaction_code = models.TextField(blank=True, null=True)
    last_transaction_date = models.DateField(blank=True, null=True)
    last_transaction_quantity = models.DecimalField(max_digits=10, decimal_places=5, blank=True, null=True)
    last_count_quantity = models.DecimalField(max_digits=10, decimal_places=5, blank=True, null=True)
    last_count_date = models.DateField(blank=True, null=True)

    class Meta:
        managed = False
        db_table = 'upcoming_component_count'

class DeskOneSchedule(models.Model):
    order = models.IntegerField(blank=False)
    item_code = models.TextField(blank=False)
    item_description = models.TextField(blank=False)
    lot = models.TextField(blank=False) #models.ForeignKey(LotNumRecord, on_delete=models.CASCADE)
    blend_area = models.TextField(blank=False)
    tank = models.TextField(blank=True, null=True)

    def __str__(self):
        return self.lot

class DeskTwoSchedule(models.Model):
    order = models.IntegerField(blank=False)
    item_code = models.TextField(blank=False)
    item_description = models.TextField(blank=False)
    lot = models.TextField(blank=False) #models.ForeignKey(LotNumRecord, on_delete=models.CASCADE)
    blend_area = models.TextField(blank=False)
    tank = models.TextField(blank=True, null=True)

    def __str__(self):
        return self.lot

class LetDeskSchedule(models.Model):
    order = models.IntegerField(blank=False)
    item_code = models.CharField(max_length=20)
    item_description = models.CharField(max_length=100)
    lot = models.CharField(max_length=20)
    blend_area = models.CharField(max_length=20, default='LET_Desk')
    tank = models.CharField(max_length=50, null=True, blank=True)
    
    def __str__(self):
        return self.lot

class StorageTank(models.Model):
    tank_label_kpk = models.TextField(blank=False)
    tank_label_vega = models.TextField(blank=False)
    distance_A = models.DecimalField(max_digits=50, decimal_places=5, blank=False)
    distance_B = models.DecimalField(max_digits=50, decimal_places=5, blank=False)
    max_gallons = models.DecimalField(max_digits=50, decimal_places=5, blank=False)
    max_inches = models.DecimalField(max_digits=50, decimal_places=5, blank=False)
    gallons_per_inch = models.DecimalField(max_digits=50, decimal_places=5, blank=False)
    item_code = models.TextField(blank=False)
    item_description = models.TextField(blank=False)

    def __str__(self):
        return self.tank_label_kpk

class TankLevel(models.Model):
    tank_name = models.TextField(blank=False)
    fill_percentage = models.DecimalField(max_digits=50, decimal_places=2, blank=True)
    fill_height_inches = models.DecimalField(max_digits=50, decimal_places=2, blank=True)
    height_capacity_inches = models.DecimalField(max_digits=50, decimal_places=2, blank=True)
    filled_gallons = models.DecimalField(max_digits=50, decimal_places=2, blank=True)

    class Meta:
        managed = False
        db_table = 'tank_level'
    
class TankLevelLog(models.Model):
    timestamp = models.DateTimeField()
    tank_name = models.TextField(blank=False)
    fill_percentage = models.DecimalField(max_digits=50, decimal_places=2, blank=True)
    fill_height_inches = models.DecimalField(max_digits=50, decimal_places=2, blank=True)
    height_capacity_inches = models.DecimalField(max_digits=50, decimal_places=2, blank=True)
    filled_gallons = models.DecimalField(max_digits=50, decimal_places=2, blank=True)

    def __str__(self):
        return self.timestamp

class WeeklyBlendTotals(models.Model):
    id = models.AutoField(primary_key=True)
    week_starting = models.DateField(blank=True, null=True)
    blend_quantity = models.DecimalField(max_digits=50, decimal_places=5, blank=False)

    class Meta:
        managed = False
        db_table = 'weekly_blend_totals'

class LoopStatus(models.Model):
    id = models.AutoField(primary_key=True)
    function_name = models.TextField(blank=False)
    function_result = models.TextField(blank=False)
    time_stamp = models.DateTimeField()

    def __str__(self):
        return self.function_name
