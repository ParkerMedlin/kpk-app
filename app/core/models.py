from pickle import TRUE
from xml.etree.ElementTree import TreeBuilder
from django.db import models
from django.utils import timezone
import os
from ordered_model.models import OrderedModel


class BillOfMaterials(models.Model):
    id = models.IntegerField(primary_key=True)
    item_code = models.TextField(blank=True, null=True)
    component_item_code = models.TextField(blank=True, null=True)
    component_item_description = models.TextField(blank=True, null=True)
    item_description = models.TextField(blank=True, null=True)
    procurementtype = models.TextField(blank=True, null=True)
    foam_factor = models.DecimalField(max_digits=100, decimal_places=2, blank=True, null=True)
    standard_uom = models.TextField(blank=True, null=True)
    qtyperbill = models.DecimalField(max_digits=10, decimal_places=5, blank=True, null=True)
    weightpergal = models.TextField(blank=True, null=True)
    qtyonhand = models.DecimalField(max_digits=10, decimal_places=5, blank=True, null=True)

    class Meta:
        managed = False
        db_table = 'bill_of_materials'

class BlendInstruction(models.Model):
    step_no = models.IntegerField(blank=True, null=True)
    step_desc = models.TextField(blank=True, null=True)
    step_qty = models.TextField(blank=True, null=True)
    step_unit = models.TextField(blank=True, null=True)
    component_item_code = models.TextField(blank=True, null=True)
    notes_1 = models.TextField(blank=True, null=True)
    notes_2 = models.TextField(blank=True, null=True)
    item_code = models.TextField(blank=True, null=True)
    ref_no = models.TextField(blank=True, null=True)
    prepared_by = models.TextField(blank=True, null=True)
    prepared_date = models.TextField(blank=True, null=True)
    lbs_per_gal = models.TextField(blank=True, null=True)

    def __str__(self):
        return self.item_code

class BlendThese(models.Model):
    id = models.IntegerField(primary_key=True)
    item_code = models.TextField(blank=True, null=True)
    component_item_code = models.TextField(blank=True, null=True)
    component_item_description = models.TextField(blank=True, null=True)
    adjustedrunqty = models.DecimalField(max_digits=100, decimal_places=2, null=True)
    qtyonhand = models.DecimalField(max_digits=100, decimal_places=2, null=True)
    starttime = models.DecimalField(max_digits=100, decimal_places=2, null=True)
    prodline = models.TextField(blank=True, null=True)
    oh_after_run = models.DecimalField(max_digits=100, decimal_places=2, null=True)
    week_calc = models.IntegerField()
    one_wk_short = models.DecimalField(max_digits=100, decimal_places=2, null=True)
    two_wk_short = models.DecimalField(max_digits=100, decimal_places=2, null=True)
    three_wk_short = models.DecimalField(max_digits=100, decimal_places=2, null=True)
    last_count_quantity = models.DecimalField(max_digits=100, decimal_places=2, null=True)
    last_count_date = models.DateField(blank=True, null=True)
    last_txn_code = models.TextField(blank=True, null=True)
    last_txn_date = models.DateField(blank=True, null=True)
    procurementtype = models.TextField(blank=True, null=True)


    class Meta:
        managed = False
        db_table = 'blendthese'

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

class ChemLocation(models.Model):
    id = models.IntegerField(primary_key=True)
    component_item_code = models.TextField(blank=True, null=True)
    component_item_description = models.TextField(blank=True, null=True)
    unit = models.TextField(blank=True, null=True)
    storagetype = models.TextField(blank=True, null=True)
    general_location = models.TextField(blank=True, null=True)
    specific_location = models.TextField(blank=True, null=True)

    def __str__(self):
        return self.component_item_code


class CountRecord(models.Model):
    item_code = models.TextField(blank=True, null=True)
    item_description = models.TextField(blank=True, null=True)
    expected_quantity = models.DecimalField(max_digits=50, decimal_places=5, blank=True, null=True)
    counted_quantity = models.DecimalField(max_digits=50, decimal_places=5, blank=True, null=True)
    counted_date = models.DateField(blank=True, null=True)
    variance = models.DecimalField(max_digits=50, decimal_places=5, blank=True, null=True)

    def __str__(self):
        return self.item_code + "; " + str(self.counted_date)

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

class FoamFactor(models.Model):
    blend = models.TextField(blank=True, null=True)
    factor = models.DecimalField(max_digits=100, decimal_places=2, null=True)
    blenddesc = models.TextField(blank=True, null=True)

    def __str__(self):
        return self.blend

