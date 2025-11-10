from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0002_manualgauge'),
    ]

    operations = [
        migrations.CreateModel(
            name='FunctionToggle',
            fields=[
                ('function_name', models.CharField(max_length=255, primary_key=True, serialize=False)),
                ('status', models.CharField(choices=[('on', 'On'), ('off', 'Off')], default='on', max_length=8)),
            ],
        ),
    ]
