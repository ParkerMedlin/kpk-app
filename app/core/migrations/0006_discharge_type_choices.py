from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ('core', '0005_rename_flush_type'),
    ]

    operations = [
        migrations.AlterField(
            model_name='dischargetestingrecord',
            name='discharge_type',
            field=models.CharField(
                choices=[
                    ('Acid', 'Acid'),
                    ('Base', 'Base'),
                    ('Soap', 'Soap'),
                    ('Polish', 'Polish'),
                    ('Oil', 'Oil'),
                ],
                max_length=100,
            ),
        ),
    ]
