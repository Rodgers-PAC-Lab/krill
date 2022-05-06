# Generated by Django 4.0.4 on 2022-05-04 01:17

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('colony', '0037_cage_dar_req_num_historicalcage_dar_req_num_and_more'),
    ]

    operations = [
        migrations.AlterField(
            model_name='cage',
            name='dar_id',
            field=models.CharField(blank=True, help_text='the long number under the barcode', max_length=100, verbose_name='DAR ID number'),
        ),
        migrations.AlterField(
            model_name='cage',
            name='dar_req_num',
            field=models.CharField(blank=True, help_text='(for purchased only) the DAR requisition number', max_length=100, verbose_name='DAR requisition number'),
        ),
        migrations.AlterField(
            model_name='historicalcage',
            name='dar_id',
            field=models.CharField(blank=True, help_text='the long number under the barcode', max_length=100, verbose_name='DAR ID number'),
        ),
        migrations.AlterField(
            model_name='historicalcage',
            name='dar_req_num',
            field=models.CharField(blank=True, help_text='(for purchased only) the DAR requisition number', max_length=100, verbose_name='DAR requisition number'),
        ),
    ]