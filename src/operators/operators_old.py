class Context:
    def __init__(self, user: str, accounts: dict, process_lists: bool = True):
        self.ctx = self.get_ctx(user)
        self.accounts = accounts
        self.portfolio = self.get_portfolio()

        if process_lists:
            self.watchlists = self.process_lt_watchlists()

    def get_portfolio(self) -> Portfolio:
        portfolio = Portfolio()

        for account_name, account_id in self.accounts.items():
            account_overview = self.ctx.get_accounts_overview(account_id)

            if account_overview:
                portfolio.buying_power[account_name] = account_overview["buyingPower"]
                portfolio.total_own_capital += account_overview["ownCapital"]

        positions = []
        all_positions = self.ctx.get_positions()
        if all_positions:
            for position in all_positions["instrumentPositions"][0]["positions"]:
                if not int(position["accountId"]) in self.accounts.values():
                    continue

                if position.get("orderbookId", None) is None:
                    log.warning(f"{position['name']} has no orderbookId")
                    continue

                positions.append(position)

        if positions:
            portfolio.positions = Positions(positions)

            tickers_yahoo = []
            for order_book_id in portfolio.positions.df["orderbookId"].tolist():
                stock_info = self.ctx.get_instrument(
                    InstrumentType.STOCK, order_book_id
                )

                tickers_yahoo.append(
                    f"{stock_info.get('listing', {}).get('tickerSymbol', '').replace(' ', '-')}.ST"
                )

            portfolio.positions.df["ticker_yahoo"] = tickers_yahoo

        return portfolio

    def get_stock_price(self, stock_id: str) -> dict:
        stock_info = self.ctx.get_instrument(InstrumentType.STOCK, stock_id)

        if not stock_info:
            raise Exception(f"Stock {stock_id} not found")

        stock_price = {
            OrderType.BUY: stock_info.get("quote", {}).get("sell"),
            OrderType.SELL: stock_info.get("quote", {}).get("buy"),
        }

        order_depth = pd.DataFrame(stock_info.get("orderDepthLevels"))
        if not order_depth.empty:
            stock_price[OrderType.SELL] = max(
                order_depth["buySide"].apply(lambda x: x["price"])
            )
            stock_price[OrderType.BUY] = min(
                order_depth["sellSide"].apply(lambda x: x["price"])
            )

        return stock_price

    def get_instrument_info(
        self, instrument_type: InstrumentType, instrument_id: str
    ) -> dict:
        instrument_info = {}

        for _ in range(5):
            try:
                instrument_info = self.ctx.get_instrument(
                    instrument_type, instrument_id
                )
                break

            except HTTPError:
                time.sleep(2)
                continue

        market_maker_orders = {"buySide": None, "sellSide": None}
        order_depth = instrument_info.get("orderDepthLevels", [])
        for side in market_maker_orders:
            side_orders_depth = [
                i[side] for i in order_depth if i[side]["volume"] >= 10000
            ]

            if len(side_orders_depth) == 0:
                continue

            market_maker_orders[side] = (
                pd.DataFrame(side_orders_depth)
                .sort_values(by="volume", ascending=False)
                .iloc[0]["price"]
            )

        has_market_maker = all([i is not None for i in market_maker_orders.values()])
        spread = (
            round(
                (market_maker_orders["sellSide"] / market_maker_orders["buySide"] - 1)  # type: ignore
                * 100,
                2,
            )
            if has_market_maker
            else instrument_info.get("quote", {}).get("spread")
        )

        is_deprecated = not instrument_info or (
            market_maker_orders["buySide"] is not None
            and market_maker_orders["sellSide"] is None
        )

        positions = instrument_info.get("holdings", {}).get(
            "accountAndPositionsView", []
        )

        orders = [
            i
            for i in instrument_info.get("ordersAndDeals", {}).get("orders", [])
            if i["orderState"] == "ACTIVE"
        ]

        deals = instrument_info.get("ordersAndDeals", {}).get("deals", [])

        key_indicators = instrument_info.get(
            "keyIndicators", {"direction": None, "leverage": None}
        )

        if instrument_info.get("type") == "CERTIFICATE":
            key_indicators.update(
                {
                    "direction": instrument_info.get("direction"),
                    "leverage": (
                        None
                        if not instrument_info.get("leverage")
                        else float(instrument_info["leverage"])
                    ),
                }
            )

        return {
            OrderType.BUY: instrument_info.get("quote", {}).get("sell", None),
            OrderType.SELL: instrument_info.get("quote", {}).get("buy", None),
            "spread": spread,
            "position": {} if len(positions) == 0 else positions[0],
            "order": {} if len(orders) == 0 else orders[0],
            "last_deal": {} if len(deals) == 0 else deals[0],
            "key_indicators": key_indicators,
            "is_deprecated": is_deprecated,
        }

    def update_todays_ochl(self, data: pd.DataFrame, stock_id: str) -> pd.DataFrame:
        stock_info = self.ctx.get_instrument(InstrumentType.STOCK, stock_id)

        if not stock_info:
            raise Exception(f"Stock {stock_id} not found")

        last_row_index = data.tail(1).index
        data.loc[last_row_index, "Open"] = (
            stock_info["quote"]["last"] - stock_info["quote"]["change"]
        )
        data.loc[last_row_index, "Close"] = stock_info["quote"]["last"]
        data.loc[last_row_index, "High"] = stock_info["quote"]["highest"]
        data.loc[last_row_index, "Low"] = stock_info["quote"]["lowest"]
        data.loc[last_row_index, "Volume"] = stock_info["quote"]["totalVolumeTraded"]

        return data

    def get_today_history(self, stock_id: str) -> pd.DataFrame:
        period = TimePeriod.TODAY
        resolution = Resolution.MINUTE

        chart_data = self.ctx.get_chart_data(stock_id, period, resolution)

        if chart_data is None or len(chart_data["ohlc"]) == 0:
            return pd.DataFrame(
                columns=["Datetime", "Open", "High", "Low", "Close", "Volume"]
            ).set_index("Datetime")

        data = pd.DataFrame(chart_data["ohlc"])
        data["Datetime"] = [
            datetime.fromtimestamp(x / 1000).astimezone(timezone("Europe/Stockholm"))
            for x in data.timestamp
        ]
        data = (
            data.rename(
                columns={
                    "open": "Open",
                    "high": "High",
                    "low": "Low",
                    "close": "Close",
                    "totalVolumeTraded": "Volume",
                }
            )
            .set_index("Datetime")
            .drop(["timestamp"], axis=1)
        )

        return data
