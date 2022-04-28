from django.contrib import admin
from core.models import checklistlog, Sample, lotnumrecord
from import_export.admin import ImportExportModelAdmin

from import_export import resources

@admin.register(checklistlog)
class checkListLogAdmin(admin.ModelAdmin):
    list_display=('date', 'operator_name', 'unit_number')
    ordering=('-date',)

class lotnumrecordResource(resources.ModelResource):
    class Meta:
        model=lotnumrecord

@admin.register(lotnumrecord)
class lotnumrecordAdmin(ImportExportModelAdmin):
    list_display=('part_number', 'description', 'quantity', 'lot_number', 'date')
    ordering=('-date',)
    pass

admin.site.register(Sample)