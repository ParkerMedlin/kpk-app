# Generated by Django 3.2.15 on 2022-08-22 15:58

from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
    ]

    operations = [
        migrations.CreateModel(
            name='IssueSheetNeeded',
            fields=[
                ('id', models.IntegerField(primary_key=True, serialize=False)),
                ('id2', models.DecimalField(blank=True, decimal_places=1, max_digits=50, null=True)),
                ('bill_pn', models.TextField(blank=True, null=True)),
                ('blend_pn', models.TextField(blank=True, null=True)),
                ('blend_desc', models.TextField(blank=True, null=True)),
                ('adjustedrunqty', models.DecimalField(blank=True, decimal_places=5, max_digits=50, null=True)),
                ('qtyonhand', models.DecimalField(blank=True, decimal_places=5, max_digits=50, null=True)),
                ('starttime', models.DecimalField(blank=True, decimal_places=7, max_digits=50, null=True)),
                ('prodline', models.TextField(blank=True, null=True)),
                ('oh_after_run', models.DecimalField(blank=True, decimal_places=5, max_digits=50, null=True)),
                ('week_calc', models.DecimalField(blank=True, decimal_places=1, max_digits=50, null=True)),
                ('batchnum1', models.TextField(blank=True, null=True)),
                ('batchqty1', models.TextField(blank=True, null=True)),
                ('batchnum2', models.TextField(blank=True, null=True)),
                ('batchqty2', models.TextField(blank=True, null=True)),
                ('batchnum3', models.TextField(blank=True, null=True)),
                ('batchqty3', models.TextField(blank=True, null=True)),
                ('batchnum4', models.TextField(blank=True, null=True)),
                ('batchqty4', models.TextField(blank=True, null=True)),
                ('batchnum5', models.TextField(blank=True, null=True)),
                ('batchqty5', models.TextField(blank=True, null=True)),
                ('batchnum6', models.TextField(blank=True, null=True)),
                ('batchqty6', models.TextField(blank=True, null=True)),
                ('uniqchek', models.TextField(blank=True, null=True)),
            ],
            options={
                'db_table': 'issue_sheet_needed',
                'managed': False,
            },
        ),
    ]