import json
import os
from collections import defaultdict
from datetime import date, datetime, time, timedelta

from avanza.constants import TransactionsDetailsType

from apis.avanza.client.client import get_client
from apis.avanza.client.models.order.transactions import Transaction
from apis.avanza.operators.models.transactions import Deal
from config import SETTINGS
from utils.logger.operators import get_logger

log = get_logger()


class Transactions:
    def __init__(self):
        self.log_per_day: dict = {}

    def _reload_log(self, date_from: date, date_to: date | None = None) -> list[Transaction]:
        log = (
            get_client()
            .get_transactions(
                transaction_details_types=[
                    TransactionsDetailsType.BUY,
                    TransactionsDetailsType.SELL,
                ],
                transactions_from=date_from,
                transactions_to=date_to,
            )
            .transactions
        )

        return sorted([i for i in log if i.account.id == SETTINGS.ACCOUNT_ID], key=lambda x: x.date, reverse=True)

    def _group_transactions_by_instrument(self, date_from: date) -> dict[str, list[Transaction]]:
        log_per_instrument: dict[str, list[Transaction]] = defaultdict(list)
        for transaction in self._reload_log(date_from=date_from):
            log_per_instrument[transaction.instrument_name].append(transaction)

        return log_per_instrument

    def _build_deals(
        self,
        log_per_instrument: dict[str, list[Transaction]],
        only_today: bool,
        today_date: date,
    ) -> dict[str, list[Deal]]:
        deals_per_instrument: dict[str, list[Deal]] = defaultdict(list)

        for instrument_name, transactions in log_per_instrument.items():
            deal = Deal()
            for transaction in transactions:
                if only_today and not deal.buy and not deal.sell and transaction.date.date() != today_date:
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

        return deals_per_instrument

    def _format_deal_datetime(self, transaction_buy: Transaction, transaction_sell: Transaction) -> str:
        if transaction_buy.date.date() == transaction_sell.date.date():
            if transaction_buy.date.time() == time(0, 0):
                return transaction_buy.date.strftime("%Y-%m-%d")

            return f"{transaction_buy.date.strftime('%Y-%m-%d %H:%M')} -> {transaction_sell.date.strftime('%H:%M')}"

        datetime_pattern = "%Y-%m-%d %H:%M" if transaction_buy.date.time() != time(0, 0) else "%Y-%m-%d"
        return (
            f"{transaction_buy.date.strftime(datetime_pattern)} -> {transaction_sell.date.strftime(datetime_pattern)}"
        )

    def _calculate_deal_value(self, transaction_buy: Transaction, transaction_sell: Transaction) -> int:
        return round(sum(i.amount.value for i in [transaction_buy, transaction_sell]))

    def _log_deals_summary(self, deals_per_instrument: dict[str, list[Deal]]) -> int:
        total_deal_value = 0

        for instrument_name, deals in deals_per_instrument.items():
            log.info(f"> Found {len(deals)} deal(s) for '{instrument_name}'")
            for deal in deals:
                if not deal.buy or not deal.sell:
                    log.warning(f"> Found not closed deal for instrument: {instrument_name}")
                    continue

                deal_datetime = self._format_deal_datetime(transaction_buy=deal.buy, transaction_sell=deal.sell)
                deal_value = self._calculate_deal_value(transaction_buy=deal.buy, transaction_sell=deal.sell)
                total_deal_value += deal_value
                log.info(f">> {deal_datetime} -> {deal_value}")

        return total_deal_value

    def _get_logs_dir(self) -> str:
        return os.path.abspath(__file__).split("apis")[0] + "logs"

    # Public methods

    def log_deals(
        self,
        date_from: date = (datetime.today() - timedelta(days=6)).date(),
        only_today: bool = False,
    ) -> None:
        log.info("Group transactions into deals")

        log_per_instrument = self._group_transactions_by_instrument(date_from=date_from)
        deals_per_instrument = self._build_deals(
            log_per_instrument=log_per_instrument,
            only_today=only_today,
            today_date=datetime.today().date(),
        )

        total_deal_value = self._log_deals_summary(deals_per_instrument=deals_per_instrument)
        log.info(f"Total deals value: {total_deal_value}")

    def get_daily_trading_stats(self, date_from: date = (datetime.today() - timedelta(days=61)).date()) -> dict:
        log.info("Log daily trading stats")

        for i in self._reload_log(date_from=date_from):
            date_str = i.date.date().strftime("%Y-%m-%d")
            if date_str not in self.log_per_day:
                self.log_per_day[date_str] = {"amount": 0, "transactions": 0}

            self.log_per_day[date_str]["amount"] += int(i.amount.value)
            self.log_per_day[date_str]["transactions"] += 1

        for v in self.log_per_day.values():
            v["deals"] = int(v.pop("transactions") / 2)

        return self.log_per_day

    def save_daily_trading_stats(
        self,
        date_from: date = (datetime.today() - timedelta(days=180)).replace(day=1).date(),
    ) -> None:
        log.info("Save daily trading stats")

        if not self.log_per_day:
            self.get_daily_trading_stats(date_from=date_from)

        logs_dir = self._get_logs_dir()
        json.dump(
            obj=self.log_per_day,
            fp=open(file=f"{logs_dir}/daily_trading_stats_{SETTINGS.NAME}.json", mode="w"),
            indent=4,
        )
