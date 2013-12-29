django-narrative
================

Narrative is an a Django app that allows for monitoring of your application's business logic.  Think a cross between the 'assert' statement and Nagios for your web application.

# Major components #


## Classes ##

1. Event - a class for decting certain occurrences in your application and responding to them.  Creates a datum to track events.
2. Assertion - a class for detecting and tracking misbehavior in your application and taking actions.  Creates and updates Issue records.
3. Executor - a class that encapsulates all actual actions; this is how Events and Assertions communicate via email to the outside world.  This class
can be extended to provide interfaces to externa services.


## Models ##

1. Datums - model for representing quick facts, log entries, or general events in your system.
2. NarrativeConfig - model for configuring the behavior of narrative
3. Issue - a model recording an 'issue' in your application; an Issue corresponds to a failing aassertion.
4. ResolutionStep - a particular step taken to address an issue.
5. Solution - the exact sequence of actions taken in a ResolutionStep.
6. AssertionMeta - a model storing meta information about some assertion in your system
7. EventMeta - a model storing meta information about some event your system is watching for


# Installing narrative #

1) Install django-narrative
2) Add 'narrative' to your `INSTALLED_APPS`


## Working with Datums ##

Datums are a generic way to track notes that your system should keep track of.  Think of it as internal logging for your application.  It's a way of providing an internal 'narrative'
for what all is occurring in your application.  With sufficient logging, you can develop Assertions and Events for noticing particular large-scale occurrences in your system, and
responding appropriately.

Datums have 'log levels' associated with them (as defined by the DatumLoglLevel in narrative/models.py).


### Quick example ###

You can you use the `log_datum` function.

    from narrative.models import DatumLogLevel, NarrativeConfig, log_datum

    log_datum(origin='ENCLOSING_SOFTWARE-FUNCTION-METHOD-OR-COMPONENT', datum_name='EXAMPLE', note={'foo': 'bar'}, log_level=DatumLogLevel.INFO)

`NarrativeConfig` contains a field, `minimum_datum_log_level`, which indicates the minimum log level that should be stored.  Attempts to save a Datum with a lower priority log level will
be ignored.

You can create Datums directly, but this is not recommended because it bypasses the `NarrativeConfig` `minimum_datum_log_level` check:

    datum = Datum.objects.create(origin='ENCLOSING_SOFTWARE-FUNCTION-METHOD-OR-COMPONENT', datum_name='EXAMPLE', log_level=DatumLogLevel.INFO)
    datum.set_note({'foo': 'bar'}))
    datum.save()


## Working with assertions ##

Once your've installed narrative, take the following steps to use Assertions in your application:
1) Create an Assertion subclass
2) Create an AssertionMeta entry for your Assertion
3) Run `check_assertions` periodically to check all defined and enabled Assertions


### Quick example ###

Suppose you have an external application component that regularly sends an application heartbeat to your system.  You would like to know when the heartbeat goes away and what went wrong.

You might create an assertion that looks something like this:

    from narrative.assertions import Assertion
    from narrative.models import ResolutionStep, Solution

    class AgentRunningAssertion(Assertion):
        def check(self):
            return your_logic_to_check_for_missing_heartbeat()

        def diagnostic_case_agent_quiet(self, current_issue, *args, **kwargs):
            return ResolutionStep.objects.create(
                issue=current_issue, solution=Solution.objects.create(plan=plan))

Once your code is ready, create an `AssertionMeta` in your database to track this Assertion:

    AssertionMeta.objects.create(
        display_name='Tracking external Agent',
        class_load_path='PYTHON.PATH.TO.AgentRunningAssertion',
        'enabled': True,
        'check_interval_seconds': 3600)         # Check this assertion every hour


## Working with events ##

Once your've installed narrative, take the following steps to use Events in your application:
1) Create an Event subclass
2) Create an EventMeta entry for your Assertion
3) Run `check_events` periodically to check all defined and enabled Assertions


### Quick example ###

Suppose you have some step in processing some data.  If it fails, you would like to be notified.

You might create an event that looks something like this:

    from datetime import datetime

    from narrative.events import Event

    class ProcessingFailedEvent(Event):
        def detect(self):
            return your_logic_to_check_failure()     # Return True if the event has occurred

        @property
        def summary_datum_ttl(self):
            return datetime.timedelta(weeks=1)      # Track this event for 1 week

        def instance_summary(self, *args, **kwargs):
            return {
                'faild_process': when_did_failure_occurr(),     # Do something to separate this occurrence of the event from others
            }

        def event_instance_detected(self, *args, **kwargs):
            self.executor.do_email('devops@example.com', 'Processing failed', 'Processing failed', '<html>Processing failed</html>')

Once your code is ready, create an `EventMeta` in your database to track this Event:

    EventMeta.objects.create(
        display_name='Failed processing event',
        class_load_path='PYTHON.PATH.TO.ProcessingFailedEvent',
        'enabled': True,
        'check_interval_seconds': 3600)         # Check this event every hour
