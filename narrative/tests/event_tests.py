import datetime

from django.test import TestCase

from ..models import Event, EventManager


class TestEventTTLField(TestCase):
    def setUp(self):
        self.mock_utc_now = datetime.datetime(2013, 07, 6, 12, 0, 0)

        def mock_get_utc_now(self_):
            return self.mock_utc_now

        Event.get_utc_now = mock_get_utc_now

    def test_saving_with_ttl_field(self):
        ttl = datetime.timedelta(days=1, hours=12)

        evt = Event.objects.create(origin='mock', event_name='test', ttl=ttl)

        self.assertEqual(evt.expiration_time, self.mock_utc_now + ttl)

    def test_saving_with_no_ttl_field(self):
        evt = Event.objects.create(origin='mock', event_name='test')

        self.assertEqual(evt.expiration_time, None)


class TestEventManager(TestCase):
    def setUp(self):
        self.mock_utc_now = datetime.datetime(2013, 07, 6, 12, 0, 0)

        def mock_get_utc_now(self_):
            return self.mock_utc_now

        Event.get_utc_now = mock_get_utc_now
        EventManager.get_utc_now = mock_get_utc_now

    def test_clear_expired_events(self):
        # Create a bunch of expired events
        expired_event_count = 5
        ttl = datetime.timedelta(hours=1)

        event_list = [
            Event.objects.create(origin='mock', event_name='test', ttl=ttl)
            for i in range(expired_event_count)
        ]
        event_id_list = [evt.id for evt in event_list]

        event_count = Event.objects.count()

        # Wait until 'now' is past the expiration time
        self.mock_utc_now = self.mock_utc_now + ttl + datetime.timedelta(hours=1)

        # Call clear_expired_events
        Event.objects.clear_expired()

        # Verify the events have gone away
        self.assertEqual(
            Event.objects.count(),
            event_count - len(event_list))

        self.assertEqual(
            Event.objects.filter(id__in=event_id_list).count(), 0)
