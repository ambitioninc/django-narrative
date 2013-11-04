from models import ResolutionStep, ResolutionStepActionType


def make_pass(current_issue, **kwargs):
    return ResolutionStep.objects.create(
        issue=current_issue, action_type=ResolutionStepActionType.PASS,
        **kwargs)
