from unittest import TestCase

from avanza_bank.client.models.order.delete import DeleteOrderResponse


class Test_DeleteOrderResponse(TestCase):
    def test_delete_order(self):
        delete_order_response = {
            "orderRequestStatus": "ERROR",
            "message": "Du har tyvärr inte tillräcklig täckning på ditt konto för att genomföra ordern.",
            "messageCode": "se.avanzabank.trading.account.negative.buying.power",
            "parameters": ["5554179", "-1099.100"],
        }

        assert isinstance(
            DeleteOrderResponse(**delete_order_response),
            DeleteOrderResponse,
        )

        delete_order_response = {
            "orderRequestStatus": "SUCCESS",
            "message": "",
            "parameters": [],
            "orderId": "650930816",
        }

        assert isinstance(
            DeleteOrderResponse(**delete_order_response),
            DeleteOrderResponse,
        )
