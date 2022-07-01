from django.contrib import admin
from core.models import ChecklistLog, Sample, LotNumRecord, CiItem, BmBillDetail
from import_export.admin import ImportExportModelAdmin
from import_export import resources

@admin.register(CiItem)
class CiItemAdmin(admin.ModelAdmin):
    list_display=('itemcode','itemcodedesc')

@admin.register(BmBillDetail)
class BmBillDetailAdmin(admin.ModelAdmin):
    list_display=('billno','componentitemcode','componentdesc')
    
@admin.register(ChecklistLog)
class checkListLogAdmin(admin.ModelAdmin):
    list_display=('submitted_date', 'operator_name', 'unit_number')
    ordering=('-submitted_date',)

class lotnumrecordResource(resources.ModelResource):
    class Meta:
        model=LotNumRecord

@admin.register(LotNumRecord)
class lotnumrecordAdmin(ImportExportModelAdmin):
    list_display=('part_number', 'description', 'quantity', 'lot_number', 'date')
    ordering=('-date',)
    pass

admin.site.register(Sample)