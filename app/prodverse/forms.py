from django import forms
from prodverse.models import *

class ProdComponentCountRecordForm(forms.ModelForm):

    class Meta:
        model = ProdComponentCountRecord
        fields = (
            'item_code',
            'item_description',
            'expected_quantity',
            'counted_quantity',
            'counted_date',
            'variance',
            'counted',
            'count_type',
            'collection_id'
        )
        widgets = {
            'item_code' : forms.TextInput(),
            'item_description' : forms.TextInput(),
            'count_type' : forms.TextInput(),
            'collection_id' : forms.TextInput()
        }