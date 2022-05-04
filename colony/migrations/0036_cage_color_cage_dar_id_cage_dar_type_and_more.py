# Generated by Django 4.0.4 on 2022-05-04 00:49

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('colony', '0035_strain_and_more'),
    ]

    operations = [
        migrations.AddField(
            model_name='cage',
            name='color',
            field=models.CharField(blank=True, max_length=20),
        ),
        migrations.AddField(
            model_name='cage',
            name='dar_id',
            field=models.CharField(blank=True, max_length=100),
        ),
        migrations.AddField(
            model_name='cage',
            name='dar_type',
            field=models.IntegerField(choices=[(0, 'other'), (1, 'separation'), (2, 'weaning')], default=0),
        ),
        migrations.AddField(
            model_name='historicalcage',
            name='color',
            field=models.CharField(blank=True, max_length=20),
        ),
        migrations.AddField(
            model_name='historicalcage',
            name='dar_id',
            field=models.CharField(blank=True, max_length=100),
        ),
        migrations.AddField(
            model_name='historicalcage',
            name='dar_type',
            field=models.IntegerField(choices=[(0, 'other'), (1, 'separation'), (2, 'weaning')], default=0),
        ),
        migrations.AlterField(
            model_name='cage',
            name='notes',
            field=models.CharField(blank=True, default='', max_length=100),
            preserve_default=False,
        ),
        migrations.AlterField(
            model_name='historicalcage',
            name='notes',
            field=models.CharField(blank=True, default='', max_length=100),
            preserve_default=False,
        ),
    ]
