import datetime
import json

from django.conf import settings
from django.contrib.auth.models import Group, User
from django.core import mail
from django.test import TestCase

from ..assertion import Assertion
from ..models import (Solution, AssertionMeta, Issue, ResolutionStep,
                      IssueStatusType, ResolutionStepActionType)


class AssertionTests(TestCase):
    def setUp(self):
        # Fields set by stubbed methods
        self.post_recovery_cleanup_called = True
        self.diagnostic_case_test_1_called = False
        self.diagnostic_case_test_2_called = False
        self.execute_solution_called = False
        self.deferred_multiple_solutions = False
        self.defer_to_admins_called = False
        self.email_called = False
        self.deferred_kwargs = None

        self.mock_utc_now = datetime.datetime(2013, 7, 9, 12, 0, 0)

        class TestAssertion(Assertion):
            def get_utc_now(self_):
                return self.mock_utc_now

            def check(self_):
                pass

            def post_recovery_cleanup(self_):
                self.post_recovery_cleanup_called = True

            def diagnostic_case_test_1(self_, *args, **kwargs):
                pass

            def diagnostic_case_test_2(self_, *args, **kwargs):
                pass

            def do_defer_multiple_solutions_to_admins(self_, solutions):
                self.deferred_multiple_solutions = True

            def do_defer_to_admins(self_, *args, **kwargs):
                self.defer_to_admins_called = True
                self.deferred_kwargs = kwargs

            def do_email(self_, *args, **kwargs):
                self.email_called = True

        self.assertion_meta = AssertionMeta.objects.create(
            display_name='Mock assertion', assertion_load_path='foo.bar', enabled=True)

        self.assertion = TestAssertion(self.assertion_meta)

        # Some solutions
        self.valid_solution_plan = [
            ['email', {'adddress': 'josh.marlow@akimbo.io', 'subject': 'fake subject', 'message': 'fake message'}],
            ['defer_to_admins', {'subject': 'copacetic', 'hints': ['it is all good']}],
        ]

        self.valid_solution_2_json = [
            ['email', {'address': 'wesley.kendall@akimbo.io', 'subject': 'POW', 'message': 'fake message'}],
        ]

        self.in_valid_solution_plan = [
            ('format', {'drive': 'C'}),
        ]

    def test_get_diagnostic_cases(self):
        self.assertEqual(
            set(self.assertion.diagnostic_cases),
            set(['diagnostic_case_test_1', 'diagnostic_case_test_2']),
            'Diagnostic methods not returned as expected')

    def test_validate_solution(self):
        """
        Verify that a valid solution can be validated,
        but an invalid one cannot be.
        """
        valid_solution = Solution.objects.create(plan=self.valid_solution_plan)
        self.assertTrue(self.assertion.validate_solution(valid_solution), 'Validating valid solution')
        self.assertFalse(self.defer_to_admins_called, 'Verifying the admins were not bothered by a success')

        in_valid_solution = Solution.objects.create(plan=self.in_valid_solution_plan)
        self.assertFalse(self.assertion.validate_solution(in_valid_solution), 'Validating invalid solution')
        self.assertTrue(self.defer_to_admins_called, 'Verifying the admins were notified of an invalid solution')

    def test_execute_solution(self):
        # Verify the solution was executed
        self.issue = Issue.objects.create(failed_assertion=self.assertion_meta)
        self.issue.save()

        valid_solution = Solution.objects.create(plan=self.valid_solution_plan)
        self.assertion.execute_solution(valid_solution)

        # Verify that the steps were executed appropriately
        self.assertTrue(self.email_called, 'Verifies that the appropriate person was emailed')
        self.assertTrue(self.defer_to_admins_called, 'Verifies that the admins were called')

        # Verify that the args and kwargs were passed into the steps appropriately
        self.assertEqual(
            self.deferred_kwargs, {'subject': 'copacetic', 'hints': ['it is all good']},
            'Verifying that the appropriate kwargs were used in executing the step')

        # Verify that the enacted time is updated
        self.assertEqual(
            Solution.objects.get(id=valid_solution.id).enacted,
            self.mock_utc_now,
            'Enacted time should have been updated to time of saving')


