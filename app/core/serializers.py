from rest_framework import serializers
from core.models import *
from prodverse.models import *

class WarehouseCountRecordSerializer(serializers.ModelSerializer):
    class Meta:
        model = WarehouseCountRecord 
        fields = '__all__'

class SpecSheetDataSerializer(serializers.ModelSerializer):
    class Meta:
        model = SpecSheetData 
        fields = '__all__'

class SpecSheetLabelsSerializer(serializers.ModelSerializer):
    class Meta:
        model = SpecSheetLabels 
        fields = '__all__'

class SpecsheetStateSerializer(serializers.ModelSerializer):
    class Meta:
        model = SpecsheetState 
        fields = '__all__'

class CountRecordSubmissionLogSerializer(serializers.ModelSerializer):
    class Meta:
        model = CountRecordSubmissionLog 
        fields = '__all__'

class CountCollectionLinkSerializer(serializers.ModelSerializer):
    class Meta:
        model = CountCollectionLink 
        fields = '__all__'

class ForkliftSerializer(serializers.ModelSerializer):
    class Meta:
        model = Forklift 
        fields = '__all__'

class ChecklistSubmissionRecordSerializer(serializers.ModelSerializer):
    class Meta:
        model = ChecklistSubmissionRecord 
        fields = '__all__'

class ChecklistLogSerializer(serializers.ModelSerializer):
    class Meta:
        model = ChecklistLog 
        fields = '__all__'

class ComponentUsageSerializer(serializers.ModelSerializer):
    class Meta:
        model = ComponentUsage 
        fields = '__all__'

class ComponentShortageSerializer(serializers.ModelSerializer):
    class Meta:
        model = ComponentShortage 
        fields = '__all__'

class LotNumRecordSerializer(serializers.ModelSerializer):
    class Meta:
        model = LotNumRecord 
        fields = '__all__'

class BlendSheetTemplateSerializer(serializers.ModelSerializer):
    class Meta:
        model = BlendSheetTemplate 
        fields = '__all__'

class BlendSheetSerializer(serializers.ModelSerializer):
    class Meta:
        model = BlendSheet 
        fields = '__all__'

class AdjustmentStatisticSerializer(serializers.ModelSerializer):
    class Meta:
        model = AdjustmentStatistic 
        fields = '__all__'

class BillOfMaterialsSerializer(serializers.ModelSerializer):
    class Meta:
        model = BillOfMaterials 
        fields = '__all__'

class BlendProtectionSerializer(serializers.ModelSerializer):
    class Meta:
        model = BlendProtection 
        fields = '__all__'

class BmBillDetailSerializer(serializers.ModelSerializer):
    class Meta:
        model = BmBillDetail 
        fields = '__all__'

class BmBillHeaderSerializer(serializers.ModelSerializer):
    class Meta:
        model = BmBillHeader 
        fields = '__all__'

class ItemLocationSerializer(serializers.ModelSerializer):
    class Meta:
        model = ItemLocation 
        fields = '__all__'

class AuditGroupSerializer(serializers.ModelSerializer):
    class Meta:
        model = AuditGroup 
        fields = '__all__'

class BlendCountRecordSerializer(serializers.ModelSerializer):
    class Meta:
        model = BlendCountRecord 
        fields = '__all__'

class BlendComponentCountRecordSerializer(serializers.ModelSerializer):
    class Meta:
        model = BlendComponentCountRecord 
        fields = '__all__'

class SubComponentUsageSerializer(serializers.ModelSerializer):
    class Meta:
        model = SubComponentUsage 
        fields = '__all__'

class SubComponentShortageSerializer(serializers.ModelSerializer):
    class Meta:
        model = SubComponentShortage 
        fields = '__all__'

class FoamFactorSerializer(serializers.ModelSerializer):
    class Meta:
        model = FoamFactor 
        fields = '__all__'

class ImItemCostSerializer(serializers.ModelSerializer):
    class Meta:
        model = ImItemCost 
        fields = '__all__'

class ImItemTransactionHistorySerializer(serializers.ModelSerializer):
    class Meta:
        model = ImItemTransactionHistory 
        fields = '__all__'


class WarehouseCountRecordSerializer(serializers.ModelSerializer):
    class Meta:
        model = WarehouseCountRecord
        fields = '__all__'

# Repeat the above pattern for all other models
# ...