from unittest import TestCase

from apis.avanza.client.models.order.deals import Deals


class Test_DeleteOrderResponse(TestCase):
    def test_delete_order(self):
        deals_response = {
            "deals": [
                {
                    "id": "1331319073",
                    "account": {
                        "accountId": "5554179",
                        "name": {"value": "DT"},
                        "type": {"accountType": "INVESTERINGSSPARKONTO"},
                        "urlParameterId": "pW2w96aJi5hPJVm1o6eYZw",
                    },
                    "orderbookId": "1756986",
                    "volume": 13,
                    "price": 98.51,
                    "amount": 1280.63,
                    "time": "2024-07-12T12:45:16",
                    "side": "BUY",
                    "orderId": "660637215",
                    "orderbook": {
                        "id": "1756986",
                        "name": "TURBO L OMX AVA 1903",
                        "countryCode": "SE",
                        "currency": "SEK",
                        "instrumentType": "Warrant",
                        "volumeFactor": "1.00",
                        "isin": "GB00BSJJGK59",
                        "mic": "FNSE",
                    },
                },
            ],
            "fundDeals": [],
        }

        assert isinstance(
            Deals(**deals_response),
            Deals,
        )
