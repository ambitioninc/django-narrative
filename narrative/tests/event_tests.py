from unittest import TestCase

from ..models import Datum
from ..events import Event


class Test_get_or_create_summary_datum(TestCase):
    def setUp(self):
        Datum.objects.all().delete()

        self.detect_return_value = False

        class TestEvent(Event):
            @property
            def event_name(self):
                return 'Test Event'

            def detect(self_, *args, **kwargs):
                self.detect_return_value

        self.event = TestEvent()

    def test_first_occurence(self):
        self.assertTrue(self.event.get_or_create_summary_datum())

    def test_no_duplicates(self):
        self.event.get_or_create_summary_datum()
        self.assertFalse(self.event.get_or_create_summary_datum())


class Test_detect_and_handle(TestCase):
    def setUp(self):
        Datum.objects.all().delete()

        self.detect_return_value = False

        self.handle_once_called = False
        self.handle_always_called = False

        class TestEvent(Event):
            @property
            def event_name(self):
                return 'Test Event'

            def detect(self_, *args, **kwargs):
                return self.detect_return_value

            def handle_once(self_):
                self.handle_once_called = True

            def handle_always(self_):
                self.handle_always_called = True

        self.event = TestEvent()

    def test_detect_false(self):
        """
        Verify that when detect returns False,
        1) no datums are created
        2) handle_once is not called
        3) handle_always is not called
        """
        self.detect_return_value = False

        original_datum_count = Datum.objects.filter(
            origin=self.event.origin_name).count()

        self.event.detect_and_handle()

        self.assertEqual(
            original_datum_count,
            Datum.objects.filter(origin=self.event.origin_name).count())
        self.assertFalse(self.handle_once_called)
        self.assertFalse(self.handle_always_called)

    def test_first_detection(self):
        """
        Verify that when detect returns True the first time,
        1) a summary datum is created
        2) handle_once is called
        3) handle_always is called
        """
        self.detect_return_value = True

        original_datum_count = Datum.objects.filter(
            origin=self.event.origin_name).count()

        self.event.detect_and_handle()

        self.assertEqual(
            original_datum_count + 1,
            Datum.objects.filter(origin=self.event.origin_name).count())
        self.assertTrue(self.handle_once_called)
        self.assertTrue(self.handle_always_called)

    def test_second_detection(self):
        """
        Verify that when detect returns True the second time,
        1) a summary datum is *not* created
        2) handle_once is *not* called
        3) handle_always is called
        """
        self.detect_return_value = True

        # Call once to prep the database
        self.event.detect_and_handle()

        original_datum_count = Datum.objects.filter(
            origin=self.event.origin_name).count()

        self.handle_once_called = False
        self.handle_always_called = False

        self.event.detect_and_handle()

        self.assertEqual(
            original_datum_count,
            Datum.objects.filter(origin=self.event.origin_name).count())
        self.assertFalse(self.handle_once_called)
        self.assertTrue(self.handle_always_called)
