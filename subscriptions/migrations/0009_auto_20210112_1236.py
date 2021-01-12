# Generated by Django 3.1.5 on 2021-01-12 12:36

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('subscriptions', '0008_auto_20210112_1037'),
    ]

    operations = [
        migrations.AlterField(
            model_name='paymentcurrency',
            name='positive_sign',
            field=models.CharField(default='', help_text='The symbol to use for the positive sign.', max_length=1, null=True),
        ),
    ]
