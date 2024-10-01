import json
import os
from datetime import datetime
from typing import List, Optional

from services.hold.models import Action, Event, HoldRule, Scope
from utils.logger import get_logger

log = get_logger()


class Backlog:
    def __init__(self) -> None:
        self.rules: List[HoldRule] = []
        self.events: List[Event] = []

    def _get_path(self, file_prefix: str, scope: Scope) -> str:
        project_root_dir = os.path.abspath(os.path.join(__file__, "..", "..", ".."))
        return f"{project_root_dir}/config/{file_prefix}_hold_rules_{scope.value.lower()}.json"

    def read_rules(self, settings) -> None:
        for scope in settings.SCOPES:
            data_file_path = self._get_path(settings.FILE_PREFIX, scope)

            with open(data_file_path, "r") as file:
                self.rules += [HoldRule(settings=settings, **i) for i in json.load(file)]

    def extract_events_from_rules(self):
        events = []
        for rule in self.rules:
            events.append(
                Event(
                    at=rule.buy_time,
                    action=Action.BUY,
                    orderbook_direction=rule.orderbook_direction,
                    take_profit=rule.take_profit,
                    budget=rule.settings.BUDGET,
                    settings=rule.settings,
                ),
            )

            if not rule.sell_time:
                continue

            events.append(
                Event(
                    at=rule.sell_time,
                    action=Action.SELL,
                    orderbook_direction=rule.orderbook_direction,
                    take_profit=rule.take_profit,
                    budget=rule.settings.BUDGET,
                    settings=rule.settings,
                ),
            )

        events_deduplicated = {}
        for event in events:
            key = (event.at, event.orderbook_direction, event.settings.ACCOUNT_ID)
            if key in events_deduplicated:
                if events_deduplicated[key].action == Action.BUY:
                    continue
            events_deduplicated[key] = event

        events = [i for i in events_deduplicated.values() if i.at >= datetime.now().time()]
        events = sorted(events, key=lambda x: x.action.value, reverse=True)
        events = sorted(events, key=lambda x: x.at)

        self.events = events

    def pop_next_event(self) -> Optional[Event]:
        if not self.events:
            return

        event = self.events.pop(0)

        log.info(
            "Next event: {} {} {} at {}".format(
                event.action.value,
                event.orderbook_direction.value,
                event.settings.NAME,
                event.at.strftime("%H:%M"),
            ),
        )

        return event
