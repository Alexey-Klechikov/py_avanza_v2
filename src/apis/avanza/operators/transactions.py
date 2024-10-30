from collections import defaultdict
from dataclasses import dataclass
from datetime import date, datetime, timedelta

from avanza.constants import TransactionsDetailsType

from apis.avanza.client import get_client
from apis.avanza.client.models import Transaction
from utils.logger import get_logger

log = get_logger()


@dataclass
class Deal:
    buy: Transaction | None = None
    sell: Transaction | None = None


class Transactions:
    def __init__(self, account_id: str):
        self.account_id = account_id
        self.log: list[Transaction] = []

    def _reload_log(
        self,
        date_from: date = (datetime.today() - timedelta(days=7)).date(),
        date_to: date | None = None,
    ) -> list[Transaction]:
        log = (
            get_client()
            .get_transactions(
                [
                    TransactionsDetailsType.BUY,
                    TransactionsDetailsType.SELL,
                ],
                date_from,
                date_to,
            )
            .transactions
        )

        return sorted([i for i in log if i.account.id == self.account_id], key=lambda x: x.date, reverse=True)

    def log_deals(self, log_header: str = ""):
        log.info(f"Group transactions into deals for script '{log_header}'")

        log_per_instrument = defaultdict(list)
        for i in self._reload_log():
            log_per_instrument[i.instrument_name].append(i)

        deals_per_instrument = defaultdict(list)
        for instrument_name, transactions in log_per_instrument.items():
            deal = Deal()
            for i, transaction in enumerate(transactions):
                if not deal.buy and not deal.sell and transaction.date.date() != datetime.today().date():
                    break

                if transaction.type == TransactionsDetailsType.SELL and not deal.buy:
                    deal.sell = transaction
                elif transaction.type == TransactionsDetailsType.BUY and deal.sell:
                    deal.buy = transaction
                else:
                    log.warning(f"Found not closed transaction for instrument: {instrument_name}")

                if deal.buy and deal.sell:
                    if deal.buy.volume.value + deal.sell.volume.value != 0:
                        log.warning(f"Not complete deal for instrument: {instrument_name}")

                    deals_per_instrument[instrument_name].append(deal)
                    deal = Deal()

        for instrument_name, deals in deals_per_instrument.items():
            log.info(f"Found {len(deals)} deal(s) for '{instrument_name}'")

            for deal in deals:
                # format datetime to trim down to minutes
                log.info(
                    f"> Buy: {deal.buy.date.strftime('%Y-%m-%d %H:%M')},"
                    + f" Sell: {deal.sell.date.strftime('%Y-%m-%d %H:%M')}"
                    + f" -> {round(sum([i.amount.value for i in [deal.buy, deal.sell]]))}",
                )

        return deals_per_instrument
