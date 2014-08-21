from django.contrib.auth.models import Group
from django.conf import settings
from django.core.mail import EmailMultiAlternatives
from django.template.loader import render_to_string


# misc utility methods ---
def blast_email(subject, message_txt, message_html, recipients):
    email = EmailMultiAlternatives(
        subject, message_txt, settings.NARRATIVE_REPLY_EMAIL_ADDRESS,
        recipients, headers={'Reply-To': settings.NARRATIVE_REPLY_EMAIL_ADDRESS})

    if message_html:
        email.attach_alternative(message_html, 'text/html')

    email.send()


class Executor(object):
    def get_action_handler(self, action_name):
        return 'do_{0}'.format(action_name)

    def can_execute(self, action_sequence):
        """"
        Examine all of the steps in an action sequence and verify
        that they are supported by the Executor.
        """
        for step in action_sequence:
            action, kwargs = step

            if not hasattr(self, self.get_action_handler(action)):
                return (False, step)
        else:
            return (True, None)

    def execute(self, action_sequence):
        for step in action_sequence:
            action, kwargs = step

            getattr(self, self.get_action_handler(action))(**kwargs)

    # do_* methods for executing particular operations such as notifying individuals ---
    def do_defer_to_admins(self, subject, message, message_html=None):
        admin_group = Group.objects.get(name=settings.NARRATIVE_ADMIN_GROUP_NAME)
        admins = admin_group.user_set.all()

        admin_emails = [admin.email for admin in admins]

        blast_email(subject, message, message_html, admin_emails)

    def do_defer_multiple_solutions_to_admins(self, resolution_steps, assertion_display_name):
        subject = 'Impasse: "{0}" has Multiple resolution steps proposed'.format(
            assertion_display_name)

        message_kwargs = {
            'assertion_name': assertion_display_name,
            'solution_count': len(resolution_steps),
            'proposed_steps': resolution_steps,
        }

        message = render_to_string(
            'multiple_solution_impasse_message.txt',
            message_kwargs)
        message_html = render_to_string(
            'multiple_solution_impasse_message.html',
            message_kwargs)

        self.do_defer_to_admins(subject, message, message_html)

    def do_email(self, address, subject, message_txt, message_html):
        blast_email(subject, message_txt, message_html, [address])
