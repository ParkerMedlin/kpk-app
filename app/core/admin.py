from django.contrib import admin
from core.models import *
from import_export.admin import ImportExportModelAdmin
from import_export import resources

@admin.register(CeleryTaskSetting)
class CeleryTaskSettingAdmin(admin.ModelAdmin):
    list_display=('checklist_issues', 'checklist_sub_track')

@admin.register(ChecklistLog)
class CheckListLogAdmin(admin.ModelAdmin):
    list_display=('submitted_date', 'operator_name', 'unit_number')
    ordering=('-submitted_date',)

@admin.register(ChemLocation)
class ChemLocationAdmin(admin.ModelAdmin):
    list_display=('part_number', 'description', 'generallocation', 'specificlocation')
    

# ====== THIS ISN'T BEING USED BUT I DON'T WANT TO ======
# ====== FORGET HOW TO USE THE IMPORT/EXPORT THING ======

# class lotnumrecordResource(resources.ModelResource):
#     class Meta:
#         model=LotNumRecord

# @admin.register(LotNumRecord)
# class lotnumrecordAdmin(ImportExportModelAdmin):
#     list_display=('part_number', 'description', 'quantity', 'lot_number', 'date_created')
#     ordering=('-date_created',)
#     pass

# ====== THIS ISN'T BEING USED BUT I DON'T WANT TO ======
# ====== FORGET HOW TO USE THE IMPORT/EXPORT THING ======

@admin.register(ChecklistSubmissionRecord)
class ChecklistSubmissionTrackerAdmin(admin.ModelAdmin):
    list_display=('check_date',)