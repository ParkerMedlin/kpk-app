from django.contrib import admin
from .models import checklistlog
from .models import Sample

@admin.register(checklistlog)
class checkListLogAdmin(admin.ModelAdmin):
    list_display=('date', 'operator_name', 'unit_number')
    ordering=('-date',)
admin.site.register(Sample)
