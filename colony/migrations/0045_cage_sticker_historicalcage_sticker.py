# Generated by Django 4.0.4 on 2022-10-25 19:25

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('colony', '0044_historicalmouse_tail_sharpie_and_more'),
    ]

    operations = [
        migrations.AddField(
            model_name='cage',
            name='sticker',
            field=models.CharField(blank=True, help_text='sticker that is on the cage card', max_length=100),
        ),
        migrations.AddField(
            model_name='historicalcage',
            name='sticker',
            field=models.CharField(blank=True, help_text='sticker that is on the cage card', max_length=100),
        ),
    ]
