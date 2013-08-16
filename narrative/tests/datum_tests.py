import datetime

from django.test import TestCase

from ..models import Datum, DatumManager


class TestDatumTTLField(TestCase):
    def setUp(self):
        self.mock_utc_now = datetime.datetime(2013, 07, 6, 12, 0, 0)

        def mock_get_utc_now(self_):
            return self.mock_utc_now

        Datum.get_utc_now = mock_get_utc_now

    def test_saving_with_ttl_field(self):
        ttl = datetime.timedelta(days=1, hours=12)

        evt = Datum.objects.create(origin='mock', datum_name='test', ttl=ttl)

        self.assertEqual(evt.expiration_time, self.mock_utc_now + ttl)

    def test_saving_with_no_ttl_field(self):
        evt = Datum.objects.create(origin='mock', datum_name='test')

        self.assertEqual(evt.expiration_time, None)


class TestDatumManager(TestCase):
    def setUp(self):
        self.mock_utc_now = datetime.datetime(2013, 07, 6, 12, 0, 0)

        def mock_get_utc_now(self_):
            return self.mock_utc_now

        Datum.get_utc_now = mock_get_utc_now
        DatumManager.get_utc_now = mock_get_utc_now

    def test_clear_expired_data(self):
        # Create a bunch of expired data
        expired_datum_count = 5
        ttl = datetime.timedelta(hours=1)

        datum_list = [
            Datum.objects.create(origin='mock', datum_name='test', ttl=ttl)
            for i in range(expired_datum_count)
        ]
        datum_id_list = [evt.id for evt in datum_list]

        # Wait until 'now' is past the expiration time
        self.mock_utc_now = self.mock_utc_now + ttl + datetime.timedelta(hours=1)

        # Create an datum which has not yet expired, and thus should not be deleted
        Datum.objects.create(origin='mock', datum_name='test', ttl=ttl)

        # Create an datum with no ttl (something to be remembered for an eternity)
        Datum.objects.create(origin='mock', datum_name='test')

        datum_count = Datum.objects.count()

        # Call clear_expired_data
        cleared_data = Datum.objects.clear_expired()

        self.assertEqual(
            cleared_data,
            expired_datum_count)

        # Verify the data have gone away
        self.assertEqual(
            Datum.objects.count(),
            datum_count - expired_datum_count)

        self.assertEqual(
            Datum.objects.filter(id__in=datum_id_list).count(), 0)
