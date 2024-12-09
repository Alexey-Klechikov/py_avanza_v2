import json
import os

from tasks.trade_candlesticks.models import CandlestickPatternRule
from utils.logger import get_logger

log = get_logger()


class Backlog:
    def __init__(self) -> None:
        self.rules: list[CandlestickPatternRule] = []

    def _get_path(self) -> str:
        project_root_dir = os.path.abspath(os.path.join(__file__, "..", "..", ".."))
        return f"{project_root_dir}/config/trade_candlesticks.json"

    def read_rules(self) -> None:
        data_file_path = self._get_path()

        with open(data_file_path) as file:
            self.rules += [CandlestickPatternRule(**i) for i in json.load(file)]

    def write_rules(self, reference_price: int) -> None:
        data_file_path = self._get_path()

        with open(data_file_path, "w") as file:
            json.dump([i.dump_dict(reference_price) for i in self.rules], file, indent=2)
