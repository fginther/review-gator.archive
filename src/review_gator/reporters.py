import datetime
import os

import pytz

try:
    from typing import Dict, List, Text
except ImportError:
    pass


class ReviewGatorReporter(object):
    """Super-class that ReviewGator reporters should inherit from."""

    def process_data(self, data):  # type: (Dict) -> None
        """Perform reporting with the given data dict."""
        raise NotImplementedError

    @classmethod
    def enabled(cls):  # type: () -> bool
        """A bool indicating whether this reporting class should be called."""
        return False


class InfluxDBTotalAgeReporter(ReviewGatorReporter):
    """
    When enabled, report the sum of the ages of reviews to InfluxDB.

    Will disable itself if either (a) the influxdb library isn't importable,
    or (b) the REVIEW_GATOR_METRIC_NAME environment variable isn't set.

    The REVIEW_GATOR_METRIC_NAME environment variable is used to determine the
    metric name under which results will be submitted.

    The following environment variables will be used to configure the InfluxDB
    client if present (falling back to the client's defaults otherwise):

    * INFLUXDB_HOST
    * INFLUXDB_PORT
    * INFLUXDB_USERNAME
    * INFLUXDB_PASSWORD
    * INFLUXDB_DATABASE
    """

    influxdb_args = ['host', 'port', 'username', 'password', 'database']

    def __init__(self):  # type: () -> None
        self.now = pytz.utc.localize(datetime.datetime.utcnow())

        from influxdb import InfluxDBClient, SeriesHelper
        # Construct tuples for dict creation
        client_tuples = [(k, os.environ.get('INFLUXDB_{}'.format(k.upper())))
                         for k in self.influxdb_args]
        # Strip out any unset environment variables so the InfluxDB defaults
        # are used
        client_kwargs = {k: v for k,v in client_tuples if v is not None}
        self.client = InfluxDBClient(**client_kwargs)

        # Define this class here, where we know that influxdb is importable
        class ReviewAgeSeries(SeriesHelper):

            class Meta(object):
                series_name = os.environ['REVIEW_GATOR_METRIC_NAME']
                fields = ['total_age']
                tags = []  # type: List[Text]

        self.series_cls = ReviewAgeSeries

    def _determine_total_age_in_seconds(self, data):  # type: (Dict) -> float
        """Given a review-gator data dict, sum up the review ages."""
        total_age = 0
        for repo in data.values():
            for pr in repo['pull_requests']:
                total_age += (self.now - pr['date']).total_seconds()
        return total_age

    def _record_event_in_influxdb(self, total_age):  # type: (float) -> None
        """Given a total age, push that in to InfluxDB."""
        self.series_cls(total_age=total_age)
        self.series_cls.commit(self.client)
        print(total_age)

    def process_data(self, data):  # type: (Dict) -> None
        """Determine the total age of reviews and push to InfluxDB."""
        total_age = self._determine_total_age_in_seconds(data)
        self._record_event_in_influxdb(total_age)

    @classmethod
    def enabled(cls):  # type: () -> bool
        """True if influxdb is importable and we have a metric name."""
        try:
            import influxdb
        except ImportError:
            return False
        return 'REVIEW_GATOR_METRIC_NAME' in os.environ


REPORTER_CLASSES = [InfluxDBTotalAgeReporter]
