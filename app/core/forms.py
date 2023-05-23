from django import forms
from .models import *
from decimal import *
from django.db.models.functions import Length
from crispy_forms.helper import FormHelper

class ChecklistLogForm(forms.ModelForm):
    engine_oil = forms.ChoiceField(required=True, choices=(('Good', 'Good'), ('Bad', 'Bad')), widget=forms.RadioSelect)
    propane_tank = forms.ChoiceField(required=True, choices=(('Good', 'Good'), ('Bad', 'Bad')), widget=forms.RadioSelect)
    radiator_leaks = forms.ChoiceField(required=True, choices=(('Good', 'Good'), ('Bad', 'Bad')), widget=forms.RadioSelect)
    tires = forms.ChoiceField(required=True, choices=(('Good', 'Good'), ('Bad', 'Bad')), widget=forms.RadioSelect)
    mast_and_forks = forms.ChoiceField(required=True, choices=(('Good', 'Good'), ('Bad', 'Bad')), widget=forms.RadioSelect)
    leaks = forms.ChoiceField(required=True, choices=(('Good', 'Good'), ('Bad', 'Bad')), widget=forms.RadioSelect)
    horn = forms.ChoiceField(required=True, choices=(('Good', 'Good'), ('Bad', 'Bad')), widget=forms.RadioSelect)
    driver_compartment = forms.ChoiceField(required=True, choices=(('Good', 'Good'), ('Bad', 'Bad')), widget=forms.RadioSelect)
    seatbelt = forms.ChoiceField(required=True, choices=(('Good', 'Good'), ('Bad', 'Bad')), widget=forms.RadioSelect)
    battery = forms.ChoiceField(required=True, choices=(('Good', 'Good'), ('Bad', 'Bad')), widget=forms.RadioSelect)
    safety_equipment = forms.ChoiceField(required=True, choices=(('Good', 'Good'), ('Bad', 'Bad')), widget=forms.RadioSelect)
    steering = forms.ChoiceField(required=True, choices=(('Good', 'Good'), ('Bad', 'Bad')), widget=forms.RadioSelect)
    brakes = forms.ChoiceField(required=True, choices=(('Good', 'Good'), ('Bad', 'Bad')), widget=forms.RadioSelect)
                
    class Meta:
        model = ChecklistLog
        fields = (
                    'forklift',
                    'serial_number',
                    'engine_oil',
                    'engine_oil_comments',
                    'propane_tank',
                    'propane_tank_comments',
                    'radiator_leaks',
                    'radiator_leaks_comments',
                    'tires',
                    'tires_comments',
                    'mast_and_forks',
                    'mast_and_forks_comments',
                    'leaks',
                    'leaks_comments',
                    'horn',
                    'horn_comments',
                    'driver_compartment',
                    'driver_compartment_comments',
                    'seatbelt',
                    'seatbelt_comments',
                    'battery',
                    'battery_comments',
                    'safety_equipment',
                    'safety_equipment_comments',
                    'steering',
                    'steering_comments',
                    'brakes',
                    'brakes_comments'
                    )
        labels = {
                    'radiator_leaks_comments': 'Radiator comments',
                    'mast_and_forks_comments': 'Mast and forks comments',
                }
        widgets = {
            'submitted_date': forms.HiddenInput(),
            'operator_name': forms.HiddenInput(),
            'engine_oil_comments': forms.Textarea(attrs={'cols':'23', 'rows':'2'}),
            'propane_tank_comments': forms.Textarea(attrs={'cols':'23', 'rows':'2'}),
            'radiator_leaks_comments': forms.Textarea(attrs={'cols':'23', 'rows':'2'}),
            'tires_comments': forms.Textarea(attrs={'cols':'23', 'rows':'2'}),
            'mast_and_forks_comments': forms.Textarea(attrs={'cols':'23', 'rows':'2'}),
            'leaks_comments': forms.Textarea(attrs={'cols':'23', 'rows':'2'}),
            'horn_comments': forms.Textarea(attrs={'cols':'23', 'rows':'2'}),
            'driver_compartment_comments': forms.Textarea(attrs={'cols':'23', 'rows':'2'}),
            'seatbelt_comments': forms.Textarea(attrs={'cols':'23', 'rows':'2'}),
            'battery_comments': forms.Textarea(attrs={'cols':'23', 'rows':'2'}),
            'safety_equipment_comments': forms.Textarea(attrs={'cols':'23', 'rows':'2'}),
            'steering_comments': forms.Textarea(attrs={'cols':'23', 'rows':'2'}),
            'brakes_comments': forms.Textarea(attrs={'cols':'23', 'rows':'2'}, ),
        }

    def fields_required(self, fields):
    # Used for conditionally marking fields as required.
        for field in fields:
            if not self.cleaned_data.get(field, ''):
                print('we are now setting the field to required yeehaw')
                print('the value of reqfield = ' + self.cleaned_data.get(field))
                msg = forms.ValidationError("Tell us what's wrong.")
                self.add_error(field, msg)

    def clean(self):
        checkbox_field_list = ['engine_oil', 'propane_tank', 'radiator_leaks', 'tires', 'mast_and_forks', 'leaks', 'horn', 'driver_compartment', 'seatbelt', 'battery', 'safety_equipment', 'steering', 'brakes']
        comment_field_list = ['engine_oil_comments', 'propane_tank_comments', 'radiator_leaks_comments', 'tires_comments', 'mast_and_forks_comments', 'leaks_comments', 'horn_comments', 'driver_compartment_comments', 'seatbelt_comments', 'battery_comments', 'safety_equipment_comments', 'steering_comments', 'brakes_comments']
        for checkbox_field, comment_field in zip(checkbox_field_list, comment_field_list):
            mr_clean_data = self.cleaned_data.get(checkbox_field)
            if mr_clean_data == 'Bad':
                print('mr_clean_data returned bad and we are here')
                print(comment_field)
                self.fields_required([comment_field])
            else:
                self.cleaned_data[comment_field] = ''
            continue
        return self.cleaned_data

desk_choices = [('Desk_1', 'Desk_1'), ('Desk_2', 'Desk_2'), ('Horix', 'Horix')]
line_choices = [
    ('Prod', 'Prod'),
    ('Hx', 'Hx'),
    ('Dm', 'Dm'),
    ('Totes', 'Totes'),
    ('Pails', 'Pails')
    ]


class LotNumRecordForm(forms.ModelForm):
    class Meta:
        model = LotNumRecord
        fields = ('item_code', 'item_description', 'lot_number', 'lot_quantity', 'date_created', 'line', 'desk', 'run_date')
        widgets = {
            'item_code' : forms.TextInput(),
            'item_description' : forms.TextInput(),
            'lot_number' : forms.TextInput(),
            'lot_quantity' : forms.NumberInput(attrs={'pattern': '[0-9]*'}),
            'date_created' : forms.DateInput(format='%m/%d/%Y %H:%M'),
            'line' : forms.Select(choices=line_choices),
            'desk' : forms.Select(choices=desk_choices),
            'run_date' : forms.DateInput(format='%m/%d/%Y'),
            'steps': forms.HiddenInput()

        }

        labels = {
            'item_code': 'Item Code:',
            'lot_number': 'Lot Number',
            'date_created': 'Date:',
            'run_date': 'Run Date:'
        }
    def __init__(self, *args, **kwargs):
        super(LotNumRecordForm, self).__init__(*args, **kwargs)
        self.fields['run_date'].required = False

class BlendingStepForm(forms.ModelForm):
    class Meta:
        model = BlendingStep
        fields = (
                    'step_no',
                    'step_desc',
                    'step_qty',
                    'step_unit',
                    'qty_added',
                    'component_item_code',
                    'chem_lot_number',
                    'notes_1',
                    'notes_2',
                    'start_time',
                    'end_time',
                    'chkd_by',
                    'mfg_chkd_by',
                    'picture_attachment'
                    )
        widgets = {
                    'step_qty': forms.NumberInput(attrs={'pattern': '[0-9]*'}),
                    'step_unit': forms.TextInput(),
                    'qty_added': forms.NumberInput(attrs={'pattern': '[0-9]*'}),
                    'component_item_code': forms.TextInput(),
                    'chem_lot_number': forms.TextInput(),
                    'notes_1': forms.TextInput(),
                    'notes_2': forms.TextInput(),
                    'start_time': forms.TimeInput(format='%H:%M'),
                    'end_time': forms.TimeInput(format='%H:%M'),
                    'chkd_by': forms.TextInput(),
                    'mfg_chkd_by': forms.TextInput(),
                    }
        labels = {
                    'step_no': '',
                    'step_desc': '',
                    'step_qty': '',
                    'step_unit': '',
                    'qty_added': '',
                    'component_item_code': '',
                    'chem_lot_number': '',
                    'notes_1': '',
                    'notes_2': '',
                    'start_time': '',
                    'end_time': '',
                    'chkd_by': '',
                    'mfg_chkd_by': '',
                    'picture_attachment': '',
                }



class CountRecordForm(forms.ModelForm):
    #expected_quantity = forms.DecimalField(decimal_places=2)
    # def __init__(self, *args, **kwargs):
    #      super(CountRecordForm, self).__init__(*args, **kwargs)
    #      if 'instance' in kwargs:
    #         kwargs['instance'].expected_quantity = kwargs['instance'].expected_quantity.quantize(Decimal('0.0001'))
    #         self.fields['expected_quantity'].decimal_places = 4

    class Meta:
        model = CountRecord
        fields = (
            'item_code',
            'item_description',
            'expected_quantity',
            'counted_quantity',
            'counted_date',
            'variance',
            'counted',
            'count_type'
        )
        widgets = {
            'item_code' : forms.TextInput(),
            'item_description' : forms.TextInput(),
            'count_type' : forms.TextInput(),
        }

areachoices = [
                ('Desk_1','Desk_1'),
                ('Desk_2','Desk_2'),
                ]

class DeskOneScheduleForm(forms.ModelForm):
    class Meta:
        model = DeskOneSchedule
        fields = ('item_code','item_description','lot','blend_area')
        widgets = {
            'item_code': forms.TextInput(),
            'item_description': forms.TextInput(),
            'lot': forms.TextInput(),
            'blend_area': forms.Select(choices=areachoices)
        }
        labels = {
            'item_code': 'Item Code'
        }

class DeskTwoScheduleForm(forms.ModelForm):
    class Meta:
        model = DeskTwoSchedule
        fields = ('item_code','item_description','lot','blend_area')
        widgets = {
            'item_code': forms.TextInput(),
            'item_description': forms.TextInput(),
            'lot': forms.TextInput(),
            'blend_area': forms.Select(choices=areachoices)
        }
        labels = {
            'item_code': 'Item Code'
        }