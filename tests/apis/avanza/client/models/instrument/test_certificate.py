from unittest import TestCase

from apis.avanza.client.models.instrument.certificate import InstrumentCertificate


class Test_InstrumentCertificate(TestCase):
    def test_instrument_certificate(self):
        mock_certificate = {
            "orderbookId": "1522311",
            "name": "BEAR OMX X20 AVA 30",
            "isin": "GB00BQR95N95",
            "tradable": "BUYABLE_AND_SELLABLE",
            "listing": {
                "shortName": "BEAR OMX X20 AVA 30",
                "tickerSymbol": "BEAR OMX X20 AVA 30",
                "countryCode": "SE",
                "currency": "SEK",
                "marketPlaceCode": "NMTF",
                "marketPlaceName": "Nordic MTF",
                "tickSizeListId": "257",
                "marketTradesAvailable": True,
            },
            "historicalClosingPrices": {
                "oneDay": 0.003,
                "oneWeek": 0.005,
                "oneMonth": 0.006,
                "threeMonths": 0.032,
                "startOfYear": 0.06,
                "oneYear": 1.15,
                "start": 65.99,
                "startDate": "2023-01-11",
            },
            "keyIndicators": {
                "leverage": 20.0,
                "productLink": "https://etp.morganstanley.com/SE/SV/product-details/",
                "numberOfOwners": 40,
                "isAza": True,
            },
            "quote": {
                "buy": 0.003,
                "sell": 0.254,
                "last": 0.003,
                "change": 0.0,
                "changePercent": 0.0,
                "spread": 195.33,
                "timeOfLast": 1717444800000,
                "totalValueTraded": 0.0,
                "totalVolumeTraded": 0,
                "updated": 1717491901859,
            },
            "type": "CERTIFICATE",
            "underlying": {
                "orderbookId": "19002",
                "name": "OMX Stockholm 30",
                "instrumentType": "INDEX",
                "instrumentSubType": "SECTOR",
                "quote": {
                    "last": 2587.84,
                    "highest": 2608.22,
                    "lowest": 2582.06,
                    "change": -24.18,
                    "changePercent": -0.93,
                    "timeOfLast": 1717514228000,
                    "totalValueTraded": 7118829113.6,
                    "totalVolumeTraded": 74926724,
                    "updated": 1717514228152,
                },
                "listing": {
                    "shortName": "OMXS30",
                    "tickerSymbol": "OMXS30",
                    "countryCode": "SE",
                    "currency": "SEK",
                    "marketPlaceCode": "XXXX",
                    "marketPlaceName": "Inofficiella (beQuoted)",
                    "tickSizeListId": "7700011",
                    "marketTradesAvailable": True,
                },
                "previousClosingPrice": 2612.02,
            },
            "assetCategory": "Aktier",
            "category": "Aktieindex",
            "subCategory": "OMX Stockholm 30 Index",
            "issuer": "Morgan Stanley & Co. International plc",
            "direction": "Kort",
            "leverage": 20.0,
            "documents": {
                "kid": "https://api.priiphub.com/hub/kid-portal/kid/identifier/...",
                "prospectus": "https://etp.morganstanley.com/SE/sv-SE/UnitedDocumentSection/...",
            },
            "fee": {"totalMonetaryFee": 15.96, "totalPercentageFee": 0.16},
            "trades": [],
            "orderDepth": {
                "receivedTime": 1717491925305,
                "levels": [
                    {
                        "buySide": {"price": 0.003, "priceString": "0.003", "volume": 10000000},
                        "sellSide": {"price": 0.254, "priceString": "0.254", "volume": 85325},
                    },
                    {
                        "buySide": {"price": 0.0, "priceString": "0.00", "volume": 0.0},
                        "sellSide": {"price": 0.35, "priceString": "0.350", "volume": 87542},
                    },
                    {
                        "buySide": {"price": 0.0, "priceString": "0.00", "volume": 0.0},
                        "sellSide": {"price": 0.47, "priceString": "0.470", "volume": 154223},
                    },
                ],
                "marketMakerLevelInBid": 0,
            },
            "orderDepthLevels": [
                {
                    "buySide": {
                        "price": 0.003,
                        "priceString": "0.003",
                        "volume": 10000000,
                    },
                    "sellSide": {
                        "price": 0.254,
                        "priceString": "0.254",
                        "volume": 85325,
                    },
                },
                {
                    "buySide": {"price": 0.0, "priceString": "0.00", "volume": 0.0},
                    "sellSide": {
                        "price": 0.35,
                        "priceString": "0.350",
                        "volume": 87542,
                    },
                },
                {
                    "buySide": {"price": 0.0, "priceString": "0.00", "volume": 0.0},
                    "sellSide": {
                        "price": 0.47,
                        "priceString": "0.470",
                        "volume": 154223,
                    },
                },
            ],
            "brokerTradeSummaries": [],
            "collateralValue": 0.0,
        }

        assert isinstance(InstrumentCertificate(**mock_certificate), InstrumentCertificate)
