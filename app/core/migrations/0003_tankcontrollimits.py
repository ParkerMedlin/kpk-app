# Generated manually for TankControlLimits model
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0002_desklaborrate'),
    ]

    operations = [
        migrations.CreateModel(
            name='TankControlLimits',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('tank_name', models.TextField(db_index=True)),
                ('calculated_at', models.DateTimeField(auto_now_add=True)),
                ('lookback_days', models.IntegerField(default=60, help_text='Days of historical data used')),
                ('n_samples', models.IntegerField(help_text='Number of hourly samples used in calculation')),
                ('avg_change', models.DecimalField(decimal_places=4, max_digits=12, help_text='Average hourly change in gallons during non-op hours')),
                ('avg_moving_range', models.DecimalField(decimal_places=4, max_digits=12, help_text='Average moving range (volatility measure)')),
                ('upper_control_limit', models.DecimalField(decimal_places=4, max_digits=12, help_text='UCL = avg_change + 2.66 * avg_mr')),
                ('lower_control_limit', models.DecimalField(decimal_places=4, max_digits=12, help_text='LCL = avg_change - 2.66 * avg_mr (leak threshold)')),
            ],
            options={
                'verbose_name': 'Tank Control Limit',
                'verbose_name_plural': 'Tank Control Limits',
                'ordering': ['-calculated_at'],
            },
        ),
        migrations.AddIndex(
            model_name='tankcontrollimits',
            index=models.Index(fields=['tank_name', '-calculated_at'], name='core_tankco_tank_na_4c6a77_idx'),
        ),
    ]
