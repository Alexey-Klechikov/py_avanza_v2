from types import SimpleNamespace
from unittest import TestCase
from unittest.mock import MagicMock, patch

from apis.avanza.operators import portfolio as portfolio_module
from apis.avanza.operators.portfolio import Portfolio
from config import SETTINGS


def _account_position(name: str, account_id: str = SETTINGS.ACCOUNT_ID) -> SimpleNamespace:
    return SimpleNamespace(account=SimpleNamespace(id=account_id), instrument=SimpleNamespace(name=name))


class Test_ReloadPositions(TestCase):
    def test_keeps_the_traded_products_of_the_account(self):
        product, other_product, other_account = (
            _account_position("BULL TESLA X10 AVA 3"),
            _account_position("BULL NVIDIA X5 AVA 1"),
            _account_position("BEAR TESLA X10 AVA 2", account_id="other"),
        )
        client = MagicMock()
        client.get_accounts_positions.return_value.with_orderbook = [product, other_product, other_account]
        portfolio = Portfolio.__new__(Portfolio)

        with (
            patch.object(portfolio_module, "get_client", return_value=client),
            patch.object(portfolio_module, "_to_position", side_effect=lambda position: position),
            patch.object(Portfolio, "_detect_acquired_instruments"),
        ):
            portfolio.reload_positions()

        assert portfolio.positions == [product]
