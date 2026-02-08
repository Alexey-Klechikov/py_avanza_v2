from unittest import TestCase

from apis.avanza.client.models.instrument.fund import InstrumentFund


class TestInstrumentFund(TestCase):
    def test_fund(self):
        mock_fund = {
            "adminCompany": {"country": "Sverige", "name": "Avanza", "url": "http://www.avanzafonder.se"},
            "arcticOilAndGasExplorationInvolvement": 0.0,
            "aumCoveredCarbon": None,
            "capital": 68330647652.0,
            "carbonRiskScore": 8.45,
            "carbonSolutionsInvolvement": None,
            "categories": ["Sverige"],
            "collateralValue": 80.0,
            "controversyScore": None,
            "countryChartData": [
                {
                    "countryCode": "SE",
                    "currency": None,
                    "deltaRank": 0,
                    "isin": None,
                    "name": "Sverige",
                    "orderbookId": None,
                    "previousY": 91.97,
                    "type": None,
                    "y": 92.01,
                },
            ],
            "currency": "SEK",
            "currentDateTime": "2026-02-08T20:56:56",
            "description": "Fonden är en passivt förvaltad indexfond vars mål är att ge "
            "andelsägarna en värdeutveckling i linje med utvecklingen för "
            "SIX30 Return Index (SIX30RX) genom att placera i de i index "
            "ingående aktierna. SIX30RX är uppbyggt kring de 30 "
            "värdemässigt mest omsatta aktierna på Stockholmsbörsen och "
            "inkluderar utdelningar. I SIX30RX tillämpas en screening som "
            "innebär att företag, som bedöms bryta mot internationella "
            "normer och konventioner såsom FN Global Compacts principer, "
            "kan komma att exkluderas från index. Även företag som är "
            "involverade i kontroversiella vapen exkluderas från SIX30RX. "
            "Förutom överlåtbara värdepapper får fonden placera i "
            "fondandelar där SIX30RX är den underliggande tillgången och i "
            "derivatinstrument. Fonden får använda derivatinstrument i "
            "syfte att effektivisera förvaltningen. Högsta "
            "engångsinsättning är 25 000 SEK.",
            "environmentalRating": 0,
            "environmentalScore": 5.53,
            "esgScore": 18.81,
            "euArticleType": {"name": "Artikel 6", "value": "ARTICLE_TYPE_SIX"},
            "excludedFromPromotion": False,
            "fossilFuelInvolvement": None,
            "fundManagers": [{"name": "Emilie Chawala", "startDate": "2013-01-01"}],
            "fundRatings": [
                {"date": "2026-01-31T00:00:00", "fundRating": 5, "fundRatingType": "THREE_YEARS"},
                {"date": "2026-01-31T00:00:00", "fundRating": 5, "fundRatingType": "FIVE_YEARS"},
                {"date": "2026-01-31T00:00:00", "fundRating": 5, "fundRatingType": "TEN_YEARS"},
                {"date": "2026-01-31T00:00:00", "fundRating": 5, "fundRatingType": "ALL_TIME"},
            ],
            "fundTradingTerms": {
                "bankDaysUntilBuy": "Samma dag",
                "bankDaysUntilSell": "Samma dag",
                "bankDaysUntilVisibleInDepotWhenBuy": "Nästa bankdag",
                "bankDaysUntilVisibleInDepotWhenSell": "Nästa bankdag",
                "buyPriceDenominator": None,
                "buyStopDateTime": "2026-02-09T13:00:00",
                "feeInfo": None,
                "hasCashDividends": False,
                "hasCurrencyExchangeFee": False,
                "lockInIntervalInMonths": 0,
                "minimumBuy": 1.0,
                "minimumBuyMonthlySaving": 1.0,
                "minimumThresholdAdditionalBuy": 1.0,
                "orderbookId": "41567",
                "privateAsset": False,
                "sellStopDateTime": "2026-02-09T13:00:00",
                "tradeCurrency": "SEK",
                "tradeFrequency": "Dagligen",
                "tradingInfo": "Högsta köpbelopp är 25 000 kr per dag.",
            },
            "fundType": "EQUITY_FUND",
            "fundTypeName": "Aktiefond",
            "governanceRating": 0,
            "governanceScore": 5.39,
            "hedgeFund": False,
            "holdingChartData": [
                {
                    "countryCode": "SE",
                    "currency": "SEK",
                    "deltaRank": 0,
                    "isin": "SE0015811963",
                    "name": "Investor B",
                    "orderbookId": "5247",
                    "previousY": 8.46,
                    "type": "HOLDING_TYPE_EQUITY",
                    "y": 8.3,
                },
                {
                    "countryCode": "SE",
                    "currency": "SEK",
                    "deltaRank": 0,
                    "isin": "SE0017486889",
                    "name": "Atlas Copco A",
                    "orderbookId": "5234",
                    "previousY": 7.84,
                    "type": "HOLDING_TYPE_EQUITY",
                    "y": 8.19,
                },
                {
                    "countryCode": "SE",
                    "currency": "SEK",
                    "deltaRank": 0,
                    "isin": "SE0000115446",
                    "name": "Volvo B",
                    "orderbookId": "5269",
                    "previousY": 6.61,
                    "type": "HOLDING_TYPE_EQUITY",
                    "y": 6.83,
                },
            ],
            "indexFund": True,
            "isin": "SE0001718388",
            "lowCarbon": False,
            "managedType": "INDEX",
            "managementFee": 0.0,
            "name": "Avanza Zero",
            "nav": 521.19,
            "navDate": "2026-02-05T00:00:00",
            "oilAndGasProductionInvolvement": None,
            "oilSandsExtractionInvolvement": 0.0,
            "portfolioDate": "2026-01-31",
            "ppmCode": "734491",
            "previousPortfolioDate": "2025-12-31",
            "pricingFrequency": "Dagligen",
            "primaryBenchmark": "SIX30RX",
            "productInvolvements": [
                {"name": "TOBACCO", "product": "tobacco", "productDescription": "Tobak", "value": 0.0},
                {
                    "name": "ADULT_ENTERTAINMENT",
                    "product": "adultEntertainment",
                    "productDescription": "Pornografi",
                    "value": 0.0,
                },
                {
                    "name": "CONTROVERSIAL_WEAPONS",
                    "product": "convtroversialWeapons",
                    "productDescription": "Kontroversiella vapen",
                    "value": 0.0,
                },
            ],
            "rating": 5,
            "recommendedHoldingPeriod": "Minst 5 år",
            "riskLevel": {"riskNumber": 4, "riskText": "Medel"},
            "sectorChartData": [
                {
                    "countryCode": None,
                    "currency": None,
                    "deltaRank": 0,
                    "isin": None,
                    "name": "Industri",
                    "orderbookId": None,
                    "previousY": 41.93,
                    "type": None,
                    "y": 44.0,
                },
                {
                    "countryCode": None,
                    "currency": None,
                    "deltaRank": 0,
                    "isin": None,
                    "name": "Konsument, stabil",
                    "orderbookId": None,
                    "previousY": 2.38,
                    "type": None,
                    "y": 2.24,
                },
            ],
            "sharpeRatio": 0.99,
            "socialRating": 0,
            "socialScore": 7.9,
            "standardDeviation": 11.38,
            "startDate": "2006-05-22",
            "sustainabilityDevelopmentGoals": [
                {"name": "Ingen fattigdom", "status": "NOT_REPORTED", "type": "SOCIAL", "value": "NO_POVERTY"},
                {
                    "name": "Genomförande och globalt " "partnerskap",
                    "status": "NOT_REPORTED",
                    "type": "OVERALL",
                    "value": "PARTNERSHIPS_TO_ACHIEVE_TO_GOAL",
                },
            ],
            "sustainabilityRating": 1,
            "sustainabilityRatingCategoryName": "Aktier, Europa stora bolag",
            "svanen": False,
            "thermalCoalInvolvement": 0.0,
            "thermalCoalPowerGenerationInvolvement": None,
            "ucitsFund": True,
        }

        assert isinstance(InstrumentFund(**mock_fund), InstrumentFund)
