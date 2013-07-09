import time

from models import AssertionMeta


def check_enabled(verbose=False):
    """
    Check all enabled assertions.
    """
    check_assertions(AssertionMeta.objects.filter(enabled=True), verbose)


def check_assertions(assertion_meta_list, verbose):
    """
    Check the specified assertions.
    """
    start_time = time.time()

    for assertion_meta in assertion_meta_list:
        if verbose:
            print 'Checking Assertion {0}...'.format(assertion_meta.display_name)

        assertion_class = assertion_meta.load_assertion_class()
        assertion = assertion_class(assertion_meta)
        success = assertion.check_and_diagnose()

        if verbose:
            print '     {0}'.format('PASSED' if success else 'FAILED')

    end_time = time.time()

    duration = end_time - start_time

    if verbose:
        print '-'*20
        print 'Checked {0} assertions in {1} seconds ({2} minutes)'.format(
            len(assertion_meta_list), duration, duration/60.0)
