from django.conf import settings
from django.contrib.auth.models import User, Group
from django.test import TestCase

from ..assertion import ModelAssertion
from ..models import AssertionMeta, ModelIssue, IssueStatusType, IssueResolutionStep, IssueResolutionStepActionType

from test_project.models import TestModel


class ModelAssertionTests(TestCase):
    def setUp(self):
        self.mock_models = []
        self.failing_models = []

        self.diagnosed_records = []
        self.post_recovery_records = []

        class TestModelAssertion(ModelAssertion):
            @property
            def queryset(self_):
                return self.mock_models

            def check_record(self_, record, *args, **kwargs):
                return record not in self.failing_models

            def diagnose(self_, *args, **kwargs):
                self.diagnosed_records.append(kwargs.pop('record'))
                super(TestModelAssertion, self_).diagnose(*args, **kwargs)

            def diagnostic_case_pass(self_, *args, **kwargs):
                return IssueResolutionStep(action_type=IssueResolutionStepActionType.PASS)

            def diagnostic_case_pass_2(self_, *args, **kwargs):
                return IssueResolutionStep(action_type=IssueResolutionStepActionType.PASS)

            def post_recovery_cleanup(self_, *args, **kwargs):
                self.post_recovery_records.append(kwargs.pop('record'))

        self.assertion_meta = AssertionMeta.objects.create(
            display_name='Mock model assertion', assertion_load_path='foo.bar', enabled=True)

        self.assertion = TestModelAssertion(self.assertion_meta)

        # Set up the narrative admin group
        admin_group, created = Group.objects.get_or_create(
            name=settings.NARRATIVE_ADMIN_GROUP_NAME)
        self.test_user = User.objects.create(
            username='test_user', password='test_user', email='test_user@example.com')
        self.test_user_2 = User.objects.create(
            username='test_user_2', password='test_user_2', email='test_user_2@example.com')

        admin_group.user_set.add(self.test_user)
        admin_group.user_set.add(self.test_user_2)

    def test_check_and_diagnose(self):
        """
        Verify that records failing the check_record method
        are individually passed into diagnose.  Also verify
        that model issues are created and resolved appropriately.
        """
        # Create some model records
        self.mock_models = [TestModel.objects.create() for i in range(10)]
        # Select some of the models to fail
        self.failing_models = [self.mock_models[idx] for idx in range(0, len(self.mock_models), 2)]

        # Call check
        self.assertion.check_and_diagnose()

        # Verify that the records who fail are passed into diagnose
        self.assertEqual(
            set(self.diagnosed_records),
            set(self.failing_models),
            'Diagnose should be called on the failing models')

        model_issue_list = ModelIssue.objects.all()

        # Verify that model issues are created for the records who fail
        self.assertEqual(
            set([model_issue.model for model_issue in model_issue_list]),
            set(self.failing_models),
            'Models referenced by issues should match the failing models')

        # Verify that the proposed IssueResolutionSteps are all PASS
        issue_resolution_step_list = IssueResolutionStep.objects.all()

        self.assertEqual(
            set([isr.action_type for isr in issue_resolution_step_list]),
            set([IssueResolutionStepActionType.PASS]),
            'Should be all PASS')

        # Verify that all of the model issues are IMPASSE
        self.assertEqual(
            set([model_issue.status for model_issue in model_issue_list]),
            set([IssueStatusType.IMPASSE]),
            'All of the model issues should have an IMPASSE status')

        # Verify all of the model issues reference the test assertion
        self.assertEqual(
            set([model_issue.failed_assertion for model_issue in model_issue_list]),
            set([self.assertion_meta]),
            'All of the model issues should reference the test asserrion meta')

        ### Now, fake all models passing and verify the system recovers appropriately ###
        self.previously_failing_models = self.failing_models
        self.failing_models = []

        self.assertion.check_and_diagnose()

        model_issue_list = ModelIssue.objects.all()

        # Verify that post_recovery_cleanup is called on each record that now passes
        self.assertEqual(
            set(self.post_recovery_records),
            set(self.previously_failing_models),
            'Post recovery should have been called on all previously failing records')

        # Verify that all issues are now marked as resolved
        self.assertEqual(
            set([model_issue.status for model_issue in model_issue_list]),
            set([IssueStatusType.RESOLVED]),
            'All of the model issues should now have a Resolved status')
