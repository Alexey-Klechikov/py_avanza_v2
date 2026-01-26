import asyncio

import telegram_send

from utils.logger.operators import get_logger

log = get_logger()


class Telegram:
    def __init__(self):
        self.messages: list[str] = []

    def send_message(self):
        log.info(f"Sending message: {' | '.join(self.messages)}")

        asyncio.run(telegram_send.send(messages=["\n".join(self.messages)]))
