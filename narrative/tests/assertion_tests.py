import json

from django.conf import settings
from django.contrib.auth.models import Group, User
from django.core import mail
from django.test import TestCase

from ..assertion import Assertion
from ..models import Solution


class AssertionTests(TestCase):
    def setUp(self):
        # Fields set by stubbed methods
        self.diagnostic_case_test_1_called = False
        self.diagnostic_case_test_2_called = False
        self.execute_solution_called = False
        self.deferred_multiple_solutions = False
        self.defer_to_admins_called = False
        self.email_called = False
        self.deferred_args = None
        self.deferred_kwargs = None

        # Values returned by stubbed methods
        self.mock_solution_1 = None
        self.mock_solution_2 = None

        class TestAssertion(Assertion):
            @property
            def display_name(self):
                return 'Test Assertion'

            def check(self):
                return False

            def execute_solution(self_, solution):
                self.execute_solution_called = True
                super(TestAssertion, self_).execute_solution(solution)

            def diagnostic_case_test_1(self_, *args, **kwargs):
                self.diagnostic_case_test_1_called = True
                return self.mock_solution_1

            def diagnostic_case_test_2(self_, *args, **kwargs):
                self.diagnostic_case_test_2_called = True
                return self.mock_solution_2

            def do_defer_multiple_solutions_to_admins(self_, solutions):
                self.deferred_multiple_solutions = True

            def do_defer_to_admins(self_, *args, **kwargs):
                self.defer_to_admins_called = True
                self.deferred_args = args
                self.deferred_kwargs = kwargs

            def do_email(self_, *args, **kwargs):
                self.email_called = True

        self.test_assertion = TestAssertion()

        # Some solutions
        self.valid_solution = Solution(plan_json=json.dumps([
            ('email', ['josh.marlow@akimbo.io', 'fake subject', 'fake message'], {}),
            ('defer_to_admins', ['copacetic'], {'hints': ['it is all good']}),
        ]))
        self.valid_solution_2 = Solution(plan_json=json.dumps([
            ('email', ['wesley.kendall@akimbo.io', 'POW', 'fake message'], {}),
        ]))
        self.in_valid_solution = Solution(plan_json=json.dumps([
            ('format', ['C'], {}),
        ]))

    def test_get_diagnostic_cases(self):
        self.assertEqual(
            set(self.test_assertion.diagnostic_cases),
            set(['diagnostic_case_test_1', 'diagnostic_case_test_2']),
            'Diagnostic methods not returned as expected')

    def test_validate_solution(self):
        """
        Verify that a valid solution can be validated,
        but an invalid one cannot be.
        """
        self.assertTrue(self.test_assertion.validate_solution(self.valid_solution), 'Validating valid solution')
        self.assertFalse(self.defer_to_admins_called, 'Verifying the admins were not bothered by a success')

        self.assertFalse(self.test_assertion.validate_solution(self.in_valid_solution), 'Validating invalid solution')
        self.assertTrue(self.defer_to_admins_called, 'Verifying the admins were notified of an invalid solution')

    def test_diagnose(self):
        # Test that if no diagnostic case returns a solution, none are executed, and
        #   the admins are notified.
        self.mock_solution_1 = None
        self.mock_solution_2 = None

        self.test_assertion.diagnose()

        self.assertFalse(self.execute_solution_called, 'execute_solution should not have been called')
        self.assertTrue(self.defer_to_admins_called, 'Admins should have been notified')

        # Test that if only one diagnostic case returns a solution, it is executed
        self.mock_solution_1 = self.valid_solution
        self.mock_solution_2 = None

        self.test_assertion.diagnose()

        self.assertTrue(self.execute_solution_called, 'execute_solution should not have been called')

        # Test that if multiple diagnostic cases return solutions, none are executed, but a conflict is
        #   created and the admins are notified.
        self.execute_solution_called = False

        self.mock_solution_1 = self.valid_solution
        self.mock_solution_2 = self.valid_solution_2

        self.test_assertion.diagnose()

        self.assertFalse(self.execute_solution_called, 'execute_solution should not have been called')
        self.assertTrue(self.defer_to_admins_called, 'Verifies that the admins were contacted about the multiple solutions')

    def test_execute_solution(self):
        # Verify the solution was executed
        self.test_assertion.execute_solution(self.valid_solution)

        # Verify that the steps were executed appropriately
        self.assertTrue(self.email_called, 'Verifies that the appropriate person was emailed')
        self.assertTrue(self.defer_to_admins_called, 'Verifies that the admins were called')

        # Verify that the args and kwargs were passed into the steps appropriately
        self.assertEqual(
            self.deferred_args, (u'copacetic',),
            'Verifying that the appropriate args were used in executing the step')
        self.assertEqual(
            self.deferred_kwargs, {u'hints': [u'it is all good']},
            'Verifying that the appropriate kwarg were used in executing the step')


class DoTests(TestCase):
    """
    Tests for the various 'do_*' methods that come with
    the Assertion class.
    """
    def setUp(self):

        class TestAssertion(Assertion):
            @property
            def display_name(self):
                return 'Test Assertion'

            def check(self):
                return False

        self.test_assertion = TestAssertion()

        # Set up the user admins
        admin_group, created = Group.objects.get_or_create(name=settings.NARRATIVE_ADMIN_GROUP_NAME)
        self.test_user = User.objects.create(username='test_user', password='test_user', email='test_user@example.com')
        self.test_user_2 = User.objects.create(username='test_user_2', password='test_user_2', email='test_user_2@example.com')

        admin_group.user_set.add(self.test_user)
        admin_group.user_set.add(self.test_user_2)

    def test_defer_to_admins(self):
        sent_count = len(mail.outbox)

        test_subject = 'test subject'
        test_message = 'test message'
        test_hints = ['hint 1', 'hint 2']

        self.test_assertion.do_defer_to_admins(test_subject, test_message, test_hints)

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
        valid_solution = Solution(plan_json=json.dumps([
            ('email', ['josh.marlow@akimbo.io', 'fake subject', 'fake message'], {}),
            ('defer_to_admins', ['copacetic'], {'hints': ['it is all good']}),
        ]))
        valid_solution_2 = Solution(plan_json=json.dumps([
            ('email', ['wesley.kendall@akimbo.io', 'POW', 'fake message'], {}),
        ]))

        self.test_assertion.do_defer_multiple_solutions_to_admins([valid_solution, valid_solution_2])

        expected_subject = 'Impasse: "Test Assertion" has Multiple solutions proposed'

        # Verify the emails were sent
        self.assertEqual(
            len(mail.outbox), sent_count + 1, 'Verifying the appropriate number of emails have been sent')

        self.assertEqual(
            set(mail.outbox[0].recipients()),
            set([self.test_user.email, self.test_user_2.email]),
            'Verifying the emails are headed to the appropriate recipeients')

        print mail.outbox[0].subject, expected_subject

        self.assertEqual(
            mail.outbox[0].subject,
            expected_subject,
            'Verifying the subject was sent as expected')
