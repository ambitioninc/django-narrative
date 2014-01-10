import abc
import copy
import datetime
import json

from narrative.models import Datum
from narrative.executor import Executor


class Event(object):
    __metaclass__ = abc.ABCMeta

    def __init__(self, event_meta):
        self.event_meta = event_meta

    @property
    def args(self):
        return self.event_meta.get_args()

    @abc.abstractmethod
    def detect(self, *args, **kwargs):
        pass

    @abc.abstractmethod
    def instance_summary(self, *args, **kwargs):
        """
        Return any additional information we want to associate with this
        occurrence of this event; this is needed to separate this occurrence
        from other occurrences of the same event.
        """
        return {}

    @property
    def summary_datum_ttl(self):
        return None

    @property
    def executor(self):
        return Executor()

    @property
    def origin_name(self):
        return self.__class__.__name__

    def get_utc_now(self):
        return datetime.datetime.utcnow()

    def event_instance_detected(self):
        """
        This method is called when the event instance is first detected.
        """
        pass

    def get_or_create_summary_datum(self, *args, **kwargs):
        """
        Create the summary datum to represent this occurrence of this event.
        """
        datum_kwargs = {
            'origin': self.origin_name,
            'datum_name': self.event_meta.display_name,
            'datum_note_json': json.dumps(self.instance_summary(*args, **kwargs)),
        }

        defaults = copy.copy(datum_kwargs)

        datum_kwargs['defaults'] = defaults

        # If this event has defined a TTL for it's summary datum, then
        # respect it.
        if self.summary_datum_ttl:
            defaults['ttl'] = self.summary_datum_ttl

        datum, created = Datum.objects.get_or_create(**datum_kwargs)

        return created

    def detect_and_handle(self, *args, **kwargs):
        """
        Check if the event has occured.  If so,
        check if a datum already exists noting this event.  If not,
        create a datum, and perform any needed handling of the event.
        """
        if self.detect(*args, **kwargs):
            created = self.get_or_create_summary_datum(*args, **kwargs)

            if created:
                self.event_instance_detected(*args, **kwargs)

            return True
        return False
