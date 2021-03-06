# Generated by Django 4.0.4 on 2022-05-04 01:15

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('colony', '0036_cage_color_cage_dar_id_cage_dar_type_and_more'),
    ]

    operations = [
        migrations.AddField(
            model_name='cage',
            name='dar_req_num',
            field=models.CharField(blank=True, help_text='(for purchased only) the DAR requisition number', max_length=100),
        ),
        migrations.AddField(
            model_name='historicalcage',
            name='dar_req_num',
            field=models.CharField(blank=True, help_text='(for purchased only) the DAR requisition number', max_length=100),
        ),
        migrations.AlterField(
            model_name='cage',
            name='color',
            field=models.CharField(blank=True, help_text='color of the cage card', max_length=20),
        ),
        migrations.AlterField(
            model_name='cage',
            name='dar_id',
            field=models.CharField(blank=True, help_text='the long number under the barcode', max_length=100),
        ),
        migrations.AlterField(
            model_name='cage',
            name='dar_type',
            field=models.IntegerField(choices=[(0, 'unknown (must specify)'), (1, 'separation'), (2, 'weaning'), (3, 'ordered/imported')], default=0),
        ),
        migrations.AlterField(
            model_name='cage',
            name='rack_spot',
            field=models.CharField(blank=True, help_text='location within the rack', max_length=10),
        ),
        migrations.AlterField(
            model_name='historicalcage',
            name='color',
            field=models.CharField(blank=True, help_text='color of the cage card', max_length=20),
        ),
        migrations.AlterField(
            model_name='historicalcage',
            name='dar_id',
            field=models.CharField(blank=True, help_text='the long number under the barcode', max_length=100),
        ),
        migrations.AlterField(
            model_name='historicalcage',
            name='dar_type',
            field=models.IntegerField(choices=[(0, 'unknown (must specify)'), (1, 'separation'), (2, 'weaning'), (3, 'ordered/imported')], default=0),
        ),
        migrations.AlterField(
            model_name='historicalcage',
            name='rack_spot',
            field=models.CharField(blank=True, help_text='location within the rack', max_length=10),
        ),
    ]
