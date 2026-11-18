from unittest import TestCase

from apis.avanza.client.models.instrument.index import InstrumentIndex


class Test_InstrumentIndex(TestCase):
    def test_instrument_index(self):
        mock_index = {
            "constituents": [
                {"changePercent": 0.0183, "countryCode": "SE", "name": "Boliden", "orderbookId": "5564"},
                {"changePercent": 0.0114, "countryCode": "SE", "name": "Handelsbanken A", "orderbookId": "5264"},
                {"changePercent": 0.012, "countryCode": "SE", "name": "Swedbank A", "orderbookId": "5241"},
                {"changePercent": 0.0194, "countryCode": "SE", "name": "SEB A", "orderbookId": "5255"},
                {"changePercent": -0.0019, "countryCode": "SE", "name": "Telia Company", "orderbookId": "5479"},
                {"changePercent": 0.0136, "countryCode": "SE", "name": "Epiroc A", "orderbookId": "861430"},
                {"changePercent": 0.0083, "countryCode": "SE", "name": "ABB", "orderbookId": "5447"},
                {"changePercent": 0.0076, "countryCode": "SE", "name": "Essity B", "orderbookId": "764241"},
                {"changePercent": 0.0036, "countryCode": "SE", "name": "Ericsson B", "orderbookId": "5240"},
                {"changePercent": 0.0009, "countryCode": "SE", "name": "SCA B", "orderbookId": "5263"},
                {"changePercent": 0.023, "countryCode": "SE", "name": "Industrivärden C", "orderbookId": "5245"},
                {"changePercent": 0.0555, "countryCode": "SE", "name": "Addtech B", "orderbookId": "5537"},
                {"changePercent": 0.0024, "countryCode": "SE", "name": "SKF B", "orderbookId": "5259"},
                {"changePercent": 0.0175, "countryCode": "SE", "name": "Evolution", "orderbookId": "549768"},
                {"changePercent": 0.0046, "countryCode": "SE", "name": "Hexagon B", "orderbookId": "5286"},
                {"changePercent": 0.0075, "countryCode": "SE", "name": "Alfa Laval", "orderbookId": "5580"},
                {"changePercent": 0.0228, "countryCode": "SE", "name": "Tele2 B", "orderbookId": "5386"},
                {"changePercent": 0.017, "countryCode": "SE", "name": "Assa Abloy B", "orderbookId": "5271"},
                {"changePercent": -0.0017, "countryCode": "SE", "name": "Volvo B", "orderbookId": "5269"},
                {"changePercent": 0.0131, "countryCode": "SE", "name": "Nordea Bank", "orderbookId": "5249"},
                {"changePercent": 0.0275, "countryCode": "SE", "name": "SAAB B", "orderbookId": "5401"},
                {"changePercent": 0.0092, "countryCode": "SE", "name": "Investor B", "orderbookId": "5247"},
                {"changePercent": 0.0136, "countryCode": "SE", "name": "Sandvik", "orderbookId": "5471"},
                {"changePercent": -0.0258, "countryCode": "SE", "name": "Skanska B", "orderbookId": "5257"},
                {"changePercent": 0.0028, "countryCode": "SE", "name": "EQT", "orderbookId": "1001617"},
                {"changePercent": 0.0146, "countryCode": "SE", "name": "H&M B", "orderbookId": "5364"},
                {"changePercent": 0.0262, "countryCode": "SE", "name": "Lifco B", "orderbookId": "520898"},
                {"changePercent": 0.0032, "countryCode": "SE", "name": "Atlas Copco A", "orderbookId": "5234"},
                {"changePercent": 0.0102, "countryCode": "SE", "name": "AstraZeneca ADR", "orderbookId": "5431"},
                {"changePercent": 0.0052, "countryCode": "SE", "name": "Nibe Industrier B", "orderbookId": "5325"},
            ],
            "description": "Index över trettio bolag. Baseras på både omsättning och "
            "justerat börsvärde sk free float,\n"
            "det värde som endast avser fritt handlade aktier. Bara ett "
            "aktieslag per bolag.",
            "historicalClosingPrices": {
                "fiveYears": 1989.34,
                "oneDay": 3089.67,
                "oneMonth": 2963.307501,
                "oneWeek": 3026.56776,
                "oneYear": 2639.75,
                "start": 73.66,
                "startDate": "1984-01-02",
                "startOfYear": 2882.968965,
                "tenYears": 1330.11,
                "threeMonths": 2733.10684,
                "threeYears": 2254.8,
            },
            "indexType": "SECTOR",
            "isin": "SE0000337842",
            "listing": {
                "countryCode": "SE",
                "currency": "SEK",
                "marketPlaceCode": "XXXX",
                "shortName": "OMXS30",
                "tickSizeListId": "7700011",
                "tickerSymbol": "OMXS30",
            },
            "name": "OMX Stockholm 30",
            "orderbookId": "19002",
            "previousClosingPrice": 3089.67,
            "quote": {
                "change": 30.78,
                "changePercent": 1.0,
                "highest": 3126.35,
                "last": 3120.45,
                "lowest": 3075.8,
                "timeOfLast": 1770395400000,
                "totalValueTraded": 17966382443.86,
                "totalVolumeTraded": 79740935,
                "updated": 1770395400219,
            },
            "type": "INDEX",
        }

        assert isinstance(InstrumentIndex(**mock_index), InstrumentIndex)
