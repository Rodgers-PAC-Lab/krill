# Generated by Django 3.1.13 on 2022-04-27 01:49

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('colony', '0033_auto_20191227_1349'),
    ]

    operations = [
        migrations.AlterField(
            model_name='cage',
            name='transfer_JLG',
            field=models.BooleanField(default=None, null=True),
        ),
        migrations.AlterField(
            model_name='historicalcage',
            name='transfer_JLG',
            field=models.BooleanField(default=None, null=True),
        ),
    ]
