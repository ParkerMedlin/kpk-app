from django import forms
from .models import *
from prodverse.models import *
from decimal import *
from django.db.models.functions import Length
from .models import FormulaChangeAlert
import json

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
 
desk_choices = [('Desk_1', 'Desk_1'), ('Desk_2', 'Desk_2'), ('LET_Desk', 'LET_Desk'), ('Horix', 'Horix')]
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

    # def clean(self):
    #     item_code = self.cleaned_data.get("item_code","")
    #     blend_restrictions = BlendTankRestriction.objects.get(item_code__iexact=item_code)
    #     range_one = (blend_restrictions.range_one_minimum, blend_restrictions.range_one_maximum)
    #     range_two = (blend_restrictions.range_two_minimum, blend_restrictions.range_two_maximum)

    #     lot_quantity = self.cleaned_data.get("lot_quantity","")
    #     if lot_quantity >= range_one[0] and lot_quantity <= range_one[1]:
    #         return self.cleaned_data
    #     elif lot_quantity >= range_two[0] and lot_quantity <= range_two[1]:
    #         return self.cleaned_data
    #     else:
    #         error_string = "Invalid quantity. Please change quantity to fit within the blend vessel.\n"
    #         if range_two[0] == 0 and range_two[1] == 0:
    #             if range_one[0] == range_one[1]:
    #                 error_string += f"Blend size must be {range_one[0]}."
    #             else:
    #                 error_string += f"Blend size must be between {range_one[0]} and {range_one[1]}."
    #         else:
    #             error_string = f"""Invalid quantity. Please change quantity to fit within the blend vessel.\n
    #                                 Blend size must be between {range_one[0]} and {range_one[1]} OR\n
    #                                 between {range_two[0]} and {range_two[1]}."""
    #         error_message = forms.ValidationError(error_string)
    #         self.add_error("lot_quantity", error_message)
    #     return self.cleaned_data

    def __init__(self, *args, **kwargs):
        super(LotNumRecordForm, self).__init__(*args, **kwargs)
        self.fields['run_date'].required = False

class FoamFactorForm(forms.ModelForm):
    class Meta:
        model = FoamFactor
        fields = ('item_code','item_description','factor')

        widgets = {
            'item_code' : forms.TextInput(),
            'item_description' : forms.TextInput(),
            'factor' : forms.NumberInput(attrs={'pattern': '[0-9]*'})
        }

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
            'sage_converted_quantity',
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
            'sage_converted_quantity',
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
            'sage_converted_quantity',
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
            'counting_unit',
            'item_type'
        )
        widgets = {
            'item_code' : forms.TextInput(),
            'item_description' : forms.TextInput(),
        }

    def __init__(self, *args, **kwargs):
        super(AuditGroupForm, self).__init__(*args, **kwargs)
        # Dynamically set choices for audit_group field
        audit_group_choices = AuditGroup.objects.values_list('audit_group', flat=True).distinct().order_by('audit_group')
        audit_group_choices = [(choice, choice) for choice in audit_group_choices]
        self.fields['audit_group'].widget = forms.Select(choices=audit_group_choices)

        # Dynamically set choices for item_type field
        item_type_choices = AuditGroup.objects.values_list('item_type', flat=True).distinct()
        item_type_choices = [(choice, choice) for choice in item_type_choices]
        self.fields['item_type'].widget = forms.Select(choices=item_type_choices)

        counting_unit_choices = ['GAL','LB','LBS','FT','GRAM','TOTE','GA','100G','DRUM','FEET','EA','EACH','CASE','SECH','PAIL','CS','',]
        counting_unit_choices = [(choice, choice) for choice in counting_unit_choices]
        self.fields['counting_unit'].widget = forms.Select(choices=counting_unit_choices)


class GHSPictogramForm(forms.ModelForm):
    class Meta:
        model = GHSPictogram
        fields = ("item_code", "item_description", "image_reference")

        labels = {"image_reference" : "Image"}

