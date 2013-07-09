import json
import uuid

from pytz import utc as utc_tz

from django.contrib.contenttypes.models import ContentType
from django.contrib.contenttypes import generic
from django.db import models


def find_tuple(tuple_list, key, which):
    return filter(lambda tple: tple[which] == key, tuple_list)[0]


class StatusType(object):
    types = []

    @classmethod
    def status_by_id(cls, id_):
        return find_tuple(cls.types, id_, 0)[1]


class EventStatusType(StatusType):
    Success = 0
    Failed = 1
    InProgress = 2

    types = (
        (Success, 'Success'),
        (Failed, 'Failed'),
        (InProgress, 'InProgress'),
    )


class IssueStatusType(StatusType):
    # An open problem; we've not tried to fix it yet
    Open = 0

    # We've applied a solution and are waiting to see if it
    # fixes things.
    SolutionApplied = 1

    # At an impasse; don't know how to proceed, so we've
    # contacted some humans to take a lok
    Impasse = 2

    # The issue is fixed and the Issue has been closed
    Resolved = 3

    types = (
        (Open, 'Open'),
        (SolutionApplied, 'Solution Applied'),
        (Impasse, 'Impasse'),
        (Resolved, 'Resolved'),
    )


class Event(models.Model):
    # When did the event occur
    timestamp = models.DateTimeField(auto_now_add=True)

    # Origin of this event; ie, what piece of software created it
    origin = models.CharField(max_length=64)

    # What event happened; ie, an attempt to connect to a database
    event_name = models.CharField(max_length=64)

    # Target of the event; ie, what database did the connection involve
    event_operand = models.CharField(max_length=64, null=True, blank=True)

    # Additional information about the event_operand; ie, what error happened
    event_operand_detail = models.CharField(max_length=64, null=True, blank=True)

    # Event status
    status = models.IntegerField(choices=EventStatusType.types, default=EventStatusType.Success)

    # An ID to tie particular events together
    thread_id = models.CharField(max_length=36, null=True, blank=True)

    @property
    def timestamp_with_tz(self):
        return utc_tz.localize(self.timestamp)

    def save(self, *args, **kwargs):
        if None == self.thread_id:
            self.thread_id = str(uuid.uuid4())

        super(Event, self).save(*args, **kwargs)

    def __unicode__(self):
        return u'origin:{0} event_name:{1} event_operand:{2} event_operand_detail:{3}'.format(
            self.origin, self.event_name, self.event_operand, self.event_operand_detail)


def log_event(status_name, origin, event_name, event_operand=None, thread_id=None):
    evt = Event(
        origin=origin, event_name=event_name, event_operand=event_operand,
        status=EventStatusType.status_by_name(status_name), thread_id=thread_id)

    evt.save()

    return evt


class Solution(models.Model):
    def __init__(self, *args, **kwargs):
        self.plan = kwargs.pop('plan', [])
        self.save_plan()

        super(Solution, self).__init__(*args, **kwargs)

    issue = models.ForeignKey('Issue')

    # What was the name of the diagnostic method that generated this solution?
    diagnostic_case_name = models.CharField(max_length=64)

    # Description of the problem this solution addresses
    problem_description = models.CharField(max_length=128)

    # The steps (stored as json) for this solution
    plan_json = models.TextField()

    # Time in which the solution was enacted
    enacted = models.DateTimeField(null=True, blank=True)

    def load_plan(self):
        self.plan = json.loads(self.plan_json)

    def save_plan(self):
        self.plan_json = json.dumps(self.plan)


class AssertionMeta(models.Model):
    """
    Used for storing meta information about a specific assertion.
    """
    # Display name for humans
    display_name = models.CharField(max_length=64, unique=True)

    # Python import path to the Assertion class
    assertion_load_path = models.CharField(max_length=64, unique=True)

    # Determines if this assertion should ever be checked
    enabled = models.BooleanField(default=False)

    def load_assertion_class(self):
        """
        Imports and returns the Assertion module.
        """
        assertion_path = '.'.join(self.assertion_load_path.split('.')[:-1])
        assertion_class_name = self.assertion_load_path.split('.')[-1]
        assertion_file_name = self.assertion_load_path.split('.')[-2]

        assertion_module = __import__(assertion_path, globals(), locals(), [assertion_file_name])
        if not assertion_module or not hasattr(assertion_module, assertion_class_name):
            return None

        loaded_assertion_class = getattr(assertion_module, assertion_class_name)
        if not loaded_assertion_class:
            return None

        return loaded_assertion_class

    def __unicode__(self):
        return u'{0}::{1}'.format(self.display_name, self.assertion_load_path)


class Issue(models.Model):
    """
    Assertions can find problems in the system; these
    problems are represented using issues.
    """
    # Which failing assertion generated this Issue
    failed_assertion = models.ForeignKey(AssertionMeta)

    # Status can be open, resolved, etc
    status = models.IntegerField(choices=IssueStatusType.types, default=IssueStatusType.Open)

    created_timestamp = models.DateTimeField(auto_now_add=True)
    resolved_timestamp = models.DateTimeField(null=True, blank=True)

    def __unicode__(self):
        return u'Issue:{0}'.format(self.failed_assertion.display_name)


class ModelIssue(Issue):
    """
    Model assertions may find issues with particular models.
    This is used to track such an issue.
    """
    model_type = models.ForeignKey(ContentType)
    model_id = models.PositiveIntegerField()
    model = generic.GenericForeignKey('model_type', 'model_id')
