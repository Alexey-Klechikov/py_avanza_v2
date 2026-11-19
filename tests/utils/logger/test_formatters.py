import logging
from unittest import TestCase

from utils.logger.formatters import OneLineFormatter


class Test_OneLineFormatter(TestCase):
    def test_keeps_dashes_in_the_message(self):
        record = logging.LogRecord("task", logging.INFO, __file__, 1, "------------", None, None)

        assert OneLineFormatter().format(record).rstrip().endswith("------------")
