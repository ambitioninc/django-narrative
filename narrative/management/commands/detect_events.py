from optparse import make_option

from django.core.management.base import BaseCommand

from narrative.checker import detect_enabled_events


class Command(BaseCommand):
    option_list = BaseCommand.option_list + (
        make_option(
            '--verbose', action='store_true', dest='verbose', default=False,
            help='Determins if we should display which events are being checked'), )
    help = (
        'Check all events.')

    def handle(self, *args, **options):
        detect_enabled_events(verbose=options['verbose'])
