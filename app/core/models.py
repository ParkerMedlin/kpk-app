from django.db import models
from django import forms


class Sample(models.Model):
    attachment = models.FileField()

FORKLIFT_CHOICES = [
    ('17', '17'),
    ('6', '6'),
]

class checklistlog(models.Model):
    date = models.DateTimeField('Date')
    operator_name = models.CharField(max_length=100, null=True)
    unit_number = models.CharField(max_length=3, choices=FORKLIFT_CHOICES)
    serial_number = models.CharField(max_length=100)
    engine_oil_checked = models.BooleanField()
    engine_oil_comments = models.TextField(blank=True)
    propane_tank_checked = models.BooleanField()
    propane_tank_comments = models.TextField(blank=True)
    radiator_leaks_checked = models.BooleanField()
    radiator_leaks_comments = models.TextField(blank=True)
    tires_checked = models.BooleanField()
    tires_comments = models.TextField(blank=True)
    mast_forks_checked = models.BooleanField()
    mast_forks_comments = models.TextField(blank=True)
    leaks_checked = models.BooleanField()
    leaks_comments = models.TextField(blank=True)
    horn_checked = models.BooleanField()
    horn_comments = models.TextField(blank=True)
    driver_compartment_checked = models.BooleanField()
    driver_compartment_comments = models.TextField(blank=True)
    seatbelt_checked = models.BooleanField()
    seatbelt_comments = models.TextField(blank=True)
    battery_checked = models.BooleanField()
    battery_comments = models.TextField(blank=True)
    safety_equipment_checked = models.BooleanField()
    safety_equipment_comments = models.TextField(blank=True)
    steering_checked = models.BooleanField()
    steering_comments = models.TextField(blank=True)
    brakes_checked = models.BooleanField()
    brakes_comments = models.TextField(blank=True)

    def __str__(self):
        return self.operator_name

class safetyChecklistForm(forms.ModelForm):
    class Meta:
        model = checklistlog
        fields = ('date',
                    'operator_name',
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
            'engine_oil_comments': forms.TextInput(),
            'propane_tank_comments': forms.TextInput(),
            'radiator_leaks_comments': forms.TextInput(),
            'tires_comments': forms.TextInput(),
            'mast_forks_comments': forms.TextInput(),
            'leaks_comments': forms.TextInput(),
            'horn_comments': forms.TextInput(),
            'driver_compartment_comments': forms.TextInput(),
            'seatbelt_comments': forms.TextInput(),
            'battery_comments': forms.TextInput(),
            'safety_equipment_comments': forms.TextInput(),
            'steering_comments': forms.TextInput(),
            'brakes_comments': forms.TextInput(),
        }

class blendthese(models.Model):
    blend = models.TextField(blank=True, null=True)
    blend_description = models.TextField(blank=True, null=True)
    starttime = models.TextField(blank=True, null=True)
    line = models.TextField(blank=True, null=True)
    oh_now = models.DecimalField(max_digits=100, decimal_places=2, null=True)
    oh_during_run = models.DecimalField(max_digits=100, decimal_places=2, null=True)
    qty_required = models.DecimalField(max_digits=100, decimal_places=2, null=True)
    oh_after_run = models.DecimalField(max_digits=100, decimal_places=2, null=True)
    one_week_short = models.DecimalField(max_digits=100, decimal_places=2, null=True)
    two_week_short = models.DecimalField(max_digits=100, decimal_places=2, null=True)
    three_week_short = models.DecimalField(max_digits=100, decimal_places=2, null=True)

    class Meta:
        managed = False
        db_table = 'blendthese'

class lotnumexcel(models.Model):
    part_number = models.TextField(blank=True, null=True)
    description = models.TextField(blank=True, null=True)
    lot_number = models.TextField(blank=True, null=True)
    quantity = models.DecimalField(max_digits=100, decimal_places=2, null=True)
    date = models.TextField(blank=True, null=True)

    class Meta:
        managed = False
        db_table = 'lotnumexcel'

class lotnumrecord(models.Model):
    part_number = models.TextField(blank=True, null=True)
    description = models.TextField(blank=True, null=True)
    lot_number = models.TextField(primary_key=True, blank=True)
    quantity = models.IntegerField(null=True)
    date = models.TextField(blank=True, null=True)

    def __str__(self):
        return self.lot_number

class lotnumrecordForm(forms.ModelForm):
    class Meta:
        model = lotnumrecord
        fields = ('part_number', 'description', 'lot_number', 'quantity', 'date')
        widgets = {
            'part_number': forms.TextInput(),
            'description': forms.TextInput(),
            'lot_number': forms.TextInput(),
            'quantity': forms.NumberInput(),
            'date': forms.DateInput(),
        }