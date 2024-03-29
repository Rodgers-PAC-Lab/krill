# CR: resolving merge conflict here, which affects only these dates
# Generated by Django 4.0.4 on 2022-05-06 16:30
# Generated by Django 4.0.4 on 2022-10-25 19:24

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('colony', '0043_alter_mousestrain_weight'),
    ]

    operations = [
        migrations.AddField(
            model_name='historicalmouse',
            name='tail_sharpie',
            field=models.CharField(blank=True, help_text='(optional) sharpie markings on tail', max_length=20),
        ),
        migrations.AddField(
            model_name='historicalmouse',
            name='tail_tattoo',
            field=models.CharField(blank=True, help_text='(optional) 3-character tail tattoo', max_length=10),
        ),
        migrations.AddField(
            model_name='mouse',
            name='tail_sharpie',
            field=models.CharField(blank=True, help_text='(optional) sharpie markings on tail', max_length=20),
        ),
        migrations.AddField(
            model_name='mouse',
            name='tail_tattoo',
            field=models.CharField(blank=True, help_text='(optional) 3-character tail tattoo', max_length=10),
        ),
    ]