class Test_diagnose(TestCase):
    def setUp(self):
        # Fields set by stubbed methods
        self.diagnostic_case_test_1_called = False
        self.diagnostic_case_test_2_called = False
        self.execute_solution_called = False
        self.deferred_multiple_solutions = False
        self.defer_to_admins_called = False
        self.email_called = False
        self.deferred_kwargs = None

        # Values returned by stubbed methods
        self.mock_resolution_step_1 = None
        self.mock_resolution_step_2 = None

        class TestAssertion(Assertion):
            def check(self_):
                pass

            def execute_solution(self_, solution):
                self.execute_solution_called = True
                super(TestAssertion, self_).execute_solution(solution)

            def diagnostic_case_test_1(self_, current_issue, *args, **kwargs):
                self.diagnostic_case_test_1_called = True
                return self.mock_resolution_step_1

            def diagnostic_case_test_2(self_, current_issue, *args, **kwargs):
                self.diagnostic_case_test_2_called = True
                return self.mock_resolution_step_2

            def do_defer_multiple_solutions_to_admins(self_, solutions):
                self.deferred_multiple_solutions = True

            def do_defer_to_admins(self_, *args, **kwargs):
                self.defer_to_admins_called = True
                self.deferred_kwargs = kwargs

            def do_email(self_, *args, **kwargs):
                self.email_called = True

        self.assertion_meta = AssertionMeta.objects.create(
            display_name='Mock assertion', assertion_load_path='foo.bar', enabled=True)

        self.assertion = TestAssertion(self.assertion_meta)

        self.issue = Issue.objects.create(failed_assertion=self.assertion_meta)

        # Some solutions
        self.valid_solution_plan = [
            ['email', {'adddress': 'josh.marlow@akimbo.io', 'subject': 'fake subject', 'message': 'fake message'}],
            ['defer_to_admins', {'subject': 'copacetic', 'hints': ['it is all good']}],
        ]

        self.valid_solution_plan_2 = [
            ['email', {'address': 'wesley.kendall@akimbo.io', 'subject': 'POW', 'message': 'fake message'}],
        ]

        self.in_valid_solution_plan = [
            ('format', {'drive': 'C'}),
        ]

    def tearDown(self):
        ResolutionStep.objects.all().delete()
        Issue.objects.all().delete()
        Solution.objects.all().delete()

    def test_diagnose_with_no_solution(self):
        # Test that if no diagnostic case returns a solution, none are executed, and
        #   the admins are notified.
        self.mock_resolution_step_1 = None
        self.mock_resolution_step_2 = None

        self.assertion.diagnose(**{'current_issue': self.issue})

        self.assertFalse(self.execute_solution_called, 'execute_solution should not have been called')
        self.assertTrue(self.defer_to_admins_called, 'Admins should have been notified')

    def test_diagnose_with_one_solution(self):
        # Test that if only one diagnostic case returns a solution, it is saved in the database,
        # and it is executed
        solution_count = Solution.objects.all().count()

        soln_1 = Solution.objects.create(plan=self.valid_solution_plan)
        self.mock_resolution_step_1 = ResolutionStep.objects.create(
            issue=self.issue, solution=soln_1)
        self.mock_resolution_step_2 = None

        self.assertion.diagnose(**{'current_issue': self.issue})

        self.assertTrue(self.execute_solution_called, 'execute_solution should not have been called')
        self.assertEqual(
            Solution.objects.all().count(),
            solution_count + 1,
            'One more solution should have been created')

        issue_reloaded = Issue.objects.get(id=self.issue.id)

        # Reload the issue to check that it's state has changed
        self.assertEqual(
            issue_reloaded.status,
            IssueStatusType.SOLUTION_APPLIED,
            'Issue status should have been updated to SolutionApplied')

        plan_set = set([isr.solution.plan_json for isr in issue_reloaded.resolutionstep_set.all()])

        self.assertEqual(
            plan_set,
            set([soln_1.plan_json]),
            'Solution Plan stored in the database should match the newly created solution')

    def test_diagnose_with_multiple_solutions(self):
        # Test that if multiple diagnostic case return solutions, none are executed, but an impasse is
        #   created and the admins are notified.
        self.execute_solution_called = False

        soln_1 = Solution.objects.create(plan=self.valid_solution_plan)
        soln_2 = Solution.objects.create(plan=self.valid_solution_plan_2)

        self.mock_resolution_step_1 = ResolutionStep.objects.create(
            issue=self.issue, solution=soln_1)
        self.mock_resolution_step_2 = ResolutionStep.objects.create(
            issue=self.issue, solution=soln_2)

        self.assertion.diagnose(**{'current_issue': self.issue})

        self.assertFalse(self.execute_solution_called, 'execute_solution should not have been called')
        self.assertTrue(
            self.deferred_multiple_solutions, 'Verifies that the admins were contacted about the multiple solutions')

        # Reload the issue to check that it's state has changed
        issue_reloaded = Issue.objects.get(id=self.issue.id)

        self.assertEqual(
            issue_reloaded.status,
            IssueStatusType.IMPASSE,
            'Issue status should have been updated to Impasse')

        solution_set = Solution.objects.filter(resolutionstep__issue=self.issue)

        self.assertEqual(
            len(solution_set),
            2,
            'Expected two valid solutions')

        plan_set = set([isr.solution.plan_json for isr in issue_reloaded.resolutionstep_set.all()])

        self.assertEqual(
            plan_set,
            set([soln_1.plan_json, soln_2.plan_json]),
            'Solution plans stored in the database should match the newly created solution')

    def test_diagnose_with_pass(self):
        """
        Test that diagnose appropriately handles an ResolutionStep
        with a PASS type.
        """
        # Create an issue resolution step with a PASS type
        soln_1 = Solution.objects.create(plan=self.valid_solution_plan)

        self.mock_resolution_step_1 = ResolutionStep.objects.create(
            issue=self.issue, solution=soln_1, action_type=ResolutionStepActionType.PASS)
        self.mock_resolution_step_2 = None

        # Call diagnose
        self.assertion.diagnose(**{'current_issue': self.issue})

        # Verify that execute_solution was not called
        self.assertFalse(
            self.execute_solution_called, 'Execute solution should not have been called on a PASS step')

    def test_diagnose_with_a_solution_and_a_pass(self):
        """
        Test that diagnose appropriately handles multiple solutions and a PASS.
        """
        # Create an issue resolution step with a PASS type and one
        # EXEC type
        soln_1 = Solution.objects.create(plan=self.valid_solution_plan)
        soln_2 = Solution.objects.create(plan=self.valid_solution_plan_2)

        self.mock_resolution_step_1 = ResolutionStep.objects.create(
            issue=self.issue, solution=soln_1, action_type=ResolutionStepActionType.PASS)
        self.mock_resolution_step_2 = ResolutionStep.objects.create(
            issue=self.issue, solution=soln_2)

        # Call diagnose
        self.assertion.diagnose(**{'current_issue': self.issue})

        # Verify that execute_solution was not called
        self.assertFalse(
            self.execute_solution_called, 'Execute solution should not have been called on a PASS step')

        # Verify that the multiple resolution steps were deferred
        self.assertTrue(
            self.deferred_multiple_solutions, 'Verifies that the admins were contacted about the multiple solutions')


