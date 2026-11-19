from types import SimpleNamespace
from unittest import TestCase
from unittest.mock import MagicMock, patch

from apis.avanza.operators import orders as orders_module
from apis.avanza.operators.orders import Orders
from config import SETTINGS


def _order(name: str, account_id: str = SETTINGS.ACCOUNT_ID) -> SimpleNamespace:
    return SimpleNamespace(account=SimpleNamespace(account_id=account_id), orderbook=SimpleNamespace(name=name))


class Test_List(TestCase):
    def test_keeps_the_traded_products_of_the_account(self):
        product = _order("BEAR TESLA X10 AVA 2")
        client = MagicMock()
        client.list_orders.return_value.orders = [
            product,
            _order("BULL NVIDIA X5 AVA 1"),
            _order("BULL TESLA X10 AVA 3", account_id="other"),
        ]

        with patch.object(orders_module, "get_client", return_value=client):
            assert Orders()._list() == [product]
