import datetime
import json
import uuid

from django.contrib.contenttypes.models import ContentType
from django.contrib.contenttypes import generic
from django.db import models
from manager_utils import ManagerUtilsManager
from pytz import utc as utc_tz


def find_tuple(tuple_list, key, which):
    filtered_list = filter(lambda tple: tple[which] == key, tuple_list)
    return filtered_list[0] if len(filtered_list) else None


class StatusType(object):
    types = []

    @classmethod
    def status_by_id(cls, id_):
        return find_tuple(cls.types, id_, 0)[1]

    @classmethod
    def status_by_name(cls, name):
        status = find_tuple(cls.types, name.title(), 1)
        return status[0] if status is not None else None


class DatumLogLevel(StatusType):
    TRACE = 0
    DEBUG = 1
    INFO = 2
    WARN = 3
    ERROR = 4

    types = (
        (TRACE, 'Trace'),
        (ERROR, 'Error'),
        (WARN, 'Warn'),
        (INFO, 'Info'),
        (DEBUG, 'Debug'),
    )

    @classmethod
    def status_by_name(cls, name):
        status = find_tuple(cls.types, name.title(), 1)
        return status[0] if status is not None else NarrativeConfig.objects.get_minimum_log_level()


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


class NarrativeConfigManager(models.Manager):
    def get_minimum_log_level(self):
        return self.all()[0].minimum_datum_log_level


class NarrativeConfig(models.Model):
    # Determines what the minimum log_level allowed to be created by the log_datum function
    minimum_datum_log_level = models.IntegerField(
        choices=DatumLogLevel.types, default=DatumLogLevel.INFO)

    objects = NarrativeConfigManager()


class DatumManager(models.Manager):
    def clear_expired(self):
        expired_set = self.filter(expiration_time__isnull=False).filter(expiration_time__lte=self.get_utc_now())

        expired_count = expired_set.count()

        expired_set.delete()

        return expired_count

    def get_utc_now(self):
        return utc_tz.localize(datetime.datetime.utcnow())


class Datum(models.Model):
    def __init__(self, *args, **kwargs):
        if 'ttl' in kwargs:
            kwargs['expiration_time'] = self.get_utc_now() + kwargs.pop('ttl')

        super(Datum, self).__init__(*args, **kwargs)

    # When was the datum created
    timestamp = models.DateTimeField(auto_now_add=True, db_index=True)

    expiration_time = models.DateTimeField(null=True, blank=True, default=None)

    # Origin of this datum; ie, what piece of software created it
    origin = models.CharField(max_length=64)

    datum_name = models.CharField(max_length=64)

    # Additional information about the datum; this is very datum specific
    # This approach, storing json in a textfield and having an
    # explicit accessor and mutator, is very ugly.  Really this is because
    # we are storing non-structured/sparse data in a relational format.
    datum_note_json = models.TextField(null=True, blank=True, default=None)

    def get_note(self):
        if self.datum_note_json:
            return json.loads(self.datum_note_json)
        else:
            return []

    def set_note(self, note):
        self.datum_note_json = json.dumps(note)

    # An ID to tie particular datums together
    thread_id = models.CharField(max_length=36, null=True, blank=True)

    log_level = models.IntegerField(choices=DatumLogLevel.types, default=DatumLogLevel.INFO)

    objects = DatumManager()

    def get_utc_now(self):
        return utc_tz.localize(datetime.datetime.utcnow())

    @property
    def timestamp_with_tz(self):
        return utc_tz.localize(self.timestamp)

    def save(self, *args, **kwargs):
        if None == self.thread_id:
            self.thread_id = str(uuid.uuid4())

        super(Datum, self).save(*args, **kwargs)

    def __unicode__(self):
        note_snippet = self.datum_note_json[:50] if self.datum_note_json else ''
        return u'origin:{0} datum_name:{1} note:{2}'.format(
            self.origin, self.datum_name, note_snippet)


def log_datum(*args, **kwargs):
    """
    Handle logging a datum.  It is better to use this method than to manually create datums,
    because it provides a central place for controlling which datums should or should not be
    created based the logging level set in the NarrativeConfig.
    """
    minimum_datum_log_level = NarrativeConfig.objects.filter()[0].minimum_datum_log_level

    note = None
    datum = None

    if kwargs['log_level'] >= minimum_datum_log_level:
        note = kwargs.pop('note') if 'note' in kwargs else None

        datum = Datum(*args, **kwargs)

        if note:
            datum.set_note(note)

        datum.save()

    return datum


class PeriodicalMeta(models.Model):
    """
    Used for storing meta information about class that needs to
    be periodically checked.
    """
    class Meta:
        abstract = True
        unique_together = ('display_name', 'class_load_path',)

    # Display name for humans
    display_name = models.CharField(max_length=64)

    # Python import path to the periodic class
    class_load_path = models.CharField(max_length=96, default='')

    # Determines if this periodic should ever be checked
    enabled = models.BooleanField(default=False)

    # Indicate how often to check this periodic
    check_interval_seconds = models.IntegerField(default=3600)
    last_check = models.DateTimeField(default=datetime.datetime(1970, 1, 1))

    args_json = models.TextField(
        blank=True, default='{}',
        help_text=(u'JSON encoded named arguments'))

    objects = ManagerUtilsManager()

    def __init__(self, *args, **kwargs):
        if 'args' in kwargs:
            kwargs['args_json'] = json.dumps(kwargs.pop('args'))

        super(PeriodicalMeta, self).__init__(*args, **kwargs)

    def get_args(self):
        if self.args_json:
            return json.loads(self.args_json)
        else:
            return {}

    def set_args(self, args):
        self.args_json = json.dumps(args)

    def should_check(self):
        """
        Determine if enough time has passed to check again.
        """
        return (self.last_check + datetime.timedelta(seconds=self.check_interval_seconds)) <= datetime.datetime.utcnow()

    def load_class(self):
        """
        Imports and returns the Periodic module.
        """
        class_path = '.'.join(self.class_load_path.split('.')[:-1])
        class_name = self.class_load_path.split('.')[-1]
        class_file_name = self.class_load_path.split('.')[-2]

        try:
            class_module = __import__(class_path, globals(), locals(), [class_file_name])
            if not class_module or not hasattr(class_module, class_name):
                return None

            loaded_class = getattr(class_module, class_name)
            if not loaded_class:
                return None
            return loaded_class
        except ImportError:
            return None

    def __unicode__(self):
        return u'{0}::{1}'.format(self.display_name, self.class_load_path)


