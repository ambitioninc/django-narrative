from optparse import make_option

from django.core.management.base import BaseCommand

from narrative.models import Datum


class Command(BaseCommand):
    option_list = BaseCommand.option_list + (
        make_option(
            '--verbose', action='store_true', dest='verbose', default=False,
            help='Determins if this command should in verbose mode'),)
    help = (
        'Clear any expired events')

    def handle(self, *args, **options):
        cleared_events = Datum.objects.clear_expired()

        if options['verbose']:
            print 'Cleared data: {0}'.format(cleared_events)
