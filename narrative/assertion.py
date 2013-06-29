import abc

from django.conf import settings
from django.contrib.auth.models import Group
from django.core.mail import EmailMultiAlternatives


### misc utility methods ###
def blast_email(subject, message_txt, message_html, recipients):
    email = EmailMultiAlternatives(
        subject, message_txt, settings.NARRATIVE_REPLY_EMAIL_ADDRESS,
        recipients, headers={'Reply-To': settings.NARRATIVE_REPLY_EMAIL_ADDRESS})

    if message_html:
        email.attach_alternative(message_html, 'text/html')

    email.send()


class Assertion(object):
    __metaclass__ = abc.ABCMeta

    @abc.abstractproperty
    def display_name(self):
        pass

    @abc.abstractmethod
    def check(self):
        pass

    ### Diagnostic related methods ###
    def diagnose(self, *args, **kwargs):
        """
        Run diagnostic cases and find all potential solutions.
        If there are more than one solutions, log them and notify
        the someone.
        If there are no solutions found, notify someone.
        If one solution is found, apply it.
        """
        # Get all diagnostic results
        diagnostic_results = [
            getattr(self, diagnostic_case_name)(*args, **kwargs)
            for diagnostic_case_name in self.diagnostic_cases
        ]

        # Filter out any 'None' results
        solutions = filter(bool, diagnostic_results)

        if len(solutions) == 0:
            # No solution found, notify the admins
            self.do_defer_to_admins('No solutions found')

            return False
        elif len(solutions) > 1:
            # Multiple solutions found, notify the admins
            self.do_defer_multiple_solutions_to_admins(solutions)

            return False
        else:
            # Found a solution; apply it
            self.execute_solution(solutions[0])

            return True

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

    ### Misc utilties for working with solutions ###
    def get_action_handler(self, action_name):
        return 'do_{0}'.format(action_name)

    def validate_solution(self, solution):
        """"
        Examin all of the steps in a solution and verify
        that they are supported by this Assertion.

        If they are not, notify the admins that a bad solution
        was generated.
        """
        for step in solution.plan:
            action, args, kwargs = step

            if not hasattr(self, self.get_action_handler(action)):
                self.do_defer_to_admins('Invalid solution: {0}'.format(str(solution)))
                return False

        else:
            return True

    def execute_solution(self, solution):
        """
        Validate a solution, then step through and execute each of it's steps.
        """
        if self.validate_solution(solution):
            for step in solution.plan:
                action, args, kwargs = step

                getattr(self, self.get_action_handler(action))(*args, **kwargs)

    ### do_* methods for executing particular operations such as notifying individuals ###
    def do_defer_to_admins(self, subject, message, message_html=None, hints=[]):
        admin_group = Group.objects.get(name=settings.NARRATIVE_ADMIN_GROUP_NAME)
        admins = admin_group.user_set.all()

        admin_emails = [admin.email for admin in admins]

        blast_email(subject, message, message_html, admin_emails)

    def do_defer_multiple_solutions_to_admins(self, solutions):
        subject = 'Impasse: "{0}" has Multiple solutions proposed'.format(
            self.display_name)

        message = 'Assertion: {0} ({1}) has {2} proposed solutions'.format(
            self.display_name, self.__class__.__name__, len(solutions))

        hints = map(str, solutions)

        self.do_defer_to_admins(subject, message, hints=hints)

    def do_email(self, address, subject, message_txt, message_html):
        blast_email(subject, message_txt, message_html, [address])
