import json
import os
from datetime import time
from typing import List

from hold_correlation.models import HoldRuleCorrelation, Scope
from utils.logger import get_logger

log = get_logger()


class Backlog:
    def __init__(self) -> None:
        self.rules: List[HoldRuleCorrelation] = []

    def _get_path(self, scope: Scope) -> str:
        project_root_dir = os.path.abspath(os.path.join(__file__, "..", ".."))
        return f"{project_root_dir}/config/hold_{scope.value.lower()}_correlation_rules.json"

    def read_rules(self, settings) -> None:
        for scope in settings.SCOPES:
            data_file_path = self._get_path(scope)

            with open(data_file_path, "r") as file:
                self.rules += [HoldRuleCorrelation(settings=settings, **i) for i in json.load(file)]

    def write_rules(self, scope: Scope = Scope.INTRADAY) -> None:
        data_file_path = self._get_path(scope)

        with open(data_file_path, "w") as file:
            json.dump([i.dump_dict() for i in self.rules], file, indent=2)

    def get_rules(self, time: time) -> List[HoldRuleCorrelation]:
        return list(filter(lambda rule: rule.action_interval.start <= time <= rule.action_interval.end, self.rules))
