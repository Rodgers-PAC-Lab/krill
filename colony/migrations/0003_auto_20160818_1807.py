# -*- coding: utf-8 -*-
# Generated by Django 1.9.8 on 2016-08-18 22:07
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('colony', '0002_auto_20160818_1737'),
    ]

    operations = [
        migrations.AddField(
            model_name='specialrequest',
            name='date_completed',
            field=models.DateField(blank=True, null=True, verbose_name='date completed'),
        ),
        migrations.AddField(
            model_name='specialrequest',
            name='date_requested',
            field=models.DateField(blank=True, null=True, verbose_name='date requested'),
        ),
    ]