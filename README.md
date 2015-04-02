# django-narrative

Narrative is an a Django app that allows for monitoring of your application's 
business logic.  Think a cross between the 'assert' statement and Nagios for 
your web application.

## Major components


### Classes

- Event - a class for detecting certain occurrences in your application and 
responding to them.  Creates a datum to track events.
- Assertion - a class for detecting and tracking misbehavior in your 
application and taking actions.  Creates and updates Issue records.
- Executor - a class that encapsulates all actual actions; this is how Events 
and Assertions communicate via email to the outside world.  This class can be 
extended to provide interfaces to external services.


### Models

1. Datums - model for representing quick facts, log entries, or general events 
in your system.
2. NarrativeConfig - model for configuring the behavior of narrative
3. Issue - a model recording an 'issue' in your application; an Issue 
corresponds to a failing assertion.
4. ResolutionStep - a particular step taken to address an issue.
5. Solution - the exact sequence of actions taken in a ResolutionStep.
6. AssertionMeta - a model storing meta information about some assertion in 
your system
7. EventMeta - a model storing meta information about some event your system is
watching for


## Installing narrative

1. Install django-narrative
```bash
pip install django-narrative
```
2. Add 'narrative' to your `INSTALLED_APPS` in your settings:
```python
INSTALLED_APPS = (
    # ...
    'narrative',
)
```


### Working with Datums

Datums are a generic way to track notes that your system should keep track of. 
Think of it as internal logging for your application. It's a way of providing 
an internal 'narrative' for what all is occurring in your application. With 
sufficient logging, you can develop Assertions and Events for noticing 
particular large-scale occurrences in your system, and responding 
appropriately.

Datums have 'log levels' associated with them (as defined by the DatumLoglLevel
in narrative/models.py).


#### Quick example

You can you use the `log_datum` function.

```python
from narrative.models import DatumLogLevel, NarrativeConfig, log_datum

log_datum(
    origin='ENCLOSING_SOFTWARE-FUNCTION-METHOD-OR-COMPONENT', 
    datum_name='EXAMPLE', 
    note={'foo': 'bar'}, 
    log_level=DatumLogLevel.INFO
)
```

`NarrativeConfig` contains a field, `minimum_datum_log_level`, which indicates 
the minimum log level that should be stored.  Attempts to save a Datum with a 
lower priority log level will be ignored.

You can create Datums directly, but this is not recommended because it bypasses 
the `NarrativeConfig` `minimum_datum_log_level` check:
```python
datum = Datum.objects.create(
    origin='ENCLOSING_SOFTWARE-FUNCTION-METHOD-OR-COMPONENT', 
    datum_name='EXAMPLE', 
    log_level=DatumLogLevel.INFO
)
datum.set_note({'foo': 'bar'}))
datum.save()
```

### Working with events

Once you've installed narrative, take the following steps to use Events in your 
application:

1. Create an Event subclass
1. Create an EventMeta entry for your Assertion
1. Run `check_events` periodically to check all defined and enabled Assertions


#### Quick example
Suppose you have some step in processing some data.  If it fails, you would 
like to be notified.

You might create an event that looks something like this:

```python
from datetime import datetime

from narrative.events import Event

class ProcessingFailedEvent(Event):
    def detect(self):
        # Return True if the event has occurred
        return your_logic_to_check_failure()     

    @property
    def summary_datum_ttl(self):
        # Track this event for 1 week
        return datetime.timedelta(weeks=1)      

    def instance_summary(self, *args, **kwargs):
        # Do something to separate this occurrence of the event from others
        return {
            'faild_process': when_did_failure_occurr(),
        }

    def event_instance_detected(self, *args, **kwargs):
        self.executor.do_email(
            'devops@example.com', 
            'Processing failed', 
            'Processing failed', 
            '<html>Processing failed</html>'
        )
```

Once your code is ready, create an `EventMeta` in your database to track this 
Event:
```python
EventMeta.objects.create(
    display_name='Failed processing event',
    class_load_path='PYTHON.PATH.TO.ProcessingFailedEvent',
    'enabled': True,
    'check_interval_seconds': 3600  # Check this event every hour
)
```

### Working with assertions

`Assertions` are more heavyweight than `Events`; they are used for 
tracking/dealing with ongoing misbehavior.  To do so, narrative associates each 
failing `Assertion` with an `Issue` in the database, until the `Assertion` 
begins passing again.  The next time the `Assertion` fails, a new issue is 
created to represent this.

Once you've installed narrative, take the following steps to use Assertions in 
your application:

1. Create an Assertion subclass
1. Create an AssertionMeta entry for your Assertion
1. Run `check_assertions` periodically to check all defined and enabled 
Assertions


#### Quick example

Suppose you have an external application component that regularly sends an 
application heartbeat to your system.  You would like to know when the 
heartbeat goes away and what went wrong.

You might create an assertion that looks something like this:
```python
from narrative.assertions import Assertion
from narrative.models import ResolutionStep, Solution

class AgentRunningAssertion(Assertion):
    def check(self):
        return your_logic_to_check_for_missing_heartbeat()

    def diagnostic_case_agent_quiet(self, current_issue, *args, **kwargs):
        return ResolutionStep.objects.create(
            issue=current_issue, solution=Solution.objects.create(plan=plan))
```

Once your code is ready, create an `AssertionMeta` in your database to track 
this Assertion:
```python
AssertionMeta.objects.create(
    display_name='Tracking external Agent',
    class_load_path='PYTHON.PATH.TO.AgentRunningAssertion',
    'enabled': True,
    'check_interval_seconds': 3600  # Check this assertion every hour
)
```

### Working with Issues

To track an ongoing problem, narrative associates each failing `Assertion` with 
an `Issue` in the database, until the `Assertion` begins passing again. The 
next time the `Assertion` fails, a new issue is created to represent this.

The `Issue` model manager has a `current_issues` property to access all 
currently ongoing-issues.

Issues possess an `explain` method for returning a human readable summary of 
the problem.


#### Quick example
```python
>>> print issue.explain()
Failed Assertion: Agent Updates Arriving
Status: Resolved
Created: 2013-11-19 14:07:56.622484
Resolved: 2013-11-19 14:22:57.345463
Resolution Steps:
    ---------------
    Action Type: Exec
    Solution: Diagnostic case name:
        Problem Description:
        Enacted: 2013-11-19 14:07:57.811908
        Status: SUCCESS
        Plan:
            notify_devops
    Reason: None
    ---------------
    Action Type: Pass
    Solution: None
    Reason: Undefined case in escalating response
    ---------------
    Action Type: Pass
    Solution: None
    Reason: Undefined case in escalating response
```
