# -*- coding: utf-8 -*-
# Adapted from code generated by Django 1.10.3 on 2017-01-03 10:43
from __future__ import unicode_literals

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('publications', '0002_initial_data'),
    ]

    operations = [
        migrations.AlterModelOptions(
            name='publication',
            options={'ordering': ['-year', '-month', '-id']},
        ),
    ]
