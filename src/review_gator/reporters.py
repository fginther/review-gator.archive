import datetime
import os

import pytz

try:
    from typing import Dict, List, Text
except ImportError:
    pass


class ReviewGatorReporter(object):

    def process_data(self, data):
        # type: (Dict) -> None
        raise NotImplementedError

    @classmethod
    def enabled(cls):
        # type: () -> bool
        return False


class InfluxDBTotalAgeReporter(ReviewGatorReporter):

    influxdb_args = ['host', 'port', 'username', 'password', 'database']

    def __init__(self):
        # type: () -> None
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

    def _determine_total_age_in_seconds(self, data):
        # type: (Dict) -> float
        total_age = 0
        for repo in data.values():
            for pr in repo['pull_requests']:
                total_age += (self.now - pr['date']).total_seconds()
        return total_age

    def _record_event_in_influxdb(self, total_age):
        # type: (float) -> None
        self.series_cls(total_age=total_age)
        self.series_cls.commit(self.client)
        print(total_age)

    def process_data(self, data):
        # type: (Dict) -> None
        total_age = self._determine_total_age_in_seconds(data)
        self._record_event_in_influxdb(total_age)

    @classmethod
    def enabled(cls):
        # type: () -> bool
        try:
            import influxdb
        except ImportError:
            return False
        return 'REVIEW_GATOR_METRIC_NAME' in os.environ


REPORTER_CLASSES = [InfluxDBTotalAgeReporter]
