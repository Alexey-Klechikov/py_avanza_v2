from apis.avanza.client.client import get_client
from apis.avanza.client.models.search.market_stocks_result import Stock
from utils.logger import get_logger

log = get_logger()


def get_all_swedish_stocks() -> list[Stock]:
    stocks_results: list[Stock] = []

    try:
        offset = 0
        step = 100

        while True:
            market_stocks_filter_results = get_client().get_market_stocks(offset=offset)
            stocks_results += market_stocks_filter_results.stocks

            offset += step
            if offset >= market_stocks_filter_results.total_number_of_orderbooks:
                break

    except Exception as e:
        log.error(f"Failed to get all stocks: {e}")

    log.info(f"Total number of stocks: {len(stocks_results)}")

    return stocks_results
