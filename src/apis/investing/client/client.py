from datetime import datetime
from functools import cache
from io import StringIO

import cloudscraper
import pandas as pd
from bs4 import BeautifulSoup
from requests_html import HTMLSession

from apis.investing.client.models import Resolution
from utils.logger import get_logger

# pylint: disable=E1101

log = get_logger()


class Investing:
    def __init__(self, ticker_investing: str):
        self.ticker_investing = ticker_investing
        self.headers = {
            "Accept": "*/*",
            "Accept-Language": "en-GB,en;q=0.9,en-US;q=0.8,sv;q=0.7",
            "Cache-Control": "no-cache",
            "Content-Type": "text/plain",
            "Origin": "https://tvc-invdn-cf-com.investing.com",
            "Pragma": "no-cache",
            "Priority": "u=1, i",
            "Referer": "https://tvc-invdn-cf-com.investing.com/",
            "Sec-Ch-Ua": '"Not/A)Brand";v="8", "Chromium";v="126", "Microsoft Edge";v="126"',
            "Sec-Ch-Ua-Mobile": "?0",
            "Sec-Ch-Ua-Platform": "macOS",
            "Sec-Fetch-Dest": "empty",
            "Sec-Fetch-Mode": "cors",
            "Sec-Fetch-Site": "same-site",
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
            + "(KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36 Edg/126.0.0.0",
        }

        self.proxies = {protocol: "http://13.83.94.137:3128" for protocol in ["http", "https"]}

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

        try:
            with HTMLSession() as session:
                response = cloudscraper.create_scraper(session).get(
                    "https://www.investing.com/indices/omx-stockholm-30-chart",
                    headers=self.headers,
                    # proxies=self.proxies,
                )
                soup = BeautifulSoup(response.text, "html.parser")

                iframe = soup.find("iframe", {"data-test": "tvc-chart-iframe"})
                if iframe is None:
                    log.warning("No iframe found")
                    return pd.DataFrame()

                iframe_url = iframe.get("src")  # type: ignore
                if iframe_url is None:
                    log.warning("No iframe URL found")
                    return pd.DataFrame()

                iframe_carrier = iframe_url.split("carrier=")[1].split("&")[0]  # type: ignore

                url = (
                    f"https://tvc4.investing.com/{iframe_carrier}"
                    + f"/{int(to_datetime.timestamp())}/1/1/2/history?"
                    + "&".join([f"{key}={value}" for key, value in arguments.items()])
                )

                response = session.get(
                    url,
                    headers=self.headers,
                    # proxies=self.proxies,
                )

                soup = BeautifulSoup(response.text, "html.parser")

                df = pd.read_json(StringIO(response.text))

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
