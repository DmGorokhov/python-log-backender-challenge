# Generated by Django 5.1.2 on 2025-02-15 11:25

import django.utils.timezone
from django.db import migrations, models

import core.core_enums


class Migration(migrations.Migration):
    initial = True

    dependencies = [
    ]

    operations = [
        migrations.CreateModel(
            name='EventsLogOutBox',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('created_at', models.DateTimeField(db_index=True, default=django.utils.timezone.now)),
                ('updated_at', models.DateTimeField(auto_now=True, db_index=True)),
                ('event_type', models.CharField(max_length=255)),
                ('event_date_time', models.DateTimeField()),
                ('environment', models.CharField(max_length=255)),
                ('event_context', models.TextField()),
                ('send_status', models.CharField(
                    choices=[
                        (core.core_enums.EvenLogStatus['AWAITING_DELIVER'], 'AWAITING_DELIVER'),
                        (core.core_enums.EvenLogStatus['SENDING'], 'SENDING'),
                        (core.core_enums.EvenLogStatus['DELIVERED'], 'DELIVERED'),
                        (core.core_enums.EvenLogStatus['DELIVERY_FAILED'], 'DELIVERY_FAILED')],
                    default=core.core_enums.EvenLogStatus['AWAITING_DELIVER'],
                    help_text='Event delivery state', max_length=50)),
            ],
            options={
                'abstract': False,
            },
        ),
    ]
