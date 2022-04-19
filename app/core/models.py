from django.db import models

class userprofile(models.Model):
    first_name = models.CharField(max_length=40)
    last_name = models.CharField(max_length=40)
    phone_number = models.CharField(max_length=20)

    def __str__(self):
        return "%s %s" % (self.first_name, self.last_name)

class Sample(models.Model):
    attachment = models.FileField()

class checklistlog(models.Model):
    date = models.DateTimeField('DateTime')
    operator_name = models.CharField(max_length=100, null=True)
    #operator_name = models.ForeignKey(userprofile, blank=True, null=True, on_delete=models.PROTECT)
    unit_number = models.CharField(max_length=100)
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