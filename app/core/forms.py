from django import forms
from .models import *
from prodverse.models import *
from decimal import *
from django.db.models.functions import Length

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
    run_date = forms.DateField(widget=forms.DateInput(attrs={'type': 'date'}))

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


item_location_blend_objects = ItemLocation.objects.filter(item_type__iexact='blend')
initial_blend_zone_options = [
    (area.zone, area.zone) for area in item_location_blend_objects.distinct('zone')
]
initial_blend_bin_options = [
    (area.bin, area.bin) for area in item_location_blend_objects.distinct('bin')
]

class BlendCountRecordForm(forms.ModelForm):    

    zone = forms.ChoiceField(choices=initial_blend_zone_options)
    bin = forms.ChoiceField(choices=initial_blend_bin_options)

    class Meta:
        model = BlendCountRecord
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
            'comment',
            'zone',
            'bin'
        )
        widgets = {
            'item_code' : forms.TextInput(),
            'item_description' : forms.TextInput(),
            'count_type' : forms.TextInput(),
            'collection_id' : forms.TextInput()
        }
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)        

        # Set initial value for zone based on item_code match
        item_code = self.initial.get('item_code')
        if item_code:
            matching_item_location = ItemLocation.objects.filter(item_code=item_code).first()
            if matching_item_location:
                self.initial['zone'] = matching_item_location.zone
                self.initial['bin'] = matching_item_location.bin


item_location_blendcomponent_objects = ItemLocation.objects.filter(item_type__iexact='blendcomponent')
initial_component_zone_options = [
    (area.zone, area.zone) for area in item_location_blendcomponent_objects.distinct('zone')
]
initial_component_bin_options = [
    (area.bin, area.bin) for area in item_location_blendcomponent_objects.distinct('bin')
]

class BlendComponentCountRecordForm(forms.ModelForm):

    zone = forms.ChoiceField(choices=initial_component_zone_options)
    bin = forms.ChoiceField(choices=initial_component_bin_options)

    class Meta:
        model = BlendComponentCountRecord
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
            'comment',
            'zone',
            'bin'
        )

        widgets = {
            'item_code' : forms.TextInput(),
            'item_description' : forms.TextInput(),
            'count_type' : forms.TextInput(),
            'collection_id' : forms.TextInput()
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)        

        # Set initial value for zone based on item_code match
        item_code = self.initial.get('item_code')
        if item_code:
            matching_item_location = ItemLocation.objects.filter(item_code=item_code).first()
            if matching_item_location:
                self.initial['zone'] = matching_item_location.zone
                self.initial['bin'] = matching_item_location.bin            


item_location_warehouse_objects = ItemLocation.objects.filter(item_type__iexact='warehouse')
initial_warehouse_zone_options = [
    (area.zone, area.zone) for area in item_location_warehouse_objects.distinct('zone')
]
initial_warehouse_bin_options = [
    (area.bin, area.bin) for area in item_location_warehouse_objects.distinct('bin')
]

class WarehouseCountRecordForm(forms.ModelForm):
    
    zone = forms.ChoiceField(choices=initial_warehouse_zone_options)
    bin = forms.ChoiceField(choices=initial_warehouse_bin_options)

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
            'comment',
            'zone',
            'bin'
        )
        widgets = {
            'item_code' : forms.TextInput(),
            'item_description' : forms.TextInput(),
            'count_type' : forms.TextInput(),
            'collection_id' : forms.TextInput() 
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)        

        # Set initial value for zone based on item_code match
        item_code = self.initial.get('item_code')
        if item_code:
            matching_item_location = ItemLocation.objects.filter(item_code=item_code).first()
            if matching_item_location:
                self.initial['zone'] = matching_item_location.zone
                self.initial['bin'] = matching_item_location.bin

class BlendSheetForm(forms.ModelForm):
    class Meta:
        model = BlendSheet
        fields = (
            'lot_number',
            'blend_sheet'
        )

class FeedbackForm(forms.Form):
    FEEDBACK_TYPE_CHOICES = [
        ('Feature Request', 'Feature Request'),
        ('Improvement Suggestion', 'Improvement Suggestion'),
        ('Issue or Bug', 'Issue or Bug'),
    ]
    feedback_type = forms.ChoiceField(choices=FEEDBACK_TYPE_CHOICES)
    message = forms.CharField(widget=forms.Textarea)

class AuditGroupForm(forms.ModelForm):
    class Meta:
        model = AuditGroup
        fields = (
            'item_code',
            'item_description',
            'audit_group',
            'item_type'
        )