import datetime
from unittest import TestCase

from ..models import Datum, EventMeta
from ..events import Event


class Test_get_or_create_summary_datum(TestCase):
    def setUp(self):
        Datum.objects.all().delete()

        self.detect_return_value = False

        self.mock_ttl = None

        class TestEvent(Event):
            @property
            def summary_datum_ttl(self_):
                return self.mock_ttl

            @property
            def event_name(self):
                return 'Test Event'

            def detect(self_, *args, **kwargs):
                self.detect_return_value

        self.event_meta, created = EventMeta.objects.get_or_create(
            display_name='Fancy event', class_load_path='foo.bar')
        self.event = TestEvent(self.event_meta)

    def test_first_occurence(self):
        self.assertTrue(self.event.get_or_create_summary_datum())

    def test_no_duplicates(self):
        self.event.get_or_create_summary_datum()
        self.assertFalse(self.event.get_or_create_summary_datum())

    def test_with_summary_datum_ttl(self):
        self.mock_ttl = datetime.timedelta(hours=1)
        self.assertTrue(self.event.get_or_create_summary_datum())

        expected_expiration_time = datetime.datetime.utcnow() + self.mock_ttl
        actual_expiration_time = Datum.objects.all()[0].expiration_time
        difference_in_seconds = abs((
            expected_expiration_time - actual_expiration_time).total_seconds())

        self.assertTrue(difference_in_seconds < 1)

    def test_without_summary_datum_ttl(self):
        self.mock_ttl = None
        self.assertTrue(self.event.get_or_create_summary_datum())
        self.assertEqual(
            None,
            Datum.objects.all()[0].expiration_time)


class Test_detect_and_handle(TestCase):
    def setUp(self):
        Datum.objects.all().delete()

        self.detect_return_value = False

        self.event_instance_detected_called = False

        class TestEvent(Event):
            @property
            def event_name(self):
                return 'Test Event'

            def detect(self_, *args, **kwargs):
                return self.detect_return_value

            def event_instance_detected(self_):
                self.event_instance_detected_called = True

        self.event_meta, created = EventMeta.objects.get_or_create(
            display_name='Fancy event', class_load_path='foo.bar')
        self.event = TestEvent(self.event_meta)

    def test_detect_false(self):
        """
        Verify that when detect returns False,
        1) no datums are created
        2) event_instance_detected is not called
        """
        self.detect_return_value = False

        original_datum_count = Datum.objects.filter(
            origin=self.event.origin_name).count()

        self.event.detect_and_handle()

        self.assertEqual(
            original_datum_count,
            Datum.objects.filter(origin=self.event.origin_name).count())
        self.assertFalse(self.event_instance_detected_called)

    def test_first_detection(self):
        """
        Verify that when detect returns True the first time,
        1) a summary datum is created
        2) event_instance_detected is called
        """
        self.detect_return_value = True

        original_datum_count = Datum.objects.filter(
            origin=self.event.origin_name).count()

        self.event.detect_and_handle()

        self.assertEqual(
            original_datum_count + 1,
            Datum.objects.filter(origin=self.event.origin_name).count())
        self.assertTrue(self.event_instance_detected_called)

    def test_second_detection(self):
        """
        Verify that when detect returns True the second time,
        1) a summary datum is *not* created
        2) event_instance_detected is *not* called
        """
        self.detect_return_value = True

        # Call once to prep the database
        self.event.detect_and_handle()

        original_datum_count = Datum.objects.filter(
            origin=self.event.origin_name).count()

        self.event_instance_detected_called = False

        self.event.detect_and_handle()

        self.assertEqual(
            original_datum_count,
            Datum.objects.filter(origin=self.event.origin_name).count())
        self.assertFalse(self.event_instance_detected_called)
