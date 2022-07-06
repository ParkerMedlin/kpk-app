import json
from core.models import BlendInstruction,LotNumRecord
from django.core.management import BaseCommand


class Command(BaseCommand):
    help = 'Load a lotnumbers csv file into the database'

    def handle(self, *args, **kwargs):
        BlendInstructionDB = BlendInstruction.objects.order_by('blend_part_num', 'step_no')
        allLots = LotNumRecord.objects.all()
        for lot in allLots:
            ourBlendSteps = BlendInstructionDB.filter(blend_part_num__icontains=lot.part_number)
            numSteps = ourBlendSteps.count()
            emptyStringList = [''] # generate a list with as many empty strings as there are steps in the procedure
            for count in range(numSteps-1): 
                emptyStringList.append('')
            stepQtyFactorList = list(ourBlendSteps.all().values_list('step_qty', flat=True))
            stepQtyList = ['']
            for count in range(numSteps-1): 
                stepQtyList.append('')
            funIterator = 0
            for stepQtyFactor in stepQtyFactorList: 
                if stepQtyFactorList[funIterator] != "":
                    stepQtyList[funIterator] = float(lot.quantity) * float(stepQtyFactor)
                funIterator+=1
            thisLotDict = {
                'step_no' : list(ourBlendSteps.all().values_list('step_no', flat=True)),
                'step_desc' : list(ourBlendSteps.all().values_list('step_desc', flat=True)),
                'step_qty' : stepQtyList,
                'step_unit' : list(ourBlendSteps.all().values_list('step_unit', flat=True)),
                'component_item_code' : list(ourBlendSteps.all().values_list('component_item_code', flat=True)),
                'chem_lot_no' : emptyStringList,
                'qty_added' : emptyStringList,
                'start_time' : emptyStringList,
                'end_time' : emptyStringList,
                'chkd_by' : emptyStringList,
                'mfg_chkd_by' : emptyStringList,
            }
            thisLotStepsJSON = json.dumps(thisLotDict)
            LotNumRecord.objects.filter(lot_number=lot.lot_number).update(steps=thisLotStepsJSON)