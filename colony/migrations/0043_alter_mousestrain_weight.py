# Generated by Django 4.0.4 on 2022-05-06 15:28

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('colony', '0042_alter_historicalmouse_notes_and_more'),
    ]

    operations = [
        migrations.AlterField(
            model_name='mousestrain',
            name='weight',
            field=models.IntegerField(default=1, help_text='the relative weight of this strain in this mouse'),
        ),
    ]
