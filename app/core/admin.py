from django.contrib import admin
from core.models import *
from import_export.admin import ImportExportModelAdmin
from import_export import resources

@admin.register(ChecklistLog)
class CheckListLogAdmin(admin.ModelAdmin):
    list_display=('submitted_date', 'operator_name', 'unit_number')
    ordering=('-submitted_date',)

@admin.register(ChemLocation)
class ChemLocationAdmin(admin.ModelAdmin):
    list_display=('part_number', 'description', 'generallocation', 'specificlocation')
    
@admin.register(CountRecord)
class CountRecordAdmin(admin.ModelAdmin):
    list_display=('part_number', 'part_description', 'expected_quantity', 'counted_quantity', 'counted_date', 'variance')

# ====== THIS ISN'T BEING USED BUT I DON'T WANT TO ======
# ==== FORGET HOW TO USE THE CSV IMPORT/EXPORT THING ====

# class lotnumrecordResource(resources.ModelResource):
#     class Meta:
#         model=LotNumRecord

# @admin.register(LotNumRecord)
# class lotnumrecordAdmin(ImportExportModelAdmin):
#     list_display=('part_number', 'description', 'lot_quantity', 'lot_number', 'date_created')
#     ordering=('-date_created',)


# ====== THIS ISN'T BEING USED BUT I DON'T WANT TO ======
# ==== FORGET HOW TO USE THE CSV IMPORT/EXPORT THING ====

@admin.register(ChecklistSubmissionRecord)
class ChecklistSubmissionTrackerAdmin(admin.ModelAdmin):
    list_display=('check_date',)

@admin.register(LotNumRecord)
class lotnumrecordAdmin(ImportExportModelAdmin):
    list_display=('part_number', 'description', 'lot_quantity', 'lot_number')