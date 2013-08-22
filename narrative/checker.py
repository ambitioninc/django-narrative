import time

from models import AssertionMeta, EventMeta


def check_enabled_assertions(verbose=False):
    """
    Check all enabled assertions.
    """
    process_periodicals(
        AssertionMeta.objects.filter(enabled=True),
        verbose, process_method_name='check_and_diagnose')


def detect_enabled_events(verbose=False):
    """
    Check all enabled events.
    """
    process_periodicals(
        EventMeta.objects.filter(enabled=True),
        verbose, process_method_name='detect_and_handle', true_copy='DETECTED', false_copy='NOT DETECTED')


def process_periodicals(
        periodical_meta_list, verbose, process_method_name,
        true_copy='PASSED', false_copy='FAILED'):
    """
    Check the specified periodicals.
    """
    start_time = time.time()

    check_count = 0

    for periodical_meta in periodical_meta_list:
        if periodical_meta.should_check():
            if verbose:
                print 'Checking {0} {1}...'.format(
                    periodical_meta.__class__.__name__,
                    periodical_meta.display_name)

                periodical_class = periodical_meta.load_class()

                if periodical_class:
                    periodical_obj = periodical_class(periodical_meta)
                    success = getattr(periodical_obj, process_method_name)()

                    if verbose:
                        print '     {0}'.format(true_copy if success else false_copy)
                else:
                    print '     Error loading class "{0}"'.format(
                        periodical_meta.class_load_path)

            check_count += 1

    end_time = time.time()

    duration = end_time - start_time

    if verbose:
        print '-'*20
        print 'Checked {0} object in {1} seconds ({2} minutes)'.format(
            check_count, duration, duration/60.0)
