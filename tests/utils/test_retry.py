from unittest import TestCase

from utils.retry import backoff_seconds


class Test_BackoffSeconds(TestCase):
    def test_doubles_from_the_base_up_to_the_cap(self):
        assert [backoff_seconds(attempt, 3, 30) for attempt in range(6)] == [3, 6, 12, 24, 30, 30]
