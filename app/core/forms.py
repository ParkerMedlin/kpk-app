from django import forms
from .models import *

reportchoices = [('Chem-Shortage','Chem Shortage'),
                    ('Startron-Runs','Startron Runs'),
                    ('Transaction-History','Transaction History'),
                    ('Lot-Numbers','Lot Numbers'),
                    ('All-Upcoming-Runs','All Upcoming Runs'),
                    ('Physical-Count-History','Physical Count History'),
                    ('Counts-And-Transactions','Counts And Transactions')
                    ]

class ReportForm(forms.Form):
    part_number=forms.CharField(max_length=100,label='Enter Part Number:')
    # description=forms.CharField(max_length=100,label='Item Description:')
    which_report=forms.CharField(
        widget=forms.Select(choices=reportchoices)
        )

# Form for Django-created input table checklistlog.html
class ChecklistLogForm(forms.ModelForm):
    # Set all checkboxes to require user to check the box
    engine_oil_checked = forms.BooleanField(required=True)
    propane_tank_checked = forms.BooleanField(required=True)
    radiator_leaks_checked = forms.BooleanField(required=True)
    tires_checked = forms.BooleanField(required=True)
    mast_forks_checked = forms.BooleanField(required=True)
    leaks_checked = forms.BooleanField(required=True)
    horn_checked = forms.BooleanField(required=True)
    driver_compartment_checked = forms.BooleanField(required=True)
    seatbelt_checked = forms.BooleanField(required=True)
    battery_checked = forms.BooleanField(required=True)
    safety_equipment_checked = forms.BooleanField(required=True)
    steering_checked = forms.BooleanField(required=True)
    brakes_checked = forms.BooleanField(required=True)
    unit_number = forms.ModelChoiceField(queryset=Forklift.objects.all(), to_field_name = 'forklift_id', empty_label="Select Forklift Number")
    
    class Meta:
        model = ChecklistLog
        
        fields = (
                    'unit_number',
                    'serial_number',
                    'engine_oil_checked',
                    'engine_oil_comments',
                    'propane_tank_checked',
                    'propane_tank_comments',
                    'radiator_leaks_checked',
                    'radiator_leaks_comments',
                    'tires_checked',
                    'tires_comments',
                    'mast_forks_checked',
                    'mast_forks_comments',
                    'leaks_checked',
                    'leaks_comments',
                    'horn_checked',
                    'horn_comments',
                    'driver_compartment_checked',
                    'driver_compartment_comments',
                    'seatbelt_checked',
                    'seatbelt_comments',
                    'battery_checked',
                    'battery_comments',
                    'safety_equipment_checked',
                    'safety_equipment_comments',
                    'steering_checked',
                    'steering_comments',
                    'brakes_checked',
                    'brakes_comments'
                    )
                
        widgets = {
            'date': forms.HiddenInput(),
            'operator_name': forms.HiddenInput(),
            'engine_oil_comments': forms.Textarea(attrs={'cols':'23', 'rows':'2'}),
            'propane_tank_comments': forms.Textarea(attrs={'cols':'23', 'rows':'2'}),
            'radiator_leaks_comments': forms.Textarea(attrs={'cols':'23', 'rows':'2'}),
            'tires_comments': forms.Textarea(attrs={'cols':'23', 'rows':'2'}),
            'mast_forks_comments': forms.Textarea(attrs={'cols':'23', 'rows':'2'}),
            'leaks_comments': forms.Textarea(attrs={'cols':'23', 'rows':'2'}),
            'horn_comments': forms.Textarea(attrs={'cols':'23', 'rows':'2'}),
            'driver_compartment_comments': forms.Textarea(attrs={'cols':'23', 'rows':'2'}),
            'seatbelt_comments': forms.Textarea(attrs={'cols':'23', 'rows':'2'}),
            'battery_comments': forms.Textarea(attrs={'cols':'23', 'rows':'2'}),
            'safety_equipment_comments': forms.Textarea(attrs={'cols':'23', 'rows':'2'}),
            'steering_comments': forms.Textarea(attrs={'cols':'23', 'rows':'2'}),
            'brakes_comments': forms.Textarea(attrs={'cols':'23', 'rows':'2'}, ),
        }

        def clean(self):
            shipping = self.cleaned_data.get('engine_oil_checked')
            if shipping:
                msg = forms.ValidationError("This field is required.")
                self.add_error('engine_oil_comments', msg)
            else:
                # Keep the database consistent. The user may have
                # submitted a shipping_destination even if shipping
                # was not selected
                self.cleaned_data['engine_oil_comments'] = 'BEEEEP'

            return self.cleaned_data