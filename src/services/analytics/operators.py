import json
import os
from datetime import date
from typing import List

from services.analytics.models import Stock
from utils.logger import get_logger

log = get_logger()


class DateEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, date):
            return obj.isoformat()
        return super().default(obj)


class Analytics:
    def __init__(self) -> None:
        self.data: List[Stock] = []

    def read_file(self):
        data_file_path = self._get_path()

        with open(data_file_path, "r") as file:
            self.data = [Stock(**i) for i in json.load(file)]

    def write_file(self):
        data_file_path = self._get_path()

        with open(data_file_path, "w") as file:
            json.dump([i.model_dump() for i in self.data], file, cls=DateEncoder, indent=4)

    def _get_path(self) -> str:
        project_root_dir = os.path.abspath(os.path.join(__file__, "..", "..", ".."))
        return f"{project_root_dir}/data/analytics.json"