class Test_check_and_diagnose(TestCase):
    def setUp(self):
        # Fields set by stubbed methods
        self.diagnose_called = False
        self.post_recovery_cleanup_called = True
        self.execute_solution_called = False
        self.deferred_multiple_solutions = False
        self.defer_to_admins_called = False
        self.email_called = False
        self.deferred_kwargs = None

        # Values returned by stubbed methods
        self.check_return_value = False

        class TestAssertion(Assertion):
            def check(self_):
                return self.check_return_value

            def post_recovery_cleanup(self_):
                self.post_recovery_cleanup_called = True

            def execute_solution(self_, solution):
                self.execute_solution_called = True

            def diagnose(self_, *args, **kwargs):
                self.diagnose_called = True

            def do_defer_multiple_solutions_to_admins(self_, solutions):
                self.deferred_multiple_solutions = True

            def do_defer_to_admins(self_, *args, **kwargs):
                self.defer_to_admins_called = True
                self.deferred_kwargs = kwargs

            def do_email(self_, *args, **kwargs):
                self.email_called = True

        self.assertion_meta = AssertionMeta.objects.create(
            display_name='Mock assertion', assertion_load_path='foo.bar', enabled=True)

        self.assertion = TestAssertion(self.assertion_meta)

    def test_check_and_diagnose_with_passing_check(self):
        """
        Verifies that the check_and_diagnosis method appropriately
        creates and resolves Issue objects.
        """
        # Verify that a successful assertion does not create a new Issue
        self.check_return_value = True
        self.post_recovery_cleanup_called = False

        issue_count = Issue.objects.all().count()

        self.assertion.check_and_diagnose()

        self.assertEqual(
            Issue.objects.all().count(),
            issue_count,
            'A new Issue should not have been created')
        self.assertFalse(
            self.post_recovery_cleanup_called,
            'post_recovery_clean_up should not have been called')

    def test_check_and_diagnose_with_failing_check(self):
        # Verify that a failed assertion creates a new Issue
        self.check_return_value = False
        self.post_recovery_cleanup_called = False

        issue_count = Issue.objects.all().count()

        self.assertion.check_and_diagnose()

        open_issue_count = Issue.objects.filter(
            failed_assertion=self.assertion.assertion_meta,
            status=IssueStatusType.OPEN).count()

        self.assertEqual(
            Issue.objects.all().count(),
            issue_count + 1,
            'A new Issue should have been created')
        self.assertEqual(
            open_issue_count,
            1,
            'There should be one open Issue for this assertion')
        self.assertFalse(
            self.post_recovery_cleanup_called,
            'post_recovery_clean_up should not have been called')

    def test_check_and_diagnose_with_recovered_check(self):
        # Verify that a failed assertion does not create a new Issue if one already exist
        test_issue = Issue.objects.create(failed_assertion=self.assertion_meta, status=IssueStatusType.OPEN)

        self.post_recovery_cleanup_called = False

        issue_count = Issue.objects.all().count()

        self.assertion.check_and_diagnose()

        self.assertEqual(
            Issue.objects.all().count(),
            issue_count,
            'A duplicate Issue should not have been created')
        self.assertFalse(
            self.post_recovery_cleanup_called,
            'post_recovery_clean_up should not have been called')

        # Verify that a successful assertion, following a failed one, marks
        # any open Issues as resolved.
        self.check_return_value = True
        self.post_recovery_cleanup_called = False

        self.assertion.check_and_diagnose()

        # Reload the previously open test Issue
        test_issue = Issue.objects.get(id=test_issue.id)

        self.assertEqual(
            test_issue.status,
            IssueStatusType.RESOLVED,
            'Issue should have been resolved')

        self.assertTrue(
            self.post_recovery_cleanup_called,
            'post_recovery_clean_up should have been called')

    def test_check_and_diagnose_with_exising_wontfix_issue(self):
        # Create an issue marked as WONT_FIX
        self.wont_fix = Issue.objects.create(
            failed_assertion=self.assertion_meta,
            status=IssueStatusType.WONT_FIX)

        self.check_return_value = False

        issue_count = Issue.objects.count()

        # Run check_and_diagnose
        ret_val = self.assertion.check_and_diagnose()

        # Verify that diagnose was not called
        self.assertFalse(
            self.diagnose_called,
            'Diagnose should not have been called')

        # no additional issue was created,
        self.assertEqual(
            Issue.objects.count(),
            issue_count,
            'No new issues should have been created')

        # False was returned
        self.assertFalse(
            ret_val,
            'check_and_diagnose should have returned False')

        # The pre-existing issue is still marked as WONT_FIX
        self.assertEqual(
            Issue.objects.get(id=self.wont_fix.id).status,
            IssueStatusType.WONT_FIX,
            'Issue should still be marked as WONT_FIX')


