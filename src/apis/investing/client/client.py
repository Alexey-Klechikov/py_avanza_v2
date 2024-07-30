"""
This module is responsible for fetching data from Investing.com. It runs using Selenium.
To execute it, you need to have the GeckoDriver and firefoxinstalled (on Ubuntu).

wget https://github.com/mozilla/geckodriver/releases/download/v0.34.0/geckodriver-v0.34.0-linux64.tar.gz
tar -xvzf geckodriver-v0.34.0-linux64.tar.gz
chmod +x geckodriver
sudo mv geckodriver /usr/local/bin/
rm geckodriver-v0.34.0-linux64.tar.gz

apt  install firefox
"""

from datetime import datetime
from functools import cache
from io import StringIO

import pandas as pd
from bs4 import BeautifulSoup
from selenium import webdriver

from apis.investing.client.models import Resolution
from utils.logger import get_logger

# pylint: disable=E1101

log = get_logger()


class Investing:
    def __init__(self, ticker_investing: str):
        self.ticker_investing = ticker_investing
        self.iframe_carrier = self._get_iframe_carrier_from_session()

    def _get_iframe_carrier_from_session(self):
        with webdriver.Firefox() as driver:
            driver.get("https://www.investing.com/indices/omx-stockholm-30-chart")
            html = driver.page_source
            soup = BeautifulSoup(html, "html.parser")

            iframe = soup.find("iframe", {"data-test": "tvc-chart-iframe"})
            if iframe is None:
                log.warning("No iframe found")
                return

            iframe_url = iframe.get("src")  # type: ignore
            if iframe_url is None:
                log.warning("No iframe URL found")
                return

            return iframe_url.split("carrier=")[1].split("&")[0]  # type: ignore

    def get_history(
        self,
        resolution: Resolution,
        from_datetime: datetime,
        to_datetime: datetime,
    ) -> pd.DataFrame:
        arguments = {
            "symbol": self.ticker_investing,
            "resolution": resolution.value,
            "from": int(from_datetime.timestamp()),
            "to": int(to_datetime.timestamp()),
        }

        url = (
            f"https://tvc4.investing.com/{self.iframe_carrier}"
            + f"/{int(to_datetime.timestamp())}/1/1/2/history?"
            + "&".join([f"{key}={value}" for key, value in arguments.items()])
        )

        try:
            with webdriver.Firefox() as driver:
                driver.get(url)
                html = driver.page_source
                soup = BeautifulSoup(html, "html.parser")
                data = soup.find("body").text  # type: ignore
                df = pd.read_json(StringIO(data))

        except ValueError:
            log.exception("Failed to read JSON from response", exc_info=True)
            return pd.DataFrame()

        df["Datetime"] = pd.to_datetime(df["t"], unit="s")
        df.set_index("Datetime", inplace=True)

        columns_mapping = {"o": "Open", "h": "High", "l": "Low", "c": "Close", "v": "Volume"}
        for column_from, column_to in columns_mapping.items():
            df[column_to] = round(df[column_from], 2)

        df.drop(columns=list(set(df.columns) - set(columns_mapping.values())), inplace=True, axis=1)

        return df


@cache
def get_investing(ticker_investing):
    return Investing(ticker_investing)
