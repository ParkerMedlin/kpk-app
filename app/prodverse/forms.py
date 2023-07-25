from django import forms
from prodverse.models import *
from django.contrib.auth.models import User

user_choices = User.objects.order_by('username').values_list('username', flat=True)

class WarehouseCountRecordForm(forms.ModelForm):

    class Meta:
        model = WarehouseCountRecord
        fields = (
            'item_code',
            'item_description',
            'expected_quantity',
            'counted_quantity',
            'counted_date',
            'variance',
            'counted',
            'count_type',
            'collection_id',
            'counted_by'
        )
        widgets = {
            'item_code' : forms.TextInput(),
            'item_description' : forms.TextInput(),
            'count_type' : forms.TextInput(),
            'collection_id' : forms.TextInput(),
            'counted_by' : forms.Select(choices=user_choices)   
        }