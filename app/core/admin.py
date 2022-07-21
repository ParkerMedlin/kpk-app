from django.contrib import admin
from core.models import *
from import_export.admin import ImportExportModelAdmin
from import_export import resources

@admin.register(CeleryTaskSetting)
class CeleryTaskSettingAdmin(admin.ModelAdmin):
    list_display=('checklist_issues', 'checklist_sub_track')

@admin.register(BlendingStep)
class BlendingStepAdmin(admin.ModelAdmin):
    list_display=('step_no', 'blend_lot_number','blend_part_num', 'picture_attachment')
    ordering=('blend_lot_number','step_no')

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
    list_display=('part_number', 'description', 'quantity', 'lot_number', 'date_created')
    ordering=('-date_created',)
    pass

@admin.register(ChecklistSubmissionTracker)
class ChecklistSubmissionTrackerAdmin(admin.ModelAdmin):
    list_display=('check_date',)

admin.site.register(Sample)