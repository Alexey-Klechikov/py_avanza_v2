from src.clients.avanza_bank import Avanza
from src.data.settings import ACCOUNT_ID
from src.utils.logger import get_logger

log = get_logger("operators.avanza_bank.balance")


class Balance:
    def __init__(self, client: Avanza):
        self.client = client

        self.total_value = 0
        self.buying_power = 0

    def refresh_balance(self) -> None:
        log.debug("Refresh account balance")

        accounts_overview = self.client.get_accounts_overview()

        account_overview = [
            i for i in accounts_overview.accounts if i.info.id == str(ACCOUNT_ID)
        ][0]

        self.total_value = account_overview.total_value.total_value.value
        self.buying_power = account_overview.buying_power.total.value
