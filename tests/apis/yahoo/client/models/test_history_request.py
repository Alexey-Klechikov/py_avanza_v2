from datetime import date
from unittest import TestCase

from apis.yahoo.client.models.history_request import HistoryRequest, Interval, Period


class Test_HistoryRequest(TestCase):
    def test_history_request(self):
        self.assertEqual(
            HistoryRequest(period=Period.ONE_DAY, interval=Interval.ONE_MINUTE).model_dump(),
            {"period": "1d", "interval": "1m"},
        )

        self.assertEqual(
            HistoryRequest(start=date(2022, 1, 1), end=date(2022, 1, 31), interval=Interval.ONE_DAY).model_dump(),
            {"interval": "1d", "start": "2022-01-01", "end": "2022-01-31"},
        )

        with self.assertRaises(ValueError):
            HistoryRequest(
                period=Period.ONE_DAY,
                start=date(2022, 1, 1),
                end=date(2022, 1, 31),
                interval=Interval.ONE_DAY,
            ).model_dump()


class Test_IntervalMinutes(TestCase):
    def test_every_interval_has_a_length_in_minutes(self):
        assert Interval.TWO_MINUTES.mins == 2 and Interval.ONE_WEEK.mins == 7 * 24 * 60
        assert all(interval.mins > 0 for interval in Interval)
