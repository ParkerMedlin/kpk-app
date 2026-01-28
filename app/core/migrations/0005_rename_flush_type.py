from django.db import migrations


class Migration(migrations.Migration):
    dependencies = [
        ('core', '0004_rename_line_personnel'),
    ]

    operations = [
        migrations.RenameField(
            model_name='dischargetestingrecord',
            old_name='flush_type',
            new_name='discharge_type',
        ),
    ]
