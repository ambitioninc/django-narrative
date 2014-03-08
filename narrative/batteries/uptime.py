import datetime

from django.conf import settings

from narrative.models import Datum, DatumLogLevel, log_datum


class UptimeEventTypes:
    UP = 0
    DOWN = 1


heartbeat_details = {
    'origin': 'external_heartbeat',
    'datum_name': 'beat',
    'ttl': getattr(settings, 'NARRATIVE_HEARBEAT_TTL', None),
}


def create_heartbeat(get_utc_now=datetime.datetime.utcnow):
    """
    Create a datum recording the heartbeat, if sufficient time
    (as specified by NARRATIVE_HEARTBEAT_MIN_INTERVAL) has passed
    since the last heartbeat was created.
    """
    start_of_non_creation_window = get_utc_now() - settings.NARRATIVE_HEARTBEAT_MIN_INTERVAL

    if not Datum.objects.filter(
            origin=heartbeat_details['origin'],
            datum_name=heartbeat_details['datum_name'],
            timestamp__gte=start_of_non_creation_window).exists():
        # No recent heartbeat, so create a new one
        log_datum(
            origin=heartbeat_details['origin'],
            datum_name=heartbeat_details['datum_name'],
            ttl=heartbeat_details['ttl'],
            log_level=DatumLogLevel.INFO)


def compute_interval_list(time_list):
    """
    Given a series of times, return the intervals between them as well
    as the median interval.

    NOTE: assumes that the time_list is sorted in ascending order.
    """
    interval_list = [time_list[idx] - time_list[idx - 1] for idx in range(1, len(time_list))]
    interval_list_len = len(interval_list)

    return interval_list, interval_list[int(interval_list_len / 2)]


def detect_temporal_clusters(time_list):
    """
    Break the times in the time_list into a series of clusters based
    on changes in the median interval between times.

    The ideas is that we look at the intervals between elements in the
    list, take the median interval, then tweat any interval much bigger
    than that as indicating the start of a new cluster.

    Note: assumes that time_list is sorted in ascending order.
    """
    time_list_len = len(time_list)

    if time_list_len > 1:
        interval_list, new_cluster_threshold = compute_interval_list(time_list)

        clusters = [[time_list[0]]]

        for idx in range(1, len(time_list)):
            if interval_list[idx - 1] > new_cluster_threshold:
                # The interval past is too much; start a new cluster
                clusters.append([time_list[idx]])
            else:
                # This time was close enough to the last one to be in
                # in the same cluster
                clusters[-1].append(time_list[idx])

        return clusters, new_cluster_threshold
    elif time_list_len == 1:
        return [time_list], 0
    return [], 0


def get_uptime_history(utcnow=datetime.datetime.utcnow):
    """
    Return a history of uptime data; the data are in descending order,
    going from most recent to least recent.  Each datum is a tuple:
    (UP/Down datetime) where UP/DOWN is a value from UptimeEventType.
    """
    def unix_timestamp(dt):
        return int(dt.strftime('%s'))

    def from_unix_timestamp(timestamp):
        return datetime.datetime.utcfromtimestamp(timestamp)

    # Get a list of all heartbeats since the pusher went dark
    heartbeat_times = Datum.objects.filter(
        origin=heartbeat_details['origin'], datum_name=heartbeat_details['datum_name']).values('timestamp')

    # Pull out the heartbeat times
    heartbeat_times = [
        unix_timestamp(ht['timestamp']) for ht in heartbeat_times
    ]

    # Put in ascending order
    heartbeat_times.sort(reverse=False)

    clusters, threshold = detect_temporal_clusters(heartbeat_times)

    if len(clusters) > 0:
        # Put in descending order of clusters; the elements within the clusters
        # are still in ascending order.
        heartbeat_times.reverse()

        history = []

        for idx in range(0, len(clusters) - 1):
            cluster = clusters[idx]
            uptime = from_unix_timestamp(cluster[0])
            downtime = from_unix_timestamp(cluster[-1])

            history.append((UptimeEventTypes.UP, uptime))
            history.append((UptimeEventTypes.DOWN, downtime))

        # There is an edge case with the last cluster, where this is the most recent heartbeat
        # and it was in the last few seconds; in this case, we cannot assume this was a downtime datum
        last_cluster = clusters[-1]
        uptime = from_unix_timestamp(last_cluster[0])
        downtime = from_unix_timestamp(last_cluster[-1])

        history.append((UptimeEventTypes.UP, uptime))

        if (utcnow() - downtime).total_seconds() < threshold:
            history.append((UptimeEventTypes.DOWN, downtime))

        return history
    else:
        return [(UptimeEventTypes.UP, utcnow())]


def time_site_came_up(utcnow=datetime.datetime.utcnow):
    return get_uptime_history(utcnow=utcnow)[0][1]
