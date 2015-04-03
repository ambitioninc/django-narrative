# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations
import datetime


class Migration(migrations.Migration):

    dependencies = [
        ('contenttypes', '0001_initial'),
    ]

    operations = [
        migrations.CreateModel(
            name='AssertionMeta',
            fields=[
                ('id', models.AutoField(primary_key=True, serialize=False, auto_created=True, verbose_name='ID')),
                ('display_name', models.CharField(max_length=64)),
                ('class_load_path', models.CharField(max_length=96, default='')),
                ('enabled', models.BooleanField(default=False)),
                ('check_interval_seconds', models.IntegerField(default=3600)),
                ('last_check', models.DateTimeField(default=datetime.datetime(1970, 1, 1, 0, 0))),
                ('args_json', models.TextField(blank=True, default='{}', help_text='JSON encoded named arguments')),
            ],
            options={
                'abstract': False,
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='Datum',
            fields=[
                ('id', models.AutoField(primary_key=True, serialize=False, auto_created=True, verbose_name='ID')),
                ('timestamp', models.DateTimeField(db_index=True, auto_now_add=True)),
                ('expiration_time', models.DateTimeField(null=True, blank=True, default=None)),
                ('origin', models.CharField(max_length=64)),
                ('datum_name', models.CharField(max_length=64)),
                ('datum_note_json', models.TextField(null=True, blank=True, default=None)),
                ('thread_id', models.CharField(null=True, blank=True, max_length=36)),
                ('log_level', models.IntegerField(choices=[(0, 'Trace'), (4, 'Error'), (3, 'Warn'), (2, 'Info'), (1, 'Debug')], default=2)),
            ],
            options={
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='EventMeta',
            fields=[
                ('id', models.AutoField(primary_key=True, serialize=False, auto_created=True, verbose_name='ID')),
                ('display_name', models.CharField(max_length=64)),
                ('class_load_path', models.CharField(max_length=96, default='')),
                ('enabled', models.BooleanField(default=False)),
                ('check_interval_seconds', models.IntegerField(default=3600)),
                ('last_check', models.DateTimeField(default=datetime.datetime(1970, 1, 1, 0, 0))),
                ('args_json', models.TextField(blank=True, default='{}', help_text='JSON encoded named arguments')),
            ],
            options={
                'abstract': False,
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='Issue',
            fields=[
                ('id', models.AutoField(primary_key=True, serialize=False, auto_created=True, verbose_name='ID')),
                ('status', models.IntegerField(choices=[(0, 'Open'), (1, 'Solution Applied'), (2, 'Impasse'), (3, 'Resolved'), (4, 'Wont Fix')], default=0)),
                ('created_timestamp', models.DateTimeField(auto_now_add=True)),
                ('resolved_timestamp', models.DateTimeField(null=True, blank=True)),
            ],
            options={
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='ModelIssue',
            fields=[
                ('issue_ptr', models.OneToOneField(serialize=False, primary_key=True, parent_link=True, to='narrative.Issue', auto_created=True)),
                ('model_id', models.PositiveIntegerField()),
                ('model_type', models.ForeignKey(to='contenttypes.ContentType')),
            ],
            options={
            },
            bases=('narrative.issue',),
        ),
        migrations.CreateModel(
            name='NarrativeConfig',
            fields=[
                ('id', models.AutoField(primary_key=True, serialize=False, auto_created=True, verbose_name='ID')),
                ('minimum_datum_log_level', models.IntegerField(choices=[(0, 'Trace'), (4, 'Error'), (3, 'Warn'), (2, 'Info'), (1, 'Debug')], default=2)),
            ],
            options={
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='ResolutionStep',
            fields=[
                ('id', models.AutoField(primary_key=True, serialize=False, auto_created=True, verbose_name='ID')),
                ('action_type', models.IntegerField(choices=[(0, 'Exec'), (1, 'Pass')], default=0)),
                ('created', models.DateTimeField(auto_now_add=True)),
                ('reason', models.CharField(null=True, max_length=64, blank=True, default=None)),
                ('issue', models.ForeignKey(to='narrative.Issue')),
            ],
            options={
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='Solution',
            fields=[
                ('id', models.AutoField(primary_key=True, serialize=False, auto_created=True, verbose_name='ID')),
                ('diagnostic_case_name', models.CharField(max_length=64)),
                ('problem_description', models.CharField(max_length=128)),
                ('plan_json', models.TextField()),
                ('enacted', models.DateTimeField(null=True, blank=True)),
                ('error_traceback', models.TextField(null=True, blank=True)),
            ],
            options={
            },
            bases=(models.Model,),
        ),
        migrations.AddField(
            model_name='resolutionstep',
            name='solution',
            field=models.ForeignKey(blank=True, null=True, to='narrative.Solution'),
            preserve_default=True,
        ),
        migrations.AddField(
            model_name='issue',
            name='failed_assertion',
            field=models.ForeignKey(to='narrative.AssertionMeta'),
            preserve_default=True,
        ),
        migrations.AlterUniqueTogether(
            name='eventmeta',
            unique_together=set([('display_name', 'class_load_path')]),
        ),
        migrations.AlterUniqueTogether(
            name='assertionmeta',
            unique_together=set([('display_name', 'class_load_path')]),
        ),
    ]