class BlendTankRestrictionForm(forms.ModelForm):
    class Meta:
        model = BlendTankRestriction
        fields = ("item_code", "range_one_minimum", "range_one_maximum", "range_two_minimum", "range_two_maximum")

class ItemLocationForm(forms.ModelForm):
    class Meta:
        model = ItemLocation
        fields = ('item_code', 'item_description', 'unit', 'storage_type', 'zone', 'bin', 'item_type')

        widgets = {
            'item_code': forms.TextInput(),
            'item_description': forms.TextInput(),
            'unit': forms.TextInput(),
            'storage_type': forms.TextInput(),
            'item_type': forms.Select(choices=[
                ('blend', 'Blend'),
                ('blendcomponent', 'Blend Component'),
                ('warehouse', 'Warehouse')
            ]),
            'zone': forms.TextInput(),
            'bin': forms.TextInput()
        }

        labels = {
            'item_code': 'Item Code:',
            'item_description': 'Description:',
            'unit': 'Unit:',
            'storage_type': 'Storage Type:',
            'item_type': 'Item Type:',
            'zone': 'Zone:',
            'bin': 'Bin:'
        }

class ToteClassificationForm(forms.ModelForm):
    class Meta:
        model = ToteClassification
        fields = ('item_code', 'tote_classification')
        
        widgets = {
            'item_code': forms.TextInput(),
            'tote_classification': forms.TextInput()
        }
        
        labels = {
            'item_code': 'Item Code:',
            'tote_classification': 'Tote Classification:'
        }

class FormulaChangeAlertForm(forms.ModelForm):
    parent_item_codes = forms.CharField(
        widget=forms.Textarea(attrs={'rows': 3, 'placeholder': 'Enter as a JSON list, e.g., ["ITEM001", "ITEM002"]'}),
        help_text='Enter a valid JSON list of parent item codes. Example: ["PARENT1", "PARENT2"]'
    )

    class Meta:
        model = FormulaChangeAlert
        fields = ['parent_item_codes', 'ingredient_item_code', 'notification_trigger_quantity']
        widgets = {
            'ingredient_item_code': forms.TextInput(attrs={'placeholder': 'e.g., INGRDNT001'}),
            'notification_trigger_quantity': forms.NumberInput(attrs={'placeholder': 'e.g., 100.00'}),
        }
        labels = {
            'parent_item_codes': 'Parent Item Codes (JSON List)',
            'ingredient_item_code': 'Ingredient Item Code',
            'notification_trigger_quantity': 'Notification Trigger Quantity',
        }

    def clean_parent_item_codes(self):
        data = self.cleaned_data['parent_item_codes']
        try:
            parsed_data = json.loads(data)
            if not isinstance(parsed_data, list):
                raise forms.ValidationError("Input must be a JSON list.")
            for item in parsed_data:
                if not isinstance(item, str):
                    raise forms.ValidationError("All items in the list must be strings (item codes).")
            return parsed_data # Return the Python list
        except json.JSONDecodeError:
            raise forms.ValidationError("Invalid JSON format.")
        except TypeError:
            raise forms.ValidationError("Invalid input for JSON list.")

class PurchasingAliasForm(forms.ModelForm):
    class Meta:
        model = PurchasingAlias
        fields = [
            'vendor_part_number',
            'vendor_description',
            'blending_notes',
            'item_image'
        ]
        widgets = {
            'vendor_part_number': forms.TextInput(attrs={'placeholder': 'Item code from vendor...'}),
            'vendor_description': forms.Textarea(attrs={'rows': 3, 'placeholder': 'Full description from vendor...'}),
            'blending_notes': forms.Textarea(attrs={'rows': 3, 'placeholder': 'Notes for the blending team...'}),
        }
        labels = {
            'vendor_part_number': 'Vendor Part No.',
            'vendor_description': 'Vendor Description',
            'blending_notes': 'Blending Notes',
            'item_image': 'Item Image',
        }
