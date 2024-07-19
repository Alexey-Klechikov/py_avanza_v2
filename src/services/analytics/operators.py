import json
import os
from datetime import date
from enum import Enum
from typing import List, Type

from pydantic import BaseModel

from services.analytics.models import Exchange, Stock
from utils.logger import get_logger

log = get_logger()


class AnalyticsConfig(BaseModel):
    filename: str
    model: Type


class AnalyticsType(Enum):
    STOCK_EVENTS = AnalyticsConfig(filename="stock_events", model=Stock)
    EXCHANGE_WORKING_HOURS = AnalyticsConfig(filename="exchange_working_hours", model=Exchange)


class DateEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, date):
            return obj.isoformat()
        return super().default(obj)


class Analytics:
    def __init__(self, type: AnalyticsType) -> None:
        self.type: AnalyticsType = type

        self.data: List[type.value.model] = []

    def read_file(self):
        data_file_path = self._get_path()

        with open(data_file_path, "r") as file:
            self.data = [self.type.value.model(**i) for i in json.load(file)]

    def write_file(self):
        data_file_path = self._get_path()

        with open(data_file_path, "w") as file:
            json.dump([i.model_dump() for i in self.data], file, cls=DateEncoder, indent=4)

    def _get_path(self) -> str:
        project_root_dir = os.path.abspath(os.path.join(__file__, "..", "..", ".."))
        return f"{project_root_dir}/data/analytics_{self.type.value.filename}.json"
