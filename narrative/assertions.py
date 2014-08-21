import abc
import copy
import datetime
import sys
import traceback

from pytz import utc as utc_tz

from django.template.loader import render_to_string

from .models import Issue, ModelIssue, IssueStatusType, ResolutionStepActionType
from .executor import Executor


class Assertion(object):
    """
    The assertion class is used for making
    assertions about properties of the system.
    If an assertion is violated, it attempts
    to fix the problem by calling any provided
    diagnostic methods.
    """
    __metaclass__ = abc.ABCMeta

    def __init__(self, assertion_meta):
        self.assertion_meta = assertion_meta
        self.current_issue = None

    @property
    def args(self):
        return self.assertion_meta.get_args()

    @abc.abstractmethod
    def check(self):
        pass

    @property
    def executor(self):
        return Executor()

    # Diagnostic related methods ---
    def diagnose(self, *args, **kwargs):
        """
        Run diagnostic cases and find all potential solutions.
        If there are more than one solutions, log them and notify
        the someone.
        If there are no solutions found, notify someone.
        If one solution is found, apply it.
        """
        current_issue = kwargs['current_issue']
        # Get all diagnostic results
        resolution_steps = [
            getattr(self, diagnostic_case_name)(*args, **kwargs)
            for diagnostic_case_name in self.diagnostic_cases
        ]

        # Filter out any 'None' results
        resolution_steps = filter(bool, resolution_steps)

        if len(resolution_steps) == 0:
            # No solution found, notify the admins
            message_kwargs = {
                'assertion_name': self.assertion_meta.display_name,
            }

            message_txt = render_to_string(
                'no_solution_for_failed_assertion.txt',
                message_kwargs)

            message_html = render_to_string(
                'no_solution_for_failed_assertion.html',
                message_kwargs)

            self.executor.do_defer_to_admins(
                'Failed assertion; No solutions found', message_txt, message_html)
        elif len(resolution_steps) > 1:
            # Multiple solutions found; record them and, notify the admins
            current_issue.status = IssueStatusType.IMPASSE
            current_issue.save()

            self.executor.do_defer_multiple_solutions_to_admins(
                resolution_steps, self.assertion_meta.display_name)
        else:
            # Found a single proposed resolution step; if the step is to do something, do it
            diagnosis = resolution_steps[0]

            if ResolutionStepActionType.EXEC == diagnosis.action_type:
                self.execute_solution(diagnosis.solution)

            current_issue.status = IssueStatusType.SOLUTION_APPLIED
            current_issue.save()

    def post_recovery_cleanup(self, *args, **kwargs):
        """
        Perform any cleanup actions needed after
        this assertion begins passing again.
        """
        pass

    def build_unresolved_issue_queryset(self, *args, **kwargs):
        return Issue.objects.current_issues.filter(failed_assertion=self.assertion_meta)

    def build_wont_fix_issue_queryset(self, *args, **kwargs):
        return Issue.objects.filter(
            failed_assertion=self.assertion_meta, status=IssueStatusType.WONT_FIX)

    def create_issue(self, *args, **kwargs):
        return Issue.objects.create(
            failed_assertion=self.assertion_meta)

    def check_and_diagnose(self, *args, **kwargs):
        """
        Check and diagnose this assertion for these parameters.
        """
        unresolved_issue_queryset = self.build_unresolved_issue_queryset(
            *args, **kwargs)
        wont_fix_issue_queryset = self.build_wont_fix_issue_queryset(
            *args, **kwargs)

        check_result = self.check(*args, **kwargs)

        self.assertion_meta.last_check = datetime.datetime.utcnow()
        self.assertion_meta.save()

        if check_result:
            # Everything is currently okay
            if unresolved_issue_queryset.exists():
                # This assertion just started passing.
                # Set the resolved timestamp to now
                unresolved_issue_queryset.update(resolved_timestamp=self.get_utc_now())

                # Close any open issues
                unresolved_issue_queryset.update(status=IssueStatusType.RESOLVED)

                # Do any needed clean up.
                self.post_recovery_cleanup(*args, **kwargs)

            return True
        else:
            # Something's wrong
            if unresolved_issue_queryset.exists():
                # Issue alredy exists
                current_issue = unresolved_issue_queryset[0]
            elif wont_fix_issue_queryset.exists():
                # This is a pre-existing issue marked as WONT_FIX
                return False
            else:
                # No issue yet exists; create one
                current_issue = self.create_issue(*args, **kwargs)

            kwargs['current_issue'] = current_issue

            # Try to fix the issue
            self.diagnose(*args, **kwargs)

            return False

    @property
    def diagnostic_cases(self):
        """
        Get all diagnostic case methods.
        """
        return [
            member_name for member_name in dir(self)
            if member_name.startswith('diagnostic_case_') and
            callable(getattr(self, member_name))
        ]

    # Misc utilties for working with solutions ---
    def get_utc_now(self):
        return utc_tz.localize(datetime.datetime.utcnow())

    def validate_solution(self, solution):
        (valid, invalid_step) = self.executor.can_execute(solution.get_plan())

        if not valid:
            self.executor.do_defer_to_admins(
                'Invalid assertion detected',
                'Assertion: {0}, Invalid step: {0}'.format(
                    self.assertion_meta.display_name, invalid_step))
        return valid

    def execute_solution(self, solution):
        """
        Validate a solution, then step through and execute each of it's steps.
        """
        if self.validate_solution(solution):
            try:
                self.executor.execute(solution.get_plan())
            except:
                # If an error occurrs executing the solution, store the traceback information.
                exc_type, exc_value, tb = sys.exc_info()

                solution.error_traceback = '\n'.join(
                    traceback.format_tb(tb) + [
                        str(exc_type),
                        str(exc_value)])

            solution.enacted = self.get_utc_now()
            solution.save()