class DoMethodTests(TestCase):
    """
    Tests for the various 'do_*' methods that come with
    the Assertion class.
    """
    def setUp(self):

        class TestAssertion(Assertion):
            def check(self):
                return False

        self.assertion_meta = AssertionMeta(
            display_name='Test Assertion', assertion_load_path='foo.bar', enabled=True)

        self.assertion = TestAssertion(self.assertion_meta)

        # Set up the user admins
        admin_group, created = Group.objects.get_or_create(
            name=settings.NARRATIVE_ADMIN_GROUP_NAME)
        self.test_user = User.objects.create(
            username='test_user', password='test_user', email='test_user@example.com')
        self.test_user_2 = User.objects.create(
            username='test_user_2', password='test_user_2', email='test_user_2@example.com')

        admin_group.user_set.add(self.test_user)
        admin_group.user_set.add(self.test_user_2)

    def test_defer_to_admins(self):
        sent_count = len(mail.outbox)

        test_subject = 'test subject'
        test_message = 'test message'
        test_hints = ['hint 1', 'hint 2']

        self.assertion.do_defer_to_admins(test_subject, test_message, test_hints)

        # Verify the emails were sent to the appropriate users
        self.assertEqual(
            len(mail.outbox), sent_count + 1, 'Verifying the appropriate number of emails have been sent')

        self.assertEqual(
            set(mail.outbox[0].recipients()),
            set([self.test_user.email, self.test_user_2.email]),
            'Verifying the emails are headed to the appropriate recipeients')

    def test_defer_impasse_multiple_solutions_to_admins(self):
        sent_count = len(mail.outbox)

        # Set up some mock solutions
        valid_solution = Solution.objects.create(plan_json=json.dumps([
            ('email', ['josh.marlow@akimbo.io', 'fake subject', 'fake message'], {}),
            ('defer_to_admins', ['copacetic'], {'hints': ['it is all good']}),
        ]))
        valid_solution_2 = Solution.objects.create(plan_json=json.dumps([
            ('email', ['wesley.kendall@akimbo.io', 'POW', 'fake message'], {}),
        ]))

        self.assertion.do_defer_multiple_solutions_to_admins([valid_solution, valid_solution_2])

        expected_subject = 'Impasse: "Test Assertion" has Multiple resolution steps proposed'

        # Verify the emails were sent
        self.assertEqual(
            len(mail.outbox), sent_count + 1, 'Verifying the appropriate number of emails have been sent')

        self.assertEqual(
            set(mail.outbox[0].recipients()),
            set([self.test_user.email, self.test_user_2.email]),
            'Verifying the emails are headed to the appropriate recipeients')

        self.assertEqual(
            mail.outbox[0].subject,
            expected_subject,
            'Verifying the subject was sent as expected')
