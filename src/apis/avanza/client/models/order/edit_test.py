from unittest import TestCase

from apis.avanza.client.models.order.edit import EditOrderResponse


class Test_EditOrderResponse(TestCase):
    def test_edit_order(self):
        edit_order_response = {
            "orderRequestStatus": "ERROR",
            "message": "Du har tyvärr inte tillräcklig täckning på ditt konto för att genomföra ordern.",
            "messageCode": "se.avanzabank.trading.account.negative.buying.power",
            "parameters": ["5554179", "-1099.100"],
        }

        assert isinstance(EditOrderResponse(**edit_order_response), EditOrderResponse)

        edit_order_response = {
            "orderRequestStatus": "SUCCESS",
            "message": "",
            "parameters": [],
            "orderId": "650930816",
        }

        assert isinstance(EditOrderResponse(**edit_order_response), EditOrderResponse)
