from django.db import models
from django.forms import DateField, ModelForm
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
        fields = ('unit_number',
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
        }