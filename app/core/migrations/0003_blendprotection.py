# Generated by Django 3.2.21 on 2024-02-12 20:29

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0002_auto_20240207_0813'),
    ]

    operations = [
        migrations.CreateModel(
            name='BlendProtection',
            fields=[
                ('item_code', models.TextField(db_column='ItemCode', primary_key=True, serialize=False)),
                ('uv_protection', models.TextField(blank=True, db_column='UV  Protection', null=True)),
                ('freeze_protection', models.TextField(blank=True, db_column='Freeze Protection', null=True)),
            ],
            options={
                'db_table': 'blend_protection',
                'managed': False,
            },
        ),
    ]