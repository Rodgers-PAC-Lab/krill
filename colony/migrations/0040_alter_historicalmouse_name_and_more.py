# Generated by Django 4.0.4 on 2022-05-04 01:39

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('colony', '0039_alter_cage_dar_type_alter_cage_defunct_and_more'),
    ]

    operations = [
        migrations.AlterField(
            model_name='historicalmouse',
            name='name',
            field=models.CharField(db_index=True, help_text='a unique name for this mouse', max_length=25),
        ),
        migrations.AlterField(
            model_name='historicalmouse',
            name='pure_breeder',
            field=models.BooleanField(default=False, help_text='set True if purchased from JAX etc, rather than made by crossing'),
        ),
        migrations.AlterField(
            model_name='historicalmouse',
            name='pure_wild_type',
            field=models.BooleanField(default=False, help_text='set True if this is a pure wild type, as opposed to a transgenic of some kind'),
        ),
        migrations.AlterField(
            model_name='mouse',
            name='name',
            field=models.CharField(help_text='a unique name for this mouse', max_length=25, unique=True),
        ),
        migrations.AlterField(
            model_name='mouse',
            name='pure_breeder',
            field=models.BooleanField(default=False, help_text='set True if purchased from JAX etc, rather than made by crossing'),
        ),
        migrations.AlterField(
            model_name='mouse',
            name='pure_wild_type',
            field=models.BooleanField(default=False, help_text='set True if this is a pure wild type, as opposed to a transgenic of some kind'),
        ),
    ]