class AssertionMeta(PeriodicalMeta):
    pass


class EventMeta(PeriodicalMeta):
    pass


class Solution(models.Model):
    def __init__(self, *args, **kwargs):
        plan = kwargs.pop('plan', [])
        kwargs['plan_json'] = json.dumps(plan)

        super(Solution, self).__init__(*args, **kwargs)

    # What was the name of the diagnostic method that generated this solution?
    diagnostic_case_name = models.CharField(max_length=64)

    # Description of the problem this solution addresses
    problem_description = models.CharField(max_length=128)

    # The steps (stored as json) for this solution
    plan_json = models.TextField()

    # Time in which the solution was enacted
    enacted = models.DateTimeField(null=True, blank=True)

    # Exception traceback if there was an error executing the solution
    error_traceback = models.TextField(null=True, blank=True)

    def get_plan(self):
        if self.plan_json:
            return json.loads(self.plan_json)
        else:
            return []

    def set_plan(self, plan):
        self.plan_json = json.dumps(plan)

    def __unicode__(self):
        return u'Solution - Diagnostic case name: {0}, description: {1}'.format(
            self.diagnostic_case_name, self.problem_description)

    def __str__(self):
        return 'Solution - Diagnostic case name: {0}, description: {1}'.format(
            self.diagnostic_case_name, self.problem_description)

    def explain(self, tabs=''):
        # Aggregate all of the plan steps into a nice human readable format
        plan_explanation = [
            step[0] for step in self.get_plan()
        ]

        step_separator = ('\n{0}    '.format(tabs))

        plan_explanation_string = step_separator + step_separator.join(plan_explanation)

        explanation = [
            'Diagnostic case name: {0}'.format(self.diagnostic_case_name),
            'Problem Description: {0}'.format(self.problem_description),
            'Enacted: {0}'.format(self.enacted or 'Never'),
            'Status: {0}'.format('FAILED' if self.error_traceback else 'SUCCESS'),
            'Plan: {0}'.format(plan_explanation_string),
        ]

        separator = '\n{0}'.format(tabs)

        return separator.join(explanation)


class IssueManager(models.Manager):
    @property
    def current_issues(self):
        resolved_list = [IssueStatusType.RESOLVED, IssueStatusType.WONT_FIX]

        return self.exclude(status__in=resolved_list)


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

    objects = IssueManager()

    def __unicode__(self):
        return u'Issue - {0} ({1})'.format(
            self.failed_assertion.display_name, IssueStatusType.status_by_id(self.status))

    def __str__(self):
        return 'Issue - {0} ({1})'.format(
            self.failed_assertion.display_name, IssueStatusType.status_by_id(self.status))

    def explain(self, tabs=''):
        step_separator = '    ' + '-' * 15
        resolution_separator = '\n{0}\n{1}    '.format(step_separator, tabs)
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

    def steps_matching_plan(self, plan):
        """
        Given an Issue, return the ResolutionStep where the solution applied
        matches the provided solution.

        The match is in terms of matching operations; not neccesarily the arguments passed.
        """
        def get_step_operations(plan):
            return set(map(lambda step: step[0], plan))

        target_steps = get_step_operations(plan)

        matching_steps = []

        for step in self.resolutionstep_set.all():
            if step.solution:
                if get_step_operations(step.solution.get_plan()) == target_steps:
                    matching_steps.append(step)

        return matching_steps

    def get_non_pass_steps(self):
        """
        Return all steps that are not PASSes.
        """
        return filter(
            lambda isr: isr.action_type != ResolutionStepActionType.PASS,
            self.resolutionstep_set.order_by('created'))

    @property
    def age(self):
        return datetime.datetime.utcnow() - self.created_timestamp

    @property
    def status_name(self):
        return IssueStatusType.id_to_name(self.status)


class ResolutionStep(models.Model):
    """
    Track steps taken to resolve an issue.
    """
    issue = models.ForeignKey(Issue)
    solution = models.ForeignKey(Solution, null=True, blank=True)

    action_type = models.IntegerField(
        choices=ResolutionStepActionType.types, default=ResolutionStepActionType.EXEC)

    created = models.DateTimeField(auto_now_add=True)

    # The reason this step was selected; just human readable documentation
    reason = models.CharField(max_length=64, default=None, null=True, blank=True)

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
            'Reason: {0}'.format(self.reason),
        ]

        separator = '\n{0}'.format(tabs)

        return separator.join(explanation)


class ModelIssueManager(models.Manager):
    @property
    def current_issues(self):
        resolved_list = [IssueStatusType.RESOLVED, IssueStatusType.WONT_FIX]

        return self.exclude(status__in=resolved_list)


class ModelIssue(Issue):
    """
    Model assertions may find issues with particular models.
    This is used to track such an issue.
    """
    model_type = models.ForeignKey(ContentType)
    model_id = models.PositiveIntegerField()
    model = generic.GenericForeignKey('model_type', 'model_id')

    objects = ModelIssueManager()