class ModelAssertion(Assertion):
    """
    ModelAssertion is a class for making assertions about
    a particular set of models.
    """
    __metaclass__ = abc.ABCMeta

    def __init__(self, *args, **kwargs):
        super(ModelAssertion, self).__init__(*args, **kwargs)

    @abc.abstractproperty
    def queryset(self):
        """
        Return the queryset of records to check.
        """
        pass

    @abc.abstractmethod
    def check_record(self, record):
        pass

    def check(self, *args, **kwargs):
        return self.check_record(kwargs.pop('record'))

    def build_unresolved_issue_queryset(self, *args, **kwargs):
        """
        We override this to query for Model Issues instead of
        just Issues like the base Assertion class.
        """
        record = kwargs['record']

        return ModelIssue.objects.current_issues.filter(
            failed_assertion=self.assertion_meta,
            model_type__model=record.__class__.__name__.lower(),
            model_id=record.id)

    def build_wont_fix_issue_queryset(self, *args, **kwargs):
        """
        We override this to query for Model Issues instead of
        just Issues like the base Assertion class.
        """
        record = kwargs['record']

        return ModelIssue.objects.filter(
            failed_assertion=self.assertion_meta,
            model_type__model=record.__class__.__name__.lower(),
            status=IssueStatusType.WONT_FIX,
            model_id=record.id)

    def create_issue(self, *args, **kwargs):
        """
        We override this to create Model Issues instead of
        just Issues like the base Assertion class.
        """
        record = kwargs['record']

        return ModelIssue.objects.create(
            failed_assertion=self.assertion_meta,
            model=record)

    def check_and_diagnose(self, *args, **kwargs):
        """
        ModelAssertion is kind of funny; all of the logic of
        the base Assertion class needs to be ran, but for a particular
        record.  So that's exactly what we do.
        """
        results = []

        for record in self.queryset:
            # For each record
            args_copy = copy.copy(args)
            kwargs_copy = copy.copy(kwargs)
            kwargs_copy['record'] = record

            results.append(super(ModelAssertion, self).check_and_diagnose(*args_copy, **kwargs_copy))

        return all(results)
