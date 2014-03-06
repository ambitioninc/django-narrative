import datetime
import unittest

from uptime import detect_temporal_clusters, heartbeat_details, get_uptime_history, UptimeEventTypes
from narrative.models import Datum


def simulate_uptime(start_time, end_time, interval=None):
    """
    Create the needed heartbeats to simulate uptime during the
    specified time range.
    """
    interval = interval or datetime.timedelta(seconds=20)

    interval_seconds = int(interval.total_seconds())

    for beat_time in range(
            int(start_time.strftime('%s')),
            int(end_time.strftime('%s')) + interval_seconds,
            interval_seconds):
        # Create an datum
        evt = Datum.objects.create(
            origin=heartbeat_details['origin'], datum_name=heartbeat_details['datum_name'])
        # Reset it's creation timestamp for testing purposes
        evt.timestamp = datetime.datetime.utcfromtimestamp(beat_time)
        evt.save()


class Test_detect_temporal_clusters(unittest.TestCase):
    def test_3_clusters(self):
        time_list = [1, 2, 3, 14, 15, 16, 17, 18, 45, 46, 47, 48, 49, 50]

        self.assertEqual(
            detect_temporal_clusters(time_list)[0],
            [[1, 2, 3], [14, 15, 16, 17, 18], [45, 46, 47, 48, 49, 50]],
            'There should be three clusters')

    def test_1_element(self):
        """
        Verify that we properly handle the case where there is only 1 element.
        """
        time_list = [1]

        self.assertEqual(
            detect_temporal_clusters(time_list)[0],
            [time_list],
            'There should be one cluster')


class Test_get_uptime_events(unittest.TestCase):
    def test_up_down_history(self):
        # Simulate 2 periods of downtime
        simulation_start_time = datetime.datetime(2013, 7, 15, 12, 0, 0)
        first_time_down_start = simulation_start_time + datetime.timedelta(minutes=10)
        first_time_down_end = first_time_down_start + datetime.timedelta(minutes=10)
        second_time_down_start = first_time_down_end + datetime.timedelta(minutes=10)
        second_time_down_end = second_time_down_start + datetime.timedelta(minutes=10)
        mock_now = second_time_down_end + datetime.timedelta(minutes=10)

        simulate_uptime(simulation_start_time, first_time_down_start)
        simulate_uptime(first_time_down_end, second_time_down_start)
        simulate_uptime(second_time_down_end, mock_now)

        expected_uptime_events = [
            (UptimeEventTypes.UP, simulation_start_time),
            (UptimeEventTypes.DOWN, first_time_down_start),
            (UptimeEventTypes.UP, first_time_down_end),
            (UptimeEventTypes.DOWN, second_time_down_start),
            (UptimeEventTypes.UP, second_time_down_end),
        ]

        self.assertEqual(
            expected_uptime_events,
            get_uptime_history())

    def test_no_events(self):
        # Make sure we have no heartbeats
        Datum.objects.filter(
            origin=heartbeat_details['origin'],
            datum_name=heartbeat_details['datum_name']).delete()

        mock_now = datetime.datetime(2013, 8, 21)

        expected_uptime_events = [
            (UptimeEventTypes.UP, mock_now),
        ]

        self.assertEqual(
            expected_uptime_events,
            get_uptime_history(utcnow=lambda: mock_now))
