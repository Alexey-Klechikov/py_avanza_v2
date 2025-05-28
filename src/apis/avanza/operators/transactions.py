import json
import os
from collections import defaultdict
from dataclasses import dataclass
from datetime import date, datetime, time, timedelta

from avanza.constants import TransactionsDetailsType

from apis.avanza.client.client import get_client
from apis.avanza.client.models.order.transactions import Transaction
from config import SETTINGS
from utils.logger.operators import get_logger

log = get_logger()


@dataclass
class Deal:
    buy: Transaction | None = None
    sell: Transaction | None = None


class Transactions:
    def __init__(self):
        self.log_per_day: dict = {}

    def _reload_log(self, date_from: date, date_to: date | None = None) -> list[Transaction]:
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

        return sorted([i for i in log if i.account.id == SETTINGS.ACCOUNT_ID], key=lambda x: x.date, reverse=True)

    def log_deals(
        self,
        date_from: date = (datetime.today() - timedelta(days=6)).date(),
        only_today: bool = False,
    ) -> None:
        log.info("Group transactions into deals")

        log_per_instrument = defaultdict(list)
        for i in self._reload_log(date_from):
            log_per_instrument[i.instrument_name].append(i)

        deals_per_instrument = defaultdict(list)
        for instrument_name, transactions in log_per_instrument.items():
            deal = Deal()
            for i, transaction in enumerate(transactions):
                if only_today and not deal.buy and not deal.sell and transaction.date.date() != datetime.today().date():
                    break

                if transaction.type == TransactionsDetailsType.SELL and not deal.buy:
                    deal.sell = transaction
                elif transaction.type == TransactionsDetailsType.BUY and deal.sell:
                    deal.buy = transaction
                else:
                    log.warning(f"> Found not closed transaction for instrument: {instrument_name}")

                if deal.buy and deal.sell:
                    if deal.buy.volume.value + deal.sell.volume.value != 0:
                        log.warning(f"> Not complete deal for instrument: {instrument_name}")

                    deals_per_instrument[instrument_name].append(deal)
                    deal = Deal()

        total_deal_value = 0
        for instrument_name, deals in deals_per_instrument.items():
            log.info(f"> Found {len(deals)} deal(s) for '{instrument_name}'")

            for deal in deals:
                deal_datetime = ""
                if deal.buy.date.date() == deal.sell.date.date():
                    if deal.buy.date.time() == time(0, 0):
                        deal_datetime = deal.buy.date.strftime("%Y-%m-%d")
                    else:
                        deal_datetime = (
                            f"{deal.buy.date.strftime('%Y-%m-%d %H:%M')} -> {deal.sell.date.strftime('%H:%M')}"
                        )
                else:
                    datetime_pattern = "%Y-%m-%d %H:%M" if deal.buy.date.time() != time(0, 0) else "%Y-%m-%d"
                    deal_datetime = (
                        f"{deal.buy.date.strftime(datetime_pattern)} -> {deal.sell.date.strftime(datetime_pattern)}"
                    )

                deal_value = round(sum([i.amount.value for i in [deal.buy, deal.sell]]))

                total_deal_value += deal_value

                log.info(f">> {deal_datetime} -> {deal_value}")

        log.info(f"Total deals value: {total_deal_value}")

    def get_daily_trading_stats(self, date_from: date = (datetime.today() - timedelta(days=61)).date()) -> dict:
        log.info("Log daily trading stats")

        for i in self._reload_log(date_from):
            date_str = i.date.date().strftime("%Y-%m-%d")
            if date_str not in self.log_per_day:
                self.log_per_day[date_str] = {"amount": 0, "transactions": 0}

            self.log_per_day[date_str]["amount"] += int(i.amount.value)
            self.log_per_day[date_str]["transactions"] += 1

        for k, v in self.log_per_day.items():
            v["deals"] = int(v.pop("transactions") / 2)

        return self.log_per_day

    def save_daily_trading_stats(self, date_from: date = (datetime.today() - timedelta(days=61)).date()) -> None:
        log.info("Save daily trading stats")

        if not self.log_per_day:
            self.get_daily_trading_stats(date_from)

        logs_dir = os.path.abspath(__file__).split("apis")[0] + "logs"
        json.dump(
            self.log_per_day,
            open(f"{logs_dir}/daily_trading_stats_{SETTINGS.NAME}.json", "w"),
            indent=4,
        )
