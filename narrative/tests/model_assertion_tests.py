from django.conf import settings
from django.contrib.auth.models import User, Group
from django.test import TestCase

from ..assertions import ModelAssertion
from ..models import AssertionMeta, Issue, ModelIssue, IssueStatusType, ResolutionStep, ResolutionStepActionType

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
                return ResolutionStep.objects.create(issue=self.issue, action_type=ResolutionStepActionType.PASS)

            def diagnostic_case_pass_2(self_, *args, **kwargs):
                return ResolutionStep.objects.create(issue=self.issue, action_type=ResolutionStepActionType.PASS)

            def post_recovery_cleanup(self_, *args, **kwargs):
                self.post_recovery_records.append(kwargs.pop('record'))

        self.assertion_meta = AssertionMeta.objects.create(
            display_name='Mock model assertion', class_load_path='foo.bar', enabled=True)

        self.assertion = TestModelAssertion(self.assertion_meta)
        self.issue = Issue.objects.create(failed_assertion=self.assertion_meta)

        # Set up the narrative admin group
        admin_group, created = Group.objects.get_or_create(
            name=settings.NARRATIVE_ADMIN_GROUP_NAME)
        self.test_user = User.objects.create(
            username='test_user', password='test_user', email='test_user@example.com')
        self.test_user_2 = User.objects.create(
            username='test_user_2', password='test_user_2', email='test_user_2@example.com')

        admin_group.user_set.add(self.test_user)
        admin_group.user_set.add(self.test_user_2)

        # Create some model records
        self.mock_models = [TestModel.objects.create() for i in range(10)]

    def test_check_and_diagnose(self):
        """
        Verify that records failing the check_record method
        are individually passed into diagnose.  Also verify
        that model issues are created and resolved appropriately.
        """
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

        # Verify that the proposed ResolutionSteps are all PASS
        issue_resolution_step_list = ResolutionStep.objects.all()

        self.assertEqual(
            set([isr.action_type for isr in issue_resolution_step_list]),
            set([ResolutionStepActionType.PASS]),
            'Should be all PASS')

        # Verify that all of the model issues have an IMPASSE status
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

    def test_check_and_diagnose_with_preeixsting_wontfix(self):
        # Select some of the models to fail
        self.failing_models = [self.mock_models[idx] for idx in range(0, len(self.mock_models), 2)]

        self.wont_fix_model = self.failing_models[0]

        # Now, create a ModelIssue and mark it as WONT_FIX and make sure nothing is done
        # with that issue/model but others work fine
        self.wont_fix_issue = ModelIssue.objects.create(
            failed_assertion=self.assertion_meta, model=self.wont_fix_model,
            status=IssueStatusType.WONT_FIX)

        # Call check
        self.assertion.check_and_diagnose()

        # Verify that the records who fail (but are not marked as WONT_FIX) are passed into diagnose
        self.assertEqual(
            set(self.diagnosed_records),
            set(self.failing_models[1:]),
            'Diagnose should be called on the failing models')

        model_issue_list = ModelIssue.objects.exclude(model_id=self.wont_fix_model.id)

        # Verify that model issues are created for the records who fail
        self.assertEqual(
            set([model_issue.model for model_issue in model_issue_list]),
            set(self.failing_models[1:]),
            'Models referenced by issues should match the failing models')

        # Verify that the proposed ResolutionSteps are all PASS
        issue_resolution_step_list = ResolutionStep.objects.all()

        self.assertEqual(
            set([isr.action_type for isr in issue_resolution_step_list]),
            set([ResolutionStepActionType.PASS]),
            'Should be all PASS')

        # Verify that all of the model issues (excluding the WONT_FIX) have an IMPASSE status
        self.assertEqual(
            set([model_issue.status for model_issue in model_issue_list]),
            set([IssueStatusType.IMPASSE]),
            'All of the model issues should have an IMPASSE status')

        # Verify that the wont_fix issue still has status of WONT_FIX
        self.assertEqual(
            ModelIssue.objects.get(id=self.wont_fix_issue.id).status,
            IssueStatusType.WONT_FIX,
            'Wont fix issue should still be marked as WONT_FIX')

        # Verify all of the model issues reference the test assertion
        self.assertEqual(
            set([model_issue.failed_assertion for model_issue in model_issue_list]),
            set([self.assertion_meta]),
            'All of the model issues should reference the test asserrion meta')