class HorixBlendThese(models.Model):
    pn = models.TextField(blank=True, null=True)
    po_field = models.TextField(db_column='po_', blank=True, null=True)  # Field renamed because it ended with '_'.
    product = models.TextField(blank=True, null=True)
    amt = models.TextField(blank=True, null=True)
    blend = models.TextField(blank=True, null=True)
    dye = models.TextField(blank=True, null=True)
    case_size = models.TextField(blank=True, null=True)
    case_qty = models.TextField(blank=True, null=True)
    run_date = models.TextField(blank=True, null=True)
    id = models.TextField(primary_key=True)
    gal_factor = models.TextField(blank=True, null=True)
    line = models.TextField(blank=True, null=True)
    gallonqty = models.TextField(blank=True, null=True)
    num_blends = models.IntegerField(blank=True, null=True)

    class Meta:
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
    batchnum7 = models.TextField(blank=True, null=True)
    batchqty7 = models.TextField(blank=True, null=True)
    batchnum8 = models.TextField(blank=True, null=True)
    batchqty8 = models.TextField(blank=True, null=True)
    batchnum9 = models.TextField(blank=True, null=True)
    batchqty9 = models.TextField(blank=True, null=True)
    uniqchek = models.TextField(blank=True, null=True)

    class Meta:
        managed = False
        db_table = 'issue_sheet_needed'

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

class BlendingStep(models.Model):
    step_no = models.IntegerField(blank=True, null=True)
    step_desc = models.TextField(blank=True, null=True)
    step_qty = models.TextField(blank=True, null=True)
    step_unit = models.TextField(blank=True, null=True)
    qty_added = models.TextField(blank=True, null=True)
    component_item_code = models.TextField(blank=True, null=True)
    chem_lot_number = models.TextField(blank=True, null=True)
    notes_1 = models.TextField(blank=True, null=True)
    notes_2 = models.TextField(blank=True, null=True)
    start_time = models.TimeField(blank=True, null=True)
    end_time = models.TimeField(blank=True, null=True)
    chkd_by = models.TextField(blank=True, null=True)
    mfg_chkd_by = models.TextField(blank=True, null=True)
    item_code = models.TextField(blank=True, null=True)
    component_item_description = models.TextField(blank=True, null=True)
    ref_no = models.TextField(blank=True, null=True)
    prepared_by = models.TextField(blank=True, null=True)
    prepared_date = models.TextField(blank=True, null=True)
    lbs_per_gal = models.TextField(blank=True, null=True)
    blend_lot_number = models.TextField(blank=True, null=True)
    lot = models.TextField(blank=True, null=True) #models.ForeignKey(LotNumRecord, on_delete=models.CASCADE)
    picture_attachment = models.ImageField(upload_to=set_upload_path, blank=True)

    def __str__(self):
        return self.blend_lot_number

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
    itemcode = models.TextField(blank=True, null=True)
    itemdesc = models.TextField(blank=True, null=True)
    expected_on_hand = models.DecimalField(max_digits=10, decimal_places=5, blank=True, null=True)
    starttime = models.DecimalField(max_digits=10, decimal_places=5, blank=True, null=True)
    prodline = models.TextField(blank=True, null=True)
    last_transaction_code = models.TextField(blank=True, null=True)
    last_transaction_date = models.DateField(blank=True, null=True)
    last_count_quantity = models.DecimalField(max_digits=10, decimal_places=5, blank=True, null=True)
    last_count_date = models.DateField(blank=True, null=True)
    procurementtype = models.TextField(blank=True, null=True)

    class Meta:
        managed = False
        db_table = 'upcoming_blend_count'

class DeskOneSchedule(OrderedModel):
    component_item_code = models.TextField(blank=False)
    component_item_description = models.TextField(blank=False)
    lot = models.TextField(blank=False) #models.ForeignKey(LotNumRecord, on_delete=models.CASCADE)
    quantity = models.DecimalField(max_digits=50, decimal_places=5, blank=False)
    totes_needed = models.DecimalField(max_digits=50, decimal_places=5, blank=False)
    blend_area = models.TextField(blank=False)

    def __str__(self):
        return self.lot

class DeskTwoSchedule(OrderedModel):
    component_item_code = models.TextField(blank=False)
    component_item_description = models.TextField(blank=False)
    lot = models.TextField(blank=False) #models.ForeignKey(LotNumRecord, on_delete=models.CASCADE)
    quantity = models.DecimalField(max_digits=50, decimal_places=5, blank=False)
    totes_needed = models.DecimalField(max_digits=50, decimal_places=5, blank=False)
    blend_area = models.TextField(blank=False)

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

class WeeklyBlendTotals(models.Model):
    id = models.AutoField(primary_key=True)
    week_starting = models.DateField(blank=True, null=True)
    blend_quantity = models.DecimalField(max_digits=50, decimal_places=5, blank=False)

    class Meta:
        managed = False
        db_table = 'weekly_blend_totals'