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
    engine_oil_checked = forms.ChoiceField(required=True, choices=(('Good', 'Good'), ('False', 'Bad')), widget=forms.RadioSelect)
    propane_tank_checked = forms.ChoiceField(required=True, choices=(('Good', 'Good'), ('Bad', 'Bad')), widget=forms.RadioSelect)
    radiator_leaks_checked = forms.ChoiceField(required=True, choices=(('Good', 'Good'), ('Bad', 'Bad')), widget=forms.RadioSelect)
    tires_checked = forms.ChoiceField(required=True, choices=(('Good', 'Good'), ('Bad', 'Bad')), widget=forms.RadioSelect)
    mast_forks_checked = forms.ChoiceField(required=True, choices=(('Good', 'Good'), ('Bad', 'Bad')), widget=forms.RadioSelect)
    leaks_checked = forms.ChoiceField(required=True, choices=(('Good', 'Good'), ('Bad', 'Bad')), widget=forms.RadioSelect)
    horn_checked = forms.ChoiceField(required=True, choices=(('Good', 'Good'), ('Bad', 'Bad')), widget=forms.RadioSelect)
    driver_compartment_checked = forms.ChoiceField(required=True, choices=(('Good', 'Good'), ('Bad', 'Bad')), widget=forms.RadioSelect)
    seatbelt_checked = forms.ChoiceField(required=True, choices=(('Good', 'Good'), ('Bad', 'Bad')), widget=forms.RadioSelect)
    battery_checked = forms.ChoiceField(required=True, choices=(('Good', 'Good'), ('Bad', 'Bad')), widget=forms.RadioSelect)
    safety_equipment_checked = forms.ChoiceField(required=True, choices=(('Good', 'Good'), ('Bad', 'Bad')), widget=forms.RadioSelect)
    steering_checked = forms.ChoiceField(required=True, choices=(('Good', 'Good'), ('Bad', 'Bad')), widget=forms.RadioSelect)
    brakes_checked = forms.ChoiceField(required=True, choices=(('Good', 'Good'), ('Bad', 'Bad')), widget=forms.RadioSelect)

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
        labels = {
                    'radiator_leaks_comments': 'Radiator comments',
                    'mast_forks_checked': 'Mast and forks checked',
                    'mast_forks_comments': 'Mast and forks comments',
                }
        widgets = {
            'date': forms.HiddenInput(),
            'operator_name': forms.HiddenInput(),
            'engine_oil_checked': forms.RadioSelect(),
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

    def fields_required(self, fields):
    #Used for conditionally marking fields as required.
        for field in fields:
            if not self.cleaned_data.get(field, ''):
                print('we are now setting the field to required yeehaw')
                print('the value of reqfield = ' + self.cleaned_data.get(field))
                msg = forms.ValidationError("Tell us what's wrong.")
                self.add_error(field, msg)

    def clean(self):
        checkfieldlist = ['engine_oil_checked', 'propane_tank_checked', 'radiator_leaks_checked', 'tires_checked', 'mast_forks_checked', 'leaks_checked', 'horn_checked', 'driver_compartment_checked', 'seatbelt_checked', 'battery_checked', 'safety_equipment_checked', 'steering_checked', 'brakes_checked']
        reqfieldlist = ['engine_oil_comments', 'propane_tank_comments', 'radiator_leaks_comments', 'tires_comments', 'mast_forks_comments', 'leaks_comments', 'horn_comments', 'driver_compartment_comments', 'seatbelt_comments', 'battery_comments', 'safety_equipment_comments', 'steering_comments', 'brakes_comments']
        for checkfield, reqfield in zip(checkfieldlist, reqfieldlist):
            mrclean_data = self.cleaned_data.get(checkfield)
            print('the value of mrclean_data = ' + mrclean_data)
            if mrclean_data == 'Bad':
                print('mrclean_data returned bad and we are here')
                print(reqfield)
                self.fields_required([reqfield])
            else:
                self.cleaned_data[reqfield] = ''
            continue
        return self.cleaned_data