from django import forms
from .models import *
from django.db.models.functions import Length

report_choices = [('Chem-Shortage','Chem Shortage'),
                    ('Startron-Runs','Startron Runs'),
                    ('Transaction-History','Transaction History'),
                    ('Lot-Numbers','Lot Numbers'),
                    ('All-Upcoming-Runs','All Upcoming Runs'),
                    ('Physical-Count-History','Physical Count History'),
                    ('Counts-And-Transactions','Counts And Transactions')
                    ]

class ReportForm(forms.Form):
    part_number=forms.CharField(max_length=100,label='Enter Part Number:')
    which_report=forms.CharField(
        widget=forms.Select(choices=report_choices)
        )


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
                    'unit_number',
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


class LotNumRecordForm(forms.ModelForm):
    class Meta:
        model = LotNumRecord
        fields = ('part_number', 'description', 'lot_number', 'quantity', 'date_created')
        widgets = {
            'part_number': forms.TextInput(),
            'description': forms.TextInput(),
            'lot_number': forms.TextInput(),
            'quantity': forms.NumberInput(attrs={'pattern': '[0-9]*'}),
            'date_created': forms.DateInput(format='%m/%d/%Y %H:%M'),
            'steps': forms.HiddenInput(),
        }
        labels = {
            'part_number': 'Part Number:',
            'lot_number': 'Lot Number',
            'date_created': 'Date:'
        }


class BlendingStepModelForm(forms.ModelForm):

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


areachoices = [
                ('Desk1','Desk1'),
                ('Desk2','Desk2'),
                ]

class DeskOneScheduleForm(forms.ModelForm):
    class Meta:
        model = DeskOneSchedule
        fields = ('blend_pn','description','lot','quantity','totes_needed','blend_area')
        widgets = {
            'blend_pn': forms.TextInput(),
            'description': forms.TextInput(),
            'lot': forms.TextInput(),
            'quantity': forms.TextInput(),
            'totes_needed': forms.TextInput(),
            'blend_area': forms.Select(choices=areachoices)
        }
        labels = {
            'blend_pn': 'Part Number'
        }

class DeskTwoScheduleForm(forms.ModelForm):
    class Meta:
        model = DeskTwoSchedule
        fields = ('blend_pn','description','lot','quantity','totes_needed','blend_area')
        widgets = {
            'blend_pn': forms.TextInput(),
            'description': forms.TextInput(),
            'lot': forms.TextInput(),
            'quantity': forms.TextInput(),
            'totes_needed': forms.TextInput(),
            'blend_area': forms.Select(choices=areachoices)
        }
        labels = {
            'blend_pn': 'Part Number'
        }