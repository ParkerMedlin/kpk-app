# Generated by Django 3.2.25 on 2025-05-14 10:46

from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
    ]

    operations = [
        migrations.CreateModel(
            name='SpecSheetData',
            fields=[
                ('item_code', models.TextField(db_column='ItemCode', primary_key=True, serialize=False)),
                ('component_item_code', models.TextField(blank=True, db_column='ComponentItemCode')),
                ('product_class', models.TextField(blank=True, db_column='Product Class')),
                ('water_flush', models.TextField(blank=True, db_column='Water Flush')),
                ('solvent_flush', models.TextField(blank=True, db_column='Solvent Flush')),
                ('soap_flush', models.TextField(blank=True, db_column='Soap Flush')),
                ('oil_flush', models.TextField(blank=True, db_column='Oil Flush')),
                ('polish_flush', models.TextField(blank=True, db_column='Polish Flush')),
                ('package_retain', models.TextField(blank=True, db_column='Package Retain')),
                ('uv_protect', models.TextField(blank=True, db_column='UV  Protection')),
                ('freeze_protect', models.TextField(blank=True, db_column='Freeze Protection')),
                ('min_weight', models.TextField(blank=True, db_column='Min Weight (N)')),
                ('target_weight', models.TextField(blank=True, db_column='TARGET WEIGHT (N)')),
                ('max_weight', models.TextField(blank=True, db_column='Max Weight (N)')),
                ('upc', models.TextField(blank=True, db_column='New UPC')),
                ('scc', models.TextField(blank=True, db_column='SCC')),
                ('us_dot', models.TextField(blank=True, db_column='US - DOT')),
                ('special_notes', models.TextField(blank=True, db_column='Special Notes')),
                ('eu_case_marking', models.TextField(blank=True, db_column='Europe HAZ')),
                ('haz_symbols', models.TextField(blank=True, db_column='Haz Symbols')),
                ('pallet_footprint', models.TextField(blank=True, db_column='Current Footprint')),
                ('notes', models.TextField(blank=True, db_column='Notes')),
            ],
            options={
                'db_table': 'specsheet_data',
                'managed': False,
            },
        ),
        migrations.CreateModel(
            name='SpecSheetLabels',
            fields=[
                ('item_code', models.TextField(db_column='ItemCode', primary_key=True, serialize=False)),
                ('description', models.TextField(blank=True, db_column='Description')),
                ('weight_code', models.TextField(blank=True, db_column='Weight Code')),
                ('location', models.TextField(blank=True, db_column='Shelf')),
            ],
            options={
                'db_table': 'specsheet_labels',
                'managed': False,
            },
        ),
        migrations.CreateModel(
            name='SpecsheetState',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('item_code', models.CharField(max_length=255)),
                ('po_number', models.CharField(max_length=255)),
                ('juliandate', models.CharField(max_length=255)),
                ('state_json', models.JSONField(blank=True, null=True)),
            ],
        ),
        migrations.CreateModel(
            name='WarehouseCountRecord',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('item_code', models.TextField(blank=True, null=True)),
                ('item_description', models.TextField(blank=True, null=True)),
                ('expected_quantity', models.DecimalField(blank=True, decimal_places=5, max_digits=50, null=True)),
                ('counted_quantity', models.DecimalField(blank=True, decimal_places=5, max_digits=50, null=True)),
                ('sage_converted_quantity', models.DecimalField(blank=True, decimal_places=5, max_digits=50, null=True)),
                ('counted_date', models.DateField(blank=True, null=True)),
                ('variance', models.DecimalField(blank=True, decimal_places=5, max_digits=50, null=True)),
                ('counted', models.BooleanField(default=False)),
                ('count_type', models.TextField(blank=True, null=True)),
                ('collection_id', models.TextField(blank=True, null=True)),
                ('counted_by', models.TextField(blank=True, null=True)),
                ('comment', models.TextField(blank=True, null=True)),
                ('containers', models.JSONField(blank=True, default=list, null=True)),
            ],
        ),
        migrations.AddConstraint(
            model_name='specsheetstate',
            constraint=models.UniqueConstraint(fields=('item_code', 'po_number', 'juliandate'), name='unique_specsheet_state'),
        ),
    ]
