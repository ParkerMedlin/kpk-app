from pickle import TRUE
from xml.etree.ElementTree import TreeBuilder
from django.db import models
from django import forms
from django.utils import timezone


class Sample(models.Model):
    attachment = models.FileField()

FORKLIFT_CHOICES = [
    ('17', '17'),
    ('6', '6'),
]

class checklistlog(models.Model):
    date = models.DateTimeField('Date')
    operator_name = models.CharField(max_length=100, null=True)
    unit_number = models.CharField(max_length=3, choices=FORKLIFT_CHOICES)
    serial_number = models.CharField(max_length=100)
    engine_oil_checked = models.BooleanField()
    engine_oil_comments = models.TextField(blank=True)
    propane_tank_checked = models.BooleanField()
    propane_tank_comments = models.TextField(blank=True)
    radiator_leaks_checked = models.BooleanField()
    radiator_leaks_comments = models.TextField(blank=True)
    tires_checked = models.BooleanField()
    tires_comments = models.TextField(blank=True)
    mast_forks_checked = models.BooleanField()
    mast_forks_comments = models.TextField(blank=True)
    leaks_checked = models.BooleanField()
    leaks_comments = models.TextField(blank=True)
    horn_checked = models.BooleanField()
    horn_comments = models.TextField(blank=True)
    driver_compartment_checked = models.BooleanField()
    driver_compartment_comments = models.TextField(blank=True)
    seatbelt_checked = models.BooleanField()
    seatbelt_comments = models.TextField(blank=True)
    battery_checked = models.BooleanField()
    battery_comments = models.TextField(blank=True)
    safety_equipment_checked = models.BooleanField()
    safety_equipment_comments = models.TextField(blank=True)
    steering_checked = models.BooleanField()
    steering_comments = models.TextField(blank=True)
    brakes_checked = models.BooleanField()
    brakes_comments = models.TextField(blank=True)

    def __str__(self):
        return self.operator_name

class safetyChecklistForm(forms.ModelForm):
    class Meta:
        model = checklistlog
        fields = ('date',
                    'operator_name',
                    'unit_number',
                    'serial_number',
                    'engine_oil_checked',
                    'engine_oil_comments',
                    'propane_tank_checked',
                    'propane_tank_comments',
                    'radiator_leaks_checked',
                    'radiator_leaks_comments',
                    'tires_checked',
                    'tires_comments',
                    'mast_forks_checked',
                    'mast_forks_comments',
                    'leaks_checked',
                    'leaks_comments',
                    'horn_checked',
                    'horn_comments',
                    'driver_compartment_checked',
                    'driver_compartment_comments',
                    'seatbelt_checked',
                    'seatbelt_comments',
                    'battery_checked',
                    'battery_comments',
                    'safety_equipment_checked',
                    'safety_equipment_comments',
                    'steering_checked',
                    'steering_comments',
                    'brakes_checked',
                    'brakes_comments'
                    )
        widgets = {
            'date': forms.HiddenInput(),
            'operator_name': forms.HiddenInput(),
            'engine_oil_comments': forms.TextInput(),
            'propane_tank_comments': forms.TextInput(),
            'radiator_leaks_comments': forms.TextInput(),
            'tires_comments': forms.TextInput(),
            'mast_forks_comments': forms.TextInput(),
            'leaks_comments': forms.TextInput(),
            'horn_comments': forms.TextInput(),
            'driver_compartment_comments': forms.TextInput(),
            'seatbelt_comments': forms.TextInput(),
            'battery_comments': forms.TextInput(),
            'safety_equipment_comments': forms.TextInput(),
            'steering_comments': forms.TextInput(),
            'brakes_comments': forms.TextInput(),
        }

class blendthese(models.Model):
    blend = models.TextField(blank=True, null=True)
    blend_description = models.TextField(blank=True, null=True)
    starttime = models.TextField(blank=True, null=True)
    line = models.TextField(blank=True, null=True)
    oh_now = models.DecimalField(max_digits=100, decimal_places=2, null=True)
    oh_during_run = models.DecimalField(max_digits=100, decimal_places=2, null=True)
    qty_required = models.DecimalField(max_digits=100, decimal_places=2, null=True)
    oh_after_run = models.DecimalField(max_digits=100, decimal_places=2, null=True)
    one_week_short = models.DecimalField(max_digits=100, decimal_places=2, null=True)
    two_week_short = models.DecimalField(max_digits=100, decimal_places=2, null=True)
    three_week_short = models.DecimalField(max_digits=100, decimal_places=2, null=True)

    class Meta:
        managed = False
        db_table = 'blendthese'

class lotnumrecord(models.Model):
    part_number = models.TextField(blank=True, null=True)
    description = models.TextField(blank=True, null=True)
    lot_number = models.TextField(primary_key=True, blank=True)
    quantity = models.DecimalField(max_digits=100, decimal_places=2, null=True, blank=True)
    date = models.DateTimeField('Date')

    def __str__(self):
        return self.lot_number

#lotnumform.html
class lotnumrecordForm(forms.ModelForm):
    class Meta:
        model = lotnumrecord
        fields = ('part_number', 'description', 'lot_number', 'quantity', 'date')
        widgets = {
            'part_number': forms.TextInput(),
            'description': forms.TextInput(),
            'lot_number': forms.TextInput(),
            'quantity': forms.NumberInput(),
            'date': forms.DateInput(),
        }
        labels = {
            'part_number': 'Blend Part Number:'
        }



class blendInstruction(models.Model):
    bill_no = models.TextField(blank=True, null=True)
    status = models.TextField(blank=True, null=True)
    step_no = models.IntegerField(blank=True, null=True)
    step_desc = models.TextField(blank=True, null=True)
    component_code = models.TextField(blank=True, null=True)
    component_desc = models.TextField(blank=True, null=True)

    class Meta:
        managed = False
        db_table = 'blendinstructions'



##### **** ################# **** #####
#### *    * ############### *    * ####
### *        ############# *        ###
##    ****    SAGE TABLES    ****    ##
###        * #############        * ###
#### *    * ############### *    * ####
##### **** ################# **** #####
class PoPurchaseorderdetail(models.Model):
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


class ImItemwarehouse(models.Model):
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


class ImItemtransactionhistory(models.Model):
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


class ImItemcost(models.Model):
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


class CiItem(models.Model):
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


class BmBillheader(models.Model):
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


class BmBilldetail(models.Model):
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