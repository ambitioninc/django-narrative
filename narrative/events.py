import abc
import datetime
import json

from narrative.models import Datum
from narrative.executor import Executor


class Event(object):
    __metaclass__ = abc.ABCMeta

    def __init__(self, event_meta):
        self.event_meta = event_meta

    @abc.abstractmethod
    def detect(self, *args, **kwargs):
        pass

    @property
    def executor(self):
        return Executor()

    @property
    def origin_name(self):
        return self.__class__.__name__

    ### Misc utilties for working with solutions ###
    def get_utc_now(self):
        return datetime.datetime.utcnow()

    def summary(self, *args, **kwargs):
        """
        Return any additional information we want to associate with this
        event.
        """
        return ''

    def handle_once(self):
        """
        This method is called when the event is first detected.
        """
        pass

    def handle_always(self):
        """
        This method is called everytime the event is detected.
        """
        pass

    def get_or_create_summary_datum(self, *args, **kwargs):
        datum, created = Datum.objects.get_or_create(
            origin=self.origin_name,
            datum_name=self.event_meta.display_name,
            datum_note_json=json.dumps(self.summary(*args, **kwargs)))

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
                self.handle_once(*args, **kwargs)

            self.handle_always(*args, **kwargs)

            return True
        return False
