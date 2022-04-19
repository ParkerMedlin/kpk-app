from django.contrib import admin
from .models import userprofile
from .models import checklistlog

admin.site.register(checklistlog)

@admin.register(userprofile)
class userprofileAdmin(admin.ModelAdmin):
    list_display = ('first_name', 'last_name', 'phone_number')
    ordering = ('last_name',)

from core.models import Sample

admin.site.register(Sample)
