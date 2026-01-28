from decimal import Decimal
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0001_initial'),
    ]

    operations = [
        migrations.CreateModel(
            name='DischargeTestingRecord',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('date', models.DateTimeField(auto_now_add=True, db_index=True)),
                ('discharge_source', models.CharField(choices=[('JB Line', 'JB Line'), ('INLINE', 'INLINE'), ('PD Line', 'PD Line'), ('Warehouse', 'Warehouse')], max_length=20)),
                ('flush_type', models.CharField(max_length=100)),
                ('initial_pH', models.DecimalField(blank=True, decimal_places=2, max_digits=4, null=True)),
                ('action_required', models.TextField(blank=True, null=True)),
                ('final_pH', models.DecimalField(blank=True, decimal_places=2, max_digits=4, null=True)),
                ('final_disposition', models.TextField()),
            ],
            options={
                'db_table': 'core_dischargetestingrecord',
                'ordering': ['-date', '-id'],
            },
        ),
        migrations.AddIndex(
            model_name='dischargetestingrecord',
            index=models.Index(fields=['discharge_source'], name='core_discha_dischar_8759bd_idx'),
        ),
        migrations.AddConstraint(
            model_name='dischargetestingrecord',
            constraint=models.CheckConstraint(check=models.Q(('final_pH__isnull', True), models.Q(('final_pH__gte', Decimal('5.10')), ('final_pH__lte', Decimal('10.90'))), _connector='OR'), name='discharge_testing_final_ph_range'),
        ),
    ]
