from django.db import migrations


class Migration(migrations.Migration):
    dependencies = [
        ('core', '0003_dischargetestingrecord_user_fields'),
    ]

    operations = [
        migrations.RenameField(
            model_name='dischargetestingrecord',
            old_name='line_personnel',
            new_name='sampling_personnel',
        ),
    ]
