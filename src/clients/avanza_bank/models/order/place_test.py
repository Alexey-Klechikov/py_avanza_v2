from unittest import TestCase

from src.clients.avanza_bank.models.order.place import PlaceOrderResponse


class Test_PlaceOrderResponse(TestCase):
    def test_place_order(self):
        place_order_response = {
            "orderRequestStatus": "ERROR",
            "message": "Du har tyvärr inte tillräcklig täckning på ditt konto för att genomföra ordern.",
            "messageCode": "se.avanzabank.trading.account.negative.buying.power",
            "parameters": ["5554179", "-1099.100"],
        }

        assert isinstance(
            PlaceOrderResponse(**place_order_response), PlaceOrderResponse
        )

        place_order_response = {
            "orderRequestStatus": "SUCCESS",
            "message": "",
            "parameters": [],
            "orderId": "650930816",
        }

        assert isinstance(
            PlaceOrderResponse(**place_order_response), PlaceOrderResponse
        )
