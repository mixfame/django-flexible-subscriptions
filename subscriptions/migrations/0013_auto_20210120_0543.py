# Generated by Django 3.1.5 on 2021-01-20 05:43

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('subscriptions', '0012_subscriptiontransaction_transaction_type'),
    ]

    operations = [
        migrations.AlterField(
            model_name='subscriptiontransaction',
            name='transaction_type',
            field=models.CharField(choices=[('P', 'Payment'), ('R', 'Refund')], default='P', max_length=2),
        ),
    ]
