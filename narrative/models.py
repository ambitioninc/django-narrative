import uuid

from django.db import models


EVENT_STATUS_TYPES = (
    (0, 'Success'),
    (1, 'Failed'),
    (4, 'Unknown'),
)


def get_event_status_by_name(event_status_name):
    try:
        return filter(lambda evt_type: event_status_name == evt_type[1], EVENT_STATUS_TYPES)[0][0]
    except:
        return None


def get_event_status_by_number(event_status_number):
    try:
        return filter(lambda evt_type: event_status_number == evt_type[0], EVENT_STATUS_TYPES)[0][1]
    except:
        return None


class Event(models.Model):
    # When did the event occur
    timestamp = models.DateTimeField(auto_now_add=True)

    # Origin of this event; ie, what piece of software created it
    origin = models.CharField(max_length=64)

    # What event happened; ie, an attempt to connect to a database
    event_name = models.CharField(max_length=64)

    # Target of the event; ie, what database did the connection involve
    event_operand = models.CharField(max_length=64, null=True, blank=True)

    # Event status
    status = models.IntegerField(max_length=16, choices=EVENT_STATUS_TYPES)

    # An ID to tie particular events together
    case_id = models.CharField(max_length=36)

    def save(self, *args, **kwargs):
        if None == self.case_id:
            self.case_id = str(uuid.uuid4())

        super(Event, self).save(*kwargs, **kwargs)


def log_event(status_name, origin, event_name, event_operand=None, case_id=None):
    evt = Event(
        origin=origin, event_name=event_name, event_operand=event_operand,
        status=get_event_status_by_name(status_name), case_id=case_id)

    evt.save()

    return evt
