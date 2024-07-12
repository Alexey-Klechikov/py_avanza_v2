import telegram_send

from utils.logger import get_logger

log = get_logger()


class Telegram:
    def __init__(self):
        self.messages = []

        self.starting_balance = 0.0
        self.final_balance = 0.0

    def send_message(self):
        log.info("Sending message")

        telegram_send.send(messages=["\n".join(self.messages)])
