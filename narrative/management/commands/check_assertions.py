from optparse import make_option

from django.core.management.base import BaseCommand

from narrative.checker import check_enabled


class Command(BaseCommand):
    option_list = BaseCommand.option_list + (
        make_option(
            '--verbose', action='store_true', dest='verbose', default=False,
            help='Determins if we should display which '
                 'assertions are being checked'),)
    help = (
        'Check all enabled assertions.')

    def handle(self, *args, **options):
        check_enabled(verbose=options['verbose'])
