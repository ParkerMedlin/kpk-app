from decimal import Decimal
from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('core', '0001_initial'),
    ]

    operations = [
        migrations.CreateModel(
            name='FlushToteReading',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('date', models.DateTimeField(auto_now_add=True, db_index=True)),
                ('production_line', models.CharField(choices=[('JB Line', 'JB Line'), ('INLINE', 'INLINE'), ('PD Line', 'PD Line')], max_length=20)),
                ('flush_type', models.CharField(max_length=100)),
                ('initial_pH', models.DecimalField(blank=True, decimal_places=2, max_digits=4, null=True)),
                ('action_required', models.TextField(blank=True, null=True)),
                ('final_pH', models.DecimalField(blank=True, decimal_places=2, max_digits=4, null=True)),
                ('approval_status', models.CharField(choices=[('pending', 'Pending'), ('needs_action', 'Needs Action'), ('approved', 'Approved')], default='pending', max_length=20)),
                ('lab_technician', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='flush_totes_lab', to=settings.AUTH_USER_MODEL)),
                ('line_personnel', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='flush_totes_line', to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'db_table': 'core_flush_tote_reading',
                'ordering': ['-date', '-id'],
                'indexes': [models.Index(fields=['production_line'], name='core_flush__product_45c6a3_idx'), models.Index(fields=['approval_status'], name='core_flush__approval_d19ec3_idx')],
                'constraints': [models.CheckConstraint(check=models.Q(('final_pH__isnull', True)) | (models.Q(('final_pH__gte', Decimal('5.10'))) & models.Q(('final_pH__lte', Decimal('10.90')))), name='flush_tote_final_ph_range')],
            },
        ),
    ]
