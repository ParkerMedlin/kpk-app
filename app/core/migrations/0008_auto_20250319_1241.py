# Generated by Django 3.2.25 on 2025-03-19 17:41

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0007_letdeskschedule'),
    ]

    operations = [
        migrations.AddField(
            model_name='auditgroup',
            name='counting_unit',
            field=models.TextField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name='blendcomponentcountrecord',
            name='sage_converted_quantity',
            field=models.DecimalField(blank=True, decimal_places=5, max_digits=50, null=True),
        ),
        migrations.AddField(
            model_name='blendcountrecord',
            name='sage_converted_quantity',
            field=models.DecimalField(blank=True, decimal_places=5, max_digits=50, null=True),
        ),
    ]
