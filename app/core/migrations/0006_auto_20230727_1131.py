# Generated by Django 3.2.19 on 2023-07-27 16:31

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0005_rename_countcollectionlinks_countcollectionlink'),
    ]

    operations = [
        migrations.CreateModel(
            name='BlendSheet',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('blend_sheet', models.JSONField()),
                ('lot_number', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='core.lotnumrecord')),
            ],
        ),
        migrations.CreateModel(
            name='BlendSheetTemplate',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('item_code', models.TextField()),
                ('blend_sheet_template', models.JSONField()),
            ],
        ),
        migrations.DeleteModel(
            name='BlendingStep',
        ),
        migrations.DeleteModel(
            name='BlendProcedure',
        ),
    ]