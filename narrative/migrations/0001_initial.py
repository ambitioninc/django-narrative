# -*- coding: utf-8 -*-
import datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models


class Migration(SchemaMigration):

    def forwards(self, orm):
        # Adding model 'Event'
        db.create_table('narrative_event', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('timestamp', self.gf('django.db.models.fields.DateTimeField')(auto_now_add=True, blank=True)),
            ('origin', self.gf('django.db.models.fields.CharField')(max_length=64)),
            ('event_name', self.gf('django.db.models.fields.CharField')(max_length=64)),
            ('event_operand', self.gf('django.db.models.fields.CharField')(max_length=64, null=True, blank=True)),
            ('event_operand_detail', self.gf('django.db.models.fields.CharField')(max_length=64, null=True, blank=True)),
            ('status', self.gf('django.db.models.fields.IntegerField')(default=0)),
            ('thread_id', self.gf('django.db.models.fields.CharField')(max_length=36, null=True, blank=True)),
        ))
        db.send_create_signal('narrative', ['Event'])

        # Adding model 'AssertionMeta'
        db.create_table('narrative_assertionmeta', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('display_name', self.gf('django.db.models.fields.CharField')(unique=True, max_length=64)),
            ('assertion_load_path', self.gf('django.db.models.fields.CharField')(unique=True, max_length=64)),
            ('enabled', self.gf('django.db.models.fields.BooleanField')(default=False)),
        ))
        db.send_create_signal('narrative', ['AssertionMeta'])

        # Adding model 'Solution'
        db.create_table('narrative_solution', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('diagnostic_case_name', self.gf('django.db.models.fields.CharField')(max_length=64)),
            ('problem_description', self.gf('django.db.models.fields.CharField')(max_length=128)),
            ('plan_json', self.gf('django.db.models.fields.TextField')()),
            ('enacted', self.gf('django.db.models.fields.DateTimeField')(null=True, blank=True)),
        ))
        db.send_create_signal('narrative', ['Solution'])

        # Adding model 'Issue'
        db.create_table('narrative_issue', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('failed_assertion', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['narrative.AssertionMeta'])),
            ('status', self.gf('django.db.models.fields.IntegerField')(default=0)),
            ('created_timestamp', self.gf('django.db.models.fields.DateTimeField')(auto_now_add=True, blank=True)),
            ('resolved_timestamp', self.gf('django.db.models.fields.DateTimeField')(null=True, blank=True)),
        ))
        db.send_create_signal('narrative', ['Issue'])

        # Adding model 'ResolutionStep'
        db.create_table('narrative_resolutionstep', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('issue', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['narrative.Issue'])),
            ('solution', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['narrative.Solution'], null=True, blank=True)),
            ('action_type', self.gf('django.db.models.fields.IntegerField')(default=0)),
            ('created', self.gf('django.db.models.fields.DateTimeField')(auto_now_add=True, blank=True)),
        ))
        db.send_create_signal('narrative', ['ResolutionStep'])

        # Adding model 'ModelIssue'
        db.create_table('narrative_modelissue', (
            ('issue_ptr', self.gf('django.db.models.fields.related.OneToOneField')(to=orm['narrative.Issue'], unique=True, primary_key=True)),
            ('model_type', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['contenttypes.ContentType'])),
            ('model_id', self.gf('django.db.models.fields.PositiveIntegerField')()),
        ))
        db.send_create_signal('narrative', ['ModelIssue'])


    def backwards(self, orm):
        # Deleting model 'Event'
        db.delete_table('narrative_event')

        # Deleting model 'AssertionMeta'
        db.delete_table('narrative_assertionmeta')

        # Deleting model 'Solution'
        db.delete_table('narrative_solution')

        # Deleting model 'Issue'
        db.delete_table('narrative_issue')

        # Deleting model 'ResolutionStep'
        db.delete_table('narrative_resolutionstep')

        # Deleting model 'ModelIssue'
        db.delete_table('narrative_modelissue')


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
            'display_name': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '64'}),
            'enabled': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'})
        },
        'narrative.event': {
            'Meta': {'object_name': 'Event'},
            'event_name': ('django.db.models.fields.CharField', [], {'max_length': '64'}),
            'event_operand': ('django.db.models.fields.CharField', [], {'max_length': '64', 'null': 'True', 'blank': 'True'}),
            'event_operand_detail': ('django.db.models.fields.CharField', [], {'max_length': '64', 'null': 'True', 'blank': 'True'}),
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