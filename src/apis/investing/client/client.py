from datetime import datetime
from io import StringIO

import pandas as pd
import requests

from apis.investing.client.models import Resolution
from utils.logger import get_logger

# pylint: disable=E1101

log = get_logger()


class Investing:
    def __init__(self):
        self.base = (
            "https://tvc4.investing.com/84771021f8c0058579b0fe4d334348f3"
            + f"/{int(datetime.now().timestamp())}/1/1/8/history?"
        )
        self.headers = {
            "Host": "tvc4.investing.com",
            "Accept": "*/*",
            "Accept-Language": "en-GB,en;q=0.9,en-US;q=0.8,sv;q=0.7",
            "Content-Type": "text/plain",
            "Origin": "https://tvc-invdn-cf-com.investing.com",
            "Referer": "https://tvc-invdn-cf-com.investing.com/",
            "Sec-Ch-Ua": '"Not/A)Brand";v="8", "Chromium";v="126", "Microsoft Edge";v="126"',
            "Sec-Ch-Ua-Mobile": "?0",
            "Sec-Ch-Ua-Platform": "Linux",
            "Sec-Fetch-Dest": "empty",
            "Sec-Fetch-Mode": "cors",
            "Sec-Fetch-Site": "same-site",
            "User-Agent": "Mozilla/5.0 (X11; Ubuntu; Linux x86_64; rv:15.0) Gecko/20100101 Firefox/15.0.1",
        }

    def get_history(
        self,
        ticker_investing: str,
        resolution: Resolution,
        from_datetime: datetime,
        to_datetime: datetime,
    ) -> pd.DataFrame:
        arguments = {
            "symbol": ticker_investing,
            "resolution": resolution.value,
            "from": int(from_datetime.timestamp()),
            "to": int(to_datetime.timestamp()),
        }

        url = self.base + "&".join([f"{key}={value}" for key, value in arguments.items()])

        response = requests.get(url, headers=self.headers)

        try:
            df = pd.read_json(StringIO(response.text))

        except ValueError:
            log.error(f"Failed to read JSON from response: {response.text}")
            return pd.DataFrame()

        df["Datetime"] = pd.to_datetime(df["t"], unit="s")
        df.set_index("Datetime", inplace=True)

        columns_mapping = {"o": "Open", "h": "High", "l": "Low", "c": "Close", "v": "Volume"}
        for column_from, column_to in columns_mapping.items():
            df[column_to] = round(df[column_from], 2)

        df.drop(columns=list(set(df.columns) - set(columns_mapping.values())), inplace=True, axis=1)

        return df
