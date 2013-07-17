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
    SUCCESS = 0
    FAILED = 1
    IN_PROGRESS = 2

    types = (
        (SUCCESS, 'Success'),
        (FAILED, 'Failed'),
        (IN_PROGRESS, 'InProgress'),
    )


class IssueStatusType(StatusType):
    # An open problem; we've not tried to fix it yet
    OPEN = 0

    # We've applied a solution and are waiting to see if it
    # fixes things.
    SOLUTION_APPLIED = 1

    # At an impasse; don't know how to proceed, so we've
    # contacted some humans to take a lok
    IMPASSE = 2

    # The issue is fixed and the Issue has been closed
    RESOLVED = 3

    # The issue should not be re-opened
    WONT_FIX = 4

    types = (
        (OPEN, 'Open'),
        (SOLUTION_APPLIED, 'Solution Applied'),
        (IMPASSE, 'Impasse'),
        (RESOLVED, 'Resolved'),
        (WONT_FIX, 'Wont Fix'),
    )


class ResolutionStepActionType(StatusType):
    EXEC = 0    # Perform some actions
    PASS = 1    # Pass and don't do anything right now

    types = (
        (EXEC, 'Exec'),
        (PASS, 'Pass'),
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
    status = models.IntegerField(choices=EventStatusType.types, default=EventStatusType.SUCCESS)

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


class Solution(models.Model):
    def __init__(self, *args, **kwargs):
        self.plan = kwargs.pop('plan', [])
        self.save_plan()

        super(Solution, self).__init__(*args, **kwargs)

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

    def __unicode__(self):
        return u'Solution - Diagnostic case name: {0}, description: {1}'.format(
            self.diagnostic_case_name, self.problem_description)

    def __str__(self):
        return 'Solution - Diagnostic case name: {0}, description: {1}'.format(
            self.diagnostic_case_name, self.problem_description)

    def explain(self, tabs=''):
        # Aggregate all of the plan steps into a nice human readable format
        plan_explanation = []

        for step in self.plan:
            op_name, kwargs = step
            keyword_list = ['{0}={1}'.format(k, v) for k, v in kwargs.items()]
            plan_explanation.append('{0}({1})'.format(op_name, ', '.join(keyword_list)))

        step_separator = ('\n{0}    '.format(tabs))

        plan_explanation_string = step_separator + step_separator.join(plan_explanation)

        explanation = [
            'Diagnostic case name: {0}'.format(self.diagnostic_case_name),
            'Problem Description: {0}'.format(self.problem_description),
            'Enacted: {0}'.format(self.enacted or 'Never'),
            'Plan: {0}'.format(plan_explanation_string),
        ]

        separator = '\n{0}'.format(tabs)

        return separator.join(explanation)


class Issue(models.Model):
    """
    Assertions can find problems in the system; these
    problems are represented using issues.
    """
    # Which failing assertion generated this Issue
    failed_assertion = models.ForeignKey(AssertionMeta)

    # Status can be open, resolved, etc
    status = models.IntegerField(choices=IssueStatusType.types, default=IssueStatusType.OPEN)

    created_timestamp = models.DateTimeField(auto_now_add=True)
    resolved_timestamp = models.DateTimeField(null=True, blank=True)

    def __unicode__(self):
        return u'Issue - {0} ({1})'.format(
            self.failed_assertion.display_name, IssueStatusType.status_by_id(self.status))

    def __str__(self):
        return 'Issue - {0} ({1})'.format(
            self.failed_assertion.display_name, IssueStatusType.status_by_id(self.status))

    def explain(self, tabs=''):
        resolution_separator = '\n{0}    '.format(tabs)
        resolution_steps = resolution_separator + resolution_separator.join(
            [step.explain(tabs + '    ') for step in self.resolutionstep_set.order_by('created')])

        explanation = [
            'Failed Assertion: {0}'.format(self.failed_assertion.display_name),
            'Status: {0}'.format(IssueStatusType.status_by_id(self.status)),
            'Created: {0}'.format(self.created_timestamp),
            'Resolved: {0}'.format(self.resolved_timestamp or 'Never'),
            'Resolution Steps: {0}'.format(resolution_steps),
        ]

        return '\n'.join(explanation)

    def steps_matching_solution(self, solution):
        """
        Given an Issue, return the ResolutionStep where the solution applied
        matches the provided solution.

        The match is in terms of matching operations; not neccesarily the arguments passed.
        """
        def get_step_operations(solution):
            return set(map(lambda step: step[0], solution.plan))

        target_solution_steps = get_step_operations(solution)

        matching_steps = []

        for step in self.resolutionstep_set.all():
            if step.solution:
                step.solution.load_plan()
                if get_step_operations(step.solution) == target_solution_steps:
                    matching_steps.append(step)

        return matching_steps


class ResolutionStep(models.Model):
    """
    Track steps taken to resolve an issue.
    """
    issue = models.ForeignKey(Issue)
    solution = models.ForeignKey(Solution, null=True, blank=True)

    action_type = models.IntegerField(
        choices=ResolutionStepActionType.types, default=ResolutionStepActionType.EXEC)

    created = models.DateTimeField(auto_now_add=True)

    def __unicode__(self):
        return u'Action: {0}, Solution: {1}'.format(
            ResolutionStepActionType.status_by_id(self.action_type), self.solution)

    def __str__(self):
        return 'Action: {0}, Solution: {1}'.format(
            ResolutionStepActionType.status_by_id(self.action_type), self.solution)

    def explain(self, tabs=''):
        if self.solution:
            solution_explanation = self.solution.explain(tabs + '    ')
        else:
            solution_explanation = 'None'

        explanation = [
            'Action Type: {0}'.format(ResolutionStepActionType.status_by_id(self.action_type)),
            'Solution: {0}'.format(solution_explanation),
        ]

        separator = '\n{0}'.format(tabs)

        return separator.join(explanation)


class ModelIssue(Issue):
    """
    Model assertions may find issues with particular models.
    This is used to track such an issue.
    """
    model_type = models.ForeignKey(ContentType)
    model_id = models.PositiveIntegerField()
    model = generic.GenericForeignKey('model_type', 'model_id')
