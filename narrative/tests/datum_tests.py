import datetime
import json
from urllib import urlencode
from django.contrib.auth.models import User
from django.core.urlresolvers import reverse

from django.test import TestCase
from tastypie.models import ApiKey

from ..models import Datum, DatumManager, DatumLogLevel, NarrativeConfig, log_datum


class TestDatumTTLField(TestCase):
    def setUp(self):
        self.mock_utc_now = datetime.datetime(2013, 07, 6, 12, 0, 0)

        def mock_get_utc_now(self_):
            return self.mock_utc_now

        self.original_get_utc_now = Datum.get_utc_now

        Datum.get_utc_now = mock_get_utc_now

    def tearDown(self):
        Datum.get_utc_now = self.original_get_utc_now

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

        self.original_get_utc_now = Datum.get_utc_now

        Datum.get_utc_now = mock_get_utc_now
        DatumManager.get_utc_now = mock_get_utc_now

    def tearDown(self):
        Datum.get_utc_now = self.original_get_utc_now

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


class Test_log_datum(TestCase):
    def test_creating_datum_above_min_log_level(self):
        original_count = Datum.objects.count()

        NarrativeConfig.objects.create(minimum_datum_log_level=DatumLogLevel.DEBUG)

        log_datum(origin='test', datum_name='test_datum', log_level=DatumLogLevel.WARN)

        self.assertEqual(
            original_count + 1,
            Datum.objects.count())

    def test_creating_datum_below_min_log_level(self):
        original_count = Datum.objects.count()

        NarrativeConfig.objects.create(minimum_datum_log_level=DatumLogLevel.DEBUG)

        log_datum(origin='test', datum_name='test_datum', log_level=DatumLogLevel.TRACE)

        self.assertEqual(
            original_count,
            Datum.objects.count())

    def test_creating_datum_with_note(self):
        test_note = {
            'fruit': 'apple',
        }
        NarrativeConfig.objects.create(minimum_datum_log_level=DatumLogLevel.DEBUG)

        log_datum(origin='test', datum_name='test_datum', log_level=DatumLogLevel.INFO, note=test_note)

        new_datum = Datum.objects.order_by('-timestamp')[0]
        self.assertEqual(test_note, new_datum.get_note())


class TestLogApi(TestCase):

    def setUp(self):
        super(TestLogApi, self).setUp()
        self.user = User.objects.create(username='test_user', password='password')
        self.api_key = ApiKey.objects.create(user=self.user)
        self.params = {
            'username': self.user.username,
            'api_key': self.api_key.key,
        }
        self.url_params = urlencode(self.params)
        NarrativeConfig.objects.create(minimum_datum_log_level=DatumLogLevel.DEBUG)

    def test_post_to_tastypie(self):
        """
        Tests posting data to the tastypie api for Datum objects. This api does not
        have the ability to ignore data based on log level. Posting to the log endpoint is preferred
        """
        url = reverse(
            'narrative:api_dispatch_list', kwargs={
                'resource_name': 'datum',
                'api_name': 'api',
            })

        # Verify the api requires authorization
        response = self.client.post(url, data='', content_type='application/json')
        self.assertEqual(401, response.status_code)

        # Add auth params to url
        url = '{0}?{1}'.format(url, self.url_params)

        # Test posting a dict for the note
        post_data = {
            'note': {
                'message': 'test data',
            },
            'datum_name': 'dict test',
            'origin': 'test case',
        }
        response = self.client.post(url, data=json.dumps(post_data), content_type='application/json')
        self.assertEqual(201, response.status_code)
        datum = Datum.objects.order_by('-pk')[0]
        self.assertEqual(post_data.get('note'), datum.get_note())

        # Test posting a string for the note
        post_data = {
            'note': 'test data',
            'datum_name': 'string test',
            'origin': 'test case',
        }
        response = self.client.post(url, data=json.dumps(post_data), content_type='application/json')
        self.assertEqual(201, response.status_code)
        datum = Datum.objects.order_by('-pk')[0]
        self.assertEqual(post_data.get('note'), datum.get_note())

    def test_post_to_log_view(self):
        """
        Tests posting data to the logging api
        """
        url = reverse('narrative.log')

        # Test proper json
        response = self.client.post(url, data='', content_type='application/json')
        self.assertEqual(400, response.status_code)
        self.assertEqual('Invalid json', response.content)

        # Verify format not supported error
        response = self.client.post(url, data='', content_type='application/fake')
        self.assertEqual(400, response.status_code)
        self.assertEqual('Format not supported', response.content)

        # Verify the api requires authorization
        response = self.client.post(url, data='""', content_type='application/json')
        self.assertEqual(401, response.status_code)

        # Add auth params to url
        url = '{0}?{1}'.format(url, self.url_params)

        # Test posting a dict for the note
        post_data = {
            'note': {
                'message': 'test data',
            },
            'datum_name': 'dict test',
            'origin': 'test case',
        }
        response = self.client.post(url, data=json.dumps(post_data), content_type='application/json')
        self.assertEqual(201, response.status_code)
        datum = Datum.objects.order_by('-pk')[0]
        self.assertEqual(post_data.get('note'), datum.get_note())

        # Test posting a string for the note
        post_data = {
            'note': 'test data 2',
            'datum_name': 'string test',
            'origin': 'test case',
        }
        response = self.client.post(url, data=json.dumps(post_data), content_type='application/json')
        self.assertEqual(201, response.status_code)
        datum = Datum.objects.order_by('-pk')[0]
        self.assertEqual(post_data.get('note'), datum.get_note())

        # Test posting log level by integer
        post_data = {
            'note': 'test data 3',
            'datum_name': 'string test',
            'origin': 'test case',
            'log_level': DatumLogLevel.ERROR,
        }
        response = self.client.post(url, data=json.dumps(post_data), content_type='application/json')
        self.assertEqual(201, response.status_code)
        datum = Datum.objects.order_by('-pk')[0]
        self.assertEqual(DatumLogLevel.ERROR, datum.log_level)

        # Test posting log level by name
        post_data = {
            'note': 'test data 4',
            'datum_name': 'string test',
            'origin': 'test case',
            'log_level': 'Warn',
        }
        response = self.client.post(url, data=json.dumps(post_data), content_type='application/json')
        self.assertEqual(201, response.status_code)
        datum = Datum.objects.order_by('-pk')[0]
        self.assertEqual(DatumLogLevel.WARN, datum.log_level)

        # Test posting invalid log level by name
        post_data = {
            'note': 'test data 5',
            'datum_name': 'string test',
            'origin': 'test case',
            'log_level': 'Fake',
        }
        response = self.client.post(url, data=json.dumps(post_data), content_type='application/json')
        self.assertEqual(201, response.status_code)
        datum = Datum.objects.order_by('-pk')[0]
        self.assertEqual(NarrativeConfig.objects.get_minimum_log_level(), datum.log_level)

        # Test posting with lower log level which should be ignored
        post_data = {
            'note': 'test data 6',
            'datum_name': 'string test',
            'origin': 'test case',
            'log_level': 'error',
        }
        response = self.client.post(url, data=json.dumps(post_data), content_type='application/json')
        self.assertEqual(201, response.status_code)

        ignored_post_data = {
            'note': 'ignore me',
            'datum_name': 'string test',
            'origin': 'test case',
            'log_level': 'trace',
        }
        response = self.client.post(url, data=json.dumps(ignored_post_data), content_type='application/json')
        self.assertEqual(200, response.status_code)
        datum = Datum.objects.order_by('-pk')[0]
        self.assertEqual(post_data.get('note'), datum.get_note())
