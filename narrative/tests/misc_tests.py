from django.test import TestCase

from ..models import AssertionMeta, Solution, Issue, ResolutionStep, ResolutionStepActionType


class IssueTests(TestCase):
    def setUp(self):
        self.assertion_meta = AssertionMeta.objects.create(
            display_name='Test Assertion', assertion_load_path='foo.bar')

    def test_steps_matching_solution(self):
        """
        Test that the steps_matching_solution appropriately
        returns the steps that match the specified solution.
        """
        issue = Issue(failed_assertion=self.assertion_meta)
        issue.save()

        test_solution_1 = Solution(plan=[
            ('notify_client_it', {
                'subject': 'foo',
                'message': 'bar',
                }),
            ('do_email', {})
        ])
        test_solution_1.save()
        isr_1 = ResolutionStep.objects.create(solution=test_solution_1, issue=issue)

        test_solution_2 = Solution.objects.create(plan=[
            ('notify_client_it', {
                'subject': 'foo_2',
                'message': 'bar_2',
                }),
            ('do_email', {})
        ])
        test_solution_2.save()
        isr_2 = ResolutionStep.objects.create(solution=test_solution_2, issue=issue)

        test_solution_3 = Solution.objects.create(plan=[
            ('do_something_else', {}),
        ])
        test_solution_3.save()
        ResolutionStep.objects.create(solution=test_solution_3, issue=issue)

        ResolutionStep.objects.create(action_type=ResolutionStepActionType.PASS, issue=issue)

        # Example plan to match
        target_solution = Solution.objects.create(plan=[
            ('notify_client_it', {}),
            ('do_email', {})
        ])

        self.assertEqual(
            set(issue.steps_matching_plan(target_solution.get_plan())),
            set([isr_1, isr_2]),
            'There should only be two matching issue resolution steps')
