from unittest import TestCase

from avanza_bank.client.models.chart_data import ChartData


class Test_ChartData(TestCase):
    def test_chart_data(self):
        mock_chart_data = {
            "ohlc": [
                {
                    "timestamp": 1717398000000,
                    "open": 2627.47,
                    "close": 2631.19,
                    "low": 2627.47,
                    "high": 2631.26,
                    "totalVolumeTraded": 2262877,
                },
                {
                    "timestamp": 1717398060000,
                    "open": 2630.94,
                    "close": 2635.07,
                    "low": 2630.94,
                    "high": 2635.28,
                    "totalVolumeTraded": 499655,
                },
                {
                    "timestamp": 1717398120000,
                    "open": 2635.3,
                    "close": 2635.66,
                    "low": 2634.99,
                    "high": 2636.26,
                    "totalVolumeTraded": 481350,
                },
                {
                    "timestamp": 1717398180000,
                    "open": 2635.59,
                    "close": 2634.86,
                    "low": 2634.41,
                    "high": 2635.59,
                    "totalVolumeTraded": 703893,
                },
                {
                    "timestamp": 1717398240000,
                    "open": 2634.78,
                    "close": 2635.11,
                    "low": 2634.7,
                    "high": 2636.0,
                    "totalVolumeTraded": 528577,
                },
                {
                    "timestamp": 1717398300000,
                    "open": 2635.49,
                    "close": 2633.85,
                    "low": 2633.61,
                    "high": 2635.49,
                    "totalVolumeTraded": 486755,
                },
            ],
            "metadata": {
                "resolution": {
                    "chartResolution": "minute",
                    "availableResolutions": [
                        "minute",
                        "two_minutes",
                        "five_minutes",
                        "ten_minutes",
                        "thirty_minutes",
                        "hour",
                        "day",
                    ],
                },
            },
            "from": "2024-06-03",
            "to": "2024-06-03",
            "previousClosingPrice": 2604.1,
        }

        assert isinstance(ChartData(**mock_chart_data), ChartData)
