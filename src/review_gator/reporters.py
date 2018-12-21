try:
    from typing import Dict
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


REPORTER_CLASSES = []
