# -*- coding: utf-8 -*-
import datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models


class Migration(SchemaMigration):

    def forwards(self, orm):
        # Adding field 'Event.expiration_time'
        db.add_column('narrative_event', 'expiration_time',
                      self.gf('django.db.models.fields.DateTimeField')(default=None, null=True, blank=True),
                      keep_default=False)


    def backwards(self, orm):
        # Deleting field 'Event.expiration_time'
        db.delete_column('narrative_event', 'expiration_time')


    models = {
        'contenttypes.contenttype': {
            'Meta': {'ordering': "('name',)", 'unique_together': "(('app_label', 'model'),)", 'object_name': 'ContentType', 'db_table': "'django_content_type'"},
            'app_label': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'model': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '100'})
        },
        'narrative.assertionmeta': {
            'Meta': {'object_name': 'AssertionMeta'},
            'assertion_load_path': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '64'}),
            'check_interval_seconds': ('django.db.models.fields.IntegerField', [], {'default': '3600'}),
            'display_name': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '64'}),
            'enabled': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'last_check': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime(1970, 1, 1, 0, 0)'})
        },
        'narrative.event': {
            'Meta': {'object_name': 'Event'},
            'event_name': ('django.db.models.fields.CharField', [], {'max_length': '64'}),
            'event_operand': ('django.db.models.fields.CharField', [], {'max_length': '64', 'null': 'True', 'blank': 'True'}),
            'event_operand_detail': ('django.db.models.fields.CharField', [], {'max_length': '64', 'null': 'True', 'blank': 'True'}),
            'expiration_time': ('django.db.models.fields.DateTimeField', [], {'default': 'None', 'null': 'True', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'origin': ('django.db.models.fields.CharField', [], {'max_length': '64'}),
            'status': ('django.db.models.fields.IntegerField', [], {'default': '0'}),
            'thread_id': ('django.db.models.fields.CharField', [], {'max_length': '36', 'null': 'True', 'blank': 'True'}),
            'timestamp': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'})
        },
        'narrative.issue': {
            'Meta': {'object_name': 'Issue'},
            'created_timestamp': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'failed_assertion': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['narrative.AssertionMeta']"}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'resolved_timestamp': ('django.db.models.fields.DateTimeField', [], {'null': 'True', 'blank': 'True'}),
            'status': ('django.db.models.fields.IntegerField', [], {'default': '0'})
        },
        'narrative.modelissue': {
            'Meta': {'object_name': 'ModelIssue', '_ormbases': ['narrative.Issue']},
            'issue_ptr': ('django.db.models.fields.related.OneToOneField', [], {'to': "orm['narrative.Issue']", 'unique': 'True', 'primary_key': 'True'}),
            'model_id': ('django.db.models.fields.PositiveIntegerField', [], {}),
            'model_type': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['contenttypes.ContentType']"})
        },
        'narrative.resolutionstep': {
            'Meta': {'object_name': 'ResolutionStep'},
            'action_type': ('django.db.models.fields.IntegerField', [], {'default': '0'}),
            'created': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'issue': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['narrative.Issue']"}),
            'solution': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['narrative.Solution']", 'null': 'True', 'blank': 'True'})
        },
        'narrative.solution': {
            'Meta': {'object_name': 'Solution'},
            'diagnostic_case_name': ('django.db.models.fields.CharField', [], {'max_length': '64'}),
            'enacted': ('django.db.models.fields.DateTimeField', [], {'null': 'True', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'plan_json': ('django.db.models.fields.TextField', [], {}),
            'problem_description': ('django.db.models.fields.CharField', [], {'max_length': '128'})
        }
    }

    complete_apps = ['narrative']