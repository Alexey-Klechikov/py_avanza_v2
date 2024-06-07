from unittest import TestCase

from src.clients.avanza_bank.models.account.overview import AccountOverview


class Test_AccountOverview(TestCase):
    def test_account_overview(self):
        mock_account_overview = {
            "totalValue": {
                "totalValue": {
                    "value": 10000.01,
                    "unit": "SEK",
                    "unitType": "MONETARY",
                    "decimalPrecision": 4,
                },
                "positionValue": {
                    "value": 10000.01,
                    "unit": "SEK",
                    "unitType": "MONETARY",
                    "decimalPrecision": 4,
                },
                "balanceOnTradingAccounts": {
                    "value": 1.95,
                    "unit": "SEK",
                    "unitType": "MONETARY",
                    "decimalPrecision": 4,
                },
                "balanceOnSavingsAccounts": {
                    "value": 0,
                    "unit": "SEK",
                    "unitType": "MONETARY",
                    "decimalPrecision": 0,
                },
                "accruedInterest": {
                    "value": 0,
                    "unit": "SEK",
                    "unitType": "MONETARY",
                    "decimalPrecision": 0,
                },
                "accruedCreditInterest": {
                    "value": 0,
                    "unit": "SEK",
                    "unitType": "MONETARY",
                    "decimalPrecision": 0,
                },
                "accruedDebitInterest": {
                    "value": 0,
                    "unit": "SEK",
                    "unitType": "MONETARY",
                    "decimalPrecision": 0,
                },
                "forwardBalance": {
                    "value": 0.0,
                    "unit": "SEK",
                    "unitType": "MONETARY",
                    "decimalPrecision": 2,
                },
                "currencyBalances": [
                    {
                        "balance": {
                            "value": 1.95,
                            "unit": "SEK",
                            "unitType": "MONETARY",
                            "decimalPrecision": 2,
                        },
                    },
                ],
            },
            "totalDevelopment": {
                "ONE_WEEK": {
                    "absolute": {
                        "value": -1000.82,
                        "unit": "SEK",
                        "unitType": "MONETARY",
                        "decimalPrecision": 2,
                    },
                    "relative": {
                        "value": -0.38,
                        "unit": "percentage",
                        "unitType": "PERCENTAGE",
                        "decimalPrecision": 2,
                    },
                },
                "ONE_MONTH": {
                    "absolute": {
                        "value": 2000.36,
                        "unit": "SEK",
                        "unitType": "MONETARY",
                        "decimalPrecision": 2,
                    },
                    "relative": {
                        "value": 1.05,
                        "unit": "percentage",
                        "unitType": "PERCENTAGE",
                        "decimalPrecision": 2,
                    },
                },
                "THREE_MONTHS": {
                    "absolute": {
                        "value": 10000.98,
                        "unit": "SEK",
                        "unitType": "MONETARY",
                        "decimalPrecision": 2,
                    },
                    "relative": {
                        "value": 5.63,
                        "unit": "percentage",
                        "unitType": "PERCENTAGE",
                        "decimalPrecision": 2,
                    },
                },
                "THIS_YEAR": {
                    "absolute": {
                        "value": 20000.67,
                        "unit": "SEK",
                        "unitType": "MONETARY",
                        "decimalPrecision": 2,
                    },
                    "relative": {
                        "value": 14.5,
                        "unit": "percentage",
                        "unitType": "PERCENTAGE",
                        "decimalPrecision": 2,
                    },
                },
                "ONE_YEAR": {
                    "absolute": {
                        "value": 20000.59,
                        "unit": "SEK",
                        "unitType": "MONETARY",
                        "decimalPrecision": 2,
                    },
                    "relative": {
                        "value": 12.7,
                        "unit": "percentage",
                        "unitType": "PERCENTAGE",
                        "decimalPrecision": 2,
                    },
                },
                "THREE_YEARS": {
                    "absolute": {
                        "value": 10000.83,
                        "unit": "SEK",
                        "unitType": "MONETARY",
                        "decimalPrecision": 2,
                    },
                    "relative": {
                        "value": 5.46,
                        "unit": "percentage",
                        "unitType": "PERCENTAGE",
                        "decimalPrecision": 2,
                    },
                },
                "ALL_TIME": {
                    "absolute": {
                        "value": 10000.14,
                        "unit": "SEK",
                        "unitType": "MONETARY",
                        "decimalPrecision": 2,
                    },
                    "relative": {
                        "value": 28.52,
                        "unit": "percentage",
                        "unitType": "PERCENTAGE",
                        "decimalPrecision": 2,
                    },
                },
            },
            "buyingPower": {
                "total": {
                    "value": 1.95,
                    "unit": "SEK",
                    "unitType": "MONETARY",
                    "decimalPrecision": 2,
                },
                "totalExcludingCredit": {
                    "value": 1.95,
                    "unit": "SEK",
                    "unitType": "MONETARY",
                    "decimalPrecision": 2,
                },
                "balanceOnTradableAccounts": {
                    "value": 1.95,
                    "unit": "SEK",
                    "unitType": "MONETARY",
                    "decimalPrecision": 4,
                },
                "currentOrders": {
                    "value": 0.0,
                    "unit": "SEK",
                    "unitType": "MONETARY",
                    "decimalPrecision": 2,
                },
                "availableCredit": {
                    "value": 0.0,
                    "unit": "SEK",
                    "unitType": "MONETARY",
                    "decimalPrecision": 2,
                },
                "totalMarginRequirement": {
                    "value": 0.0,
                    "unit": "SEK",
                    "unitType": "MONETARY",
                    "decimalPrecision": 2,
                },
                "forwardResult": {
                    "value": 0.0,
                    "unit": "SEK",
                    "unitType": "MONETARY",
                    "decimalPrecision": 2,
                },
                "grossExposureLimit": {
                    "value": 0,
                    "unit": "SEK",
                    "unitType": "MONETARY",
                    "decimalPrecision": 0,
                },
                "grossExposure": {
                    "value": 0,
                    "unit": "SEK",
                    "unitType": "MONETARY",
                    "decimalPrecision": 0,
                },
                "negativeAccruedInterest": {
                    "value": 0.0,
                    "unit": "SEK",
                    "unitType": "MONETARY",
                    "decimalPrecision": 4,
                },
                "currencyBalances": [
                    {
                        "balance": {
                            "value": 1.95,
                            "unit": "SEK",
                            "unitType": "MONETARY",
                            "decimalPrecision": 2,
                        },
                    },
                ],
            },
            "hasCredit": False,
            "accounts": [
                {
                    "info": {
                        "id": "6574382",
                        "type": "INVESTERINGSSPARKONTO",
                        "name": "Vacation",
                        "urlParameterId": "cyy7TCG1GSoM_h-iSW3bBA",
                        "hasCredit": False,
                    },
                    "tradable": True,
                    "totalValue": {
                        "totalValue": {
                            "value": 5000.2339,
                            "unit": "SEK",
                            "unitType": "MONETARY",
                            "decimalPrecision": 4,
                        },
                        "positionValue": {
                            "value": 5000.9539,
                            "unit": "SEK",
                            "unitType": "MONETARY",
                            "decimalPrecision": 4,
                        },
                        "balanceOnTradingAccounts": {
                            "value": 0.28,
                            "unit": "SEK",
                            "unitType": "MONETARY",
                            "decimalPrecision": 4,
                        },
                        "balanceOnSavingsAccounts": {
                            "value": 0,
                            "unit": "SEK",
                            "unitType": "MONETARY",
                            "decimalPrecision": 0,
                        },
                        "accruedInterest": {
                            "value": 0.0,
                            "unit": "SEK",
                            "unitType": "MONETARY",
                            "decimalPrecision": 4,
                        },
                        "accruedCreditInterest": {
                            "value": 0.0,
                            "unit": "SEK",
                            "unitType": "MONETARY",
                            "decimalPrecision": 4,
                        },
                        "accruedDebitInterest": {
                            "value": 0.0,
                            "unit": "SEK",
                            "unitType": "MONETARY",
                            "decimalPrecision": 4,
                        },
                        "forwardBalance": {
                            "value": 0.0,
                            "unit": "SEK",
                            "unitType": "MONETARY",
                            "decimalPrecision": 2,
                        },
                        "currencyBalances": [
                            {
                                "balance": {
                                    "value": 0.28,
                                    "unit": "SEK",
                                    "unitType": "MONETARY",
                                    "decimalPrecision": 2,
                                },
                            },
                        ],
                    },
                    "buyingPower": {
                        "total": {
                            "value": 0.28,
                            "unit": "SEK",
                            "unitType": "MONETARY",
                            "decimalPrecision": 2,
                        },
                        "totalExcludingCredit": {
                            "value": 0.28,
                            "unit": "SEK",
                            "unitType": "MONETARY",
                            "decimalPrecision": 2,
                        },
                        "balanceOnTradableAccounts": {
                            "value": 0.28,
                            "unit": "SEK",
                            "unitType": "MONETARY",
                            "decimalPrecision": 4,
                        },
                        "currentOrders": {
                            "value": 0.0,
                            "unit": "SEK",
                            "unitType": "MONETARY",
                            "decimalPrecision": 2,
                        },
                        "availableCredit": {
                            "value": 0.0,
                            "unit": "SEK",
                            "unitType": "MONETARY",
                            "decimalPrecision": 2,
                        },
                        "totalMarginRequirement": {
                            "value": 0.0,
                            "unit": "SEK",
                            "unitType": "MONETARY",
                            "decimalPrecision": 2,
                        },
                        "forwardResult": {
                            "value": 0.0,
                            "unit": "SEK",
                            "unitType": "MONETARY",
                            "decimalPrecision": 2,
                        },
                        "grossExposureLimit": {
                            "value": 0,
                            "unit": "SEK",
                            "unitType": "MONETARY",
                            "decimalPrecision": 0,
                        },
                        "grossExposure": {
                            "value": 0,
                            "unit": "SEK",
                            "unitType": "MONETARY",
                            "decimalPrecision": 0,
                        },
                        "negativeAccruedInterest": {
                            "value": 0.0,
                            "unit": "SEK",
                            "unitType": "MONETARY",
                            "decimalPrecision": 4,
                        },
                        "currencyBalances": [
                            {
                                "balance": {
                                    "value": 0.28,
                                    "unit": "SEK",
                                    "unitType": "MONETARY",
                                    "decimalPrecision": 2,
                                },
                            },
                        ],
                    },
                    "isTradable": True,
                },
                {
                    "info": {
                        "id": "1234567869",
                        "type": "AKTIEFONDKONTO",
                        "name": "1234567869",
                        "urlParameterId": "asdasdasdasda",
                        "hasCredit": False,
                    },
                    "tradable": True,
                    "totalValue": {
                        "totalValue": {
                            "value": 0.04,
                            "unit": "SEK",
                            "unitType": "MONETARY",
                            "decimalPrecision": 4,
                        },
                        "positionValue": {
                            "value": 0.0,
                            "unit": "SEK",
                            "unitType": "MONETARY",
                            "decimalPrecision": 4,
                        },
                        "balanceOnTradingAccounts": {
                            "value": 0.04,
                            "unit": "SEK",
                            "unitType": "MONETARY",
                            "decimalPrecision": 4,
                        },
                        "balanceOnSavingsAccounts": {
                            "value": 0,
                            "unit": "SEK",
                            "unitType": "MONETARY",
                            "decimalPrecision": 0,
                        },
                        "accruedInterest": {
                            "value": 0.0,
                            "unit": "SEK",
                            "unitType": "MONETARY",
                            "decimalPrecision": 4,
                        },
                        "accruedCreditInterest": {
                            "value": 0.0,
                            "unit": "SEK",
                            "unitType": "MONETARY",
                            "decimalPrecision": 4,
                        },
                        "accruedDebitInterest": {
                            "value": 0.0,
                            "unit": "SEK",
                            "unitType": "MONETARY",
                            "decimalPrecision": 4,
                        },
                        "forwardBalance": {
                            "value": 0.0,
                            "unit": "SEK",
                            "unitType": "MONETARY",
                            "decimalPrecision": 2,
                        },
                        "currencyBalances": [
                            {
                                "balance": {
                                    "value": 0.04,
                                    "unit": "SEK",
                                    "unitType": "MONETARY",
                                    "decimalPrecision": 2,
                                },
                            },
                        ],
                    },
                    "buyingPower": {
                        "total": {
                            "value": 0.04,
                            "unit": "SEK",
                            "unitType": "MONETARY",
                            "decimalPrecision": 2,
                        },
                        "totalExcludingCredit": {
                            "value": 0.04,
                            "unit": "SEK",
                            "unitType": "MONETARY",
                            "decimalPrecision": 2,
                        },
                        "balanceOnTradableAccounts": {
                            "value": 0.04,
                            "unit": "SEK",
                            "unitType": "MONETARY",
                            "decimalPrecision": 4,
                        },
                        "currentOrders": {
                            "value": 0.0,
                            "unit": "SEK",
                            "unitType": "MONETARY",
                            "decimalPrecision": 2,
                        },
                        "availableCredit": {
                            "value": 0.0,
                            "unit": "SEK",
                            "unitType": "MONETARY",
                            "decimalPrecision": 2,
                        },
                        "totalMarginRequirement": {
                            "value": 0.0,
                            "unit": "SEK",
                            "unitType": "MONETARY",
                            "decimalPrecision": 2,
                        },
                        "forwardResult": {
                            "value": 0.0,
                            "unit": "SEK",
                            "unitType": "MONETARY",
                            "decimalPrecision": 2,
                        },
                        "grossExposureLimit": {
                            "value": 0,
                            "unit": "SEK",
                            "unitType": "MONETARY",
                            "decimalPrecision": 0,
                        },
                        "grossExposure": {
                            "value": 0,
                            "unit": "SEK",
                            "unitType": "MONETARY",
                            "decimalPrecision": 0,
                        },
                        "negativeAccruedInterest": {
                            "value": 0.0,
                            "unit": "SEK",
                            "unitType": "MONETARY",
                            "decimalPrecision": 4,
                        },
                        "currencyBalances": [
                            {
                                "balance": {
                                    "value": 0.04,
                                    "unit": "SEK",
                                    "unitType": "MONETARY",
                                    "decimalPrecision": 2,
                                },
                            },
                        ],
                    },
                    "isTradable": True,
                },
                {
                    "info": {
                        "id": "123123123123",
                        "type": "INVESTERINGSSPARKONTO",
                        "name": "Main",
                        "urlParameterId": "12asdasdasd",
                        "hasCredit": False,
                    },
                    "tradable": True,
                    "totalValue": {
                        "totalValue": {
                            "value": 20000.3951,
                            "unit": "SEK",
                            "unitType": "MONETARY",
                            "decimalPrecision": 4,
                        },
                        "positionValue": {
                            "value": 20000.6451,
                            "unit": "SEK",
                            "unitType": "MONETARY",
                            "decimalPrecision": 4,
                        },
                        "balanceOnTradingAccounts": {
                            "value": 0.75,
                            "unit": "SEK",
                            "unitType": "MONETARY",
                            "decimalPrecision": 4,
                        },
                        "balanceOnSavingsAccounts": {
                            "value": 0,
                            "unit": "SEK",
                            "unitType": "MONETARY",
                            "decimalPrecision": 0,
                        },
                        "accruedInterest": {
                            "value": 0.0,
                            "unit": "SEK",
                            "unitType": "MONETARY",
                            "decimalPrecision": 4,
                        },
                        "accruedCreditInterest": {
                            "value": 0.0,
                            "unit": "SEK",
                            "unitType": "MONETARY",
                            "decimalPrecision": 4,
                        },
                        "accruedDebitInterest": {
                            "value": 0.0,
                            "unit": "SEK",
                            "unitType": "MONETARY",
                            "decimalPrecision": 4,
                        },
                        "forwardBalance": {
                            "value": 0.0,
                            "unit": "SEK",
                            "unitType": "MONETARY",
                            "decimalPrecision": 2,
                        },
                        "currencyBalances": [
                            {
                                "balance": {
                                    "value": 0.75,
                                    "unit": "SEK",
                                    "unitType": "MONETARY",
                                    "decimalPrecision": 2,
                                },
                            },
                        ],
                    },
                    "buyingPower": {
                        "total": {
                            "value": 0.75,
                            "unit": "SEK",
                            "unitType": "MONETARY",
                            "decimalPrecision": 2,
                        },
                        "totalExcludingCredit": {
                            "value": 0.75,
                            "unit": "SEK",
                            "unitType": "MONETARY",
                            "decimalPrecision": 2,
                        },
                        "balanceOnTradableAccounts": {
                            "value": 0.75,
                            "unit": "SEK",
                            "unitType": "MONETARY",
                            "decimalPrecision": 4,
                        },
                        "currentOrders": {
                            "value": 0.0,
                            "unit": "SEK",
                            "unitType": "MONETARY",
                            "decimalPrecision": 2,
                        },
                        "availableCredit": {
                            "value": 0.0,
                            "unit": "SEK",
                            "unitType": "MONETARY",
                            "decimalPrecision": 2,
                        },
                        "totalMarginRequirement": {
                            "value": 0.0,
                            "unit": "SEK",
                            "unitType": "MONETARY",
                            "decimalPrecision": 2,
                        },
                        "forwardResult": {
                            "value": 0.0,
                            "unit": "SEK",
                            "unitType": "MONETARY",
                            "decimalPrecision": 2,
                        },
                        "grossExposureLimit": {
                            "value": 0,
                            "unit": "SEK",
                            "unitType": "MONETARY",
                            "decimalPrecision": 0,
                        },
                        "grossExposure": {
                            "value": 0,
                            "unit": "SEK",
                            "unitType": "MONETARY",
                            "decimalPrecision": 0,
                        },
                        "negativeAccruedInterest": {
                            "value": 0.0,
                            "unit": "SEK",
                            "unitType": "MONETARY",
                            "decimalPrecision": 4,
                        },
                        "currencyBalances": [
                            {
                                "balance": {
                                    "value": 0.75,
                                    "unit": "SEK",
                                    "unitType": "MONETARY",
                                    "decimalPrecision": 2,
                                },
                            },
                        ],
                    },
                    "isTradable": True,
                },
                {
                    "info": {
                        "id": "1231231231",
                        "type": "INVESTERINGSSPARKONTO",
                        "name": "DT",
                        "urlParameterId": "sdfsdgfwefdqa",
                        "hasCredit": False,
                    },
                    "tradable": True,
                    "totalValue": {
                        "totalValue": {
                            "value": 1000.1544,
                            "unit": "SEK",
                            "unitType": "MONETARY",
                            "decimalPrecision": 4,
                        },
                        "positionValue": {
                            "value": 1000.2744,
                            "unit": "SEK",
                            "unitType": "MONETARY",
                            "decimalPrecision": 4,
                        },
                        "balanceOnTradingAccounts": {
                            "value": 0.88,
                            "unit": "SEK",
                            "unitType": "MONETARY",
                            "decimalPrecision": 4,
                        },
                        "balanceOnSavingsAccounts": {
                            "value": 0,
                            "unit": "SEK",
                            "unitType": "MONETARY",
                            "decimalPrecision": 0,
                        },
                        "accruedInterest": {
                            "value": 0.0,
                            "unit": "SEK",
                            "unitType": "MONETARY",
                            "decimalPrecision": 4,
                        },
                        "accruedCreditInterest": {
                            "value": 0.0,
                            "unit": "SEK",
                            "unitType": "MONETARY",
                            "decimalPrecision": 4,
                        },
                        "accruedDebitInterest": {
                            "value": 0.0,
                            "unit": "SEK",
                            "unitType": "MONETARY",
                            "decimalPrecision": 4,
                        },
                        "forwardBalance": {
                            "value": 0.0,
                            "unit": "SEK",
                            "unitType": "MONETARY",
                            "decimalPrecision": 2,
                        },
                        "currencyBalances": [
                            {
                                "balance": {
                                    "value": 0.88,
                                    "unit": "SEK",
                                    "unitType": "MONETARY",
                                    "decimalPrecision": 2,
                                },
                            },
                        ],
                    },
                    "buyingPower": {
                        "total": {
                            "value": 0.88,
                            "unit": "SEK",
                            "unitType": "MONETARY",
                            "decimalPrecision": 2,
                        },
                        "totalExcludingCredit": {
                            "value": 0.88,
                            "unit": "SEK",
                            "unitType": "MONETARY",
                            "decimalPrecision": 2,
                        },
                        "balanceOnTradableAccounts": {
                            "value": 0.88,
                            "unit": "SEK",
                            "unitType": "MONETARY",
                            "decimalPrecision": 4,
                        },
                        "currentOrders": {
                            "value": 0.0,
                            "unit": "SEK",
                            "unitType": "MONETARY",
                            "decimalPrecision": 2,
                        },
                        "availableCredit": {
                            "value": 0.0,
                            "unit": "SEK",
                            "unitType": "MONETARY",
                            "decimalPrecision": 2,
                        },
                        "totalMarginRequirement": {
                            "value": 0.0,
                            "unit": "SEK",
                            "unitType": "MONETARY",
                            "decimalPrecision": 2,
                        },
                        "forwardResult": {
                            "value": 0.0,
                            "unit": "SEK",
                            "unitType": "MONETARY",
                            "decimalPrecision": 2,
                        },
                        "grossExposureLimit": {
                            "value": 0,
                            "unit": "SEK",
                            "unitType": "MONETARY",
                            "decimalPrecision": 0,
                        },
                        "grossExposure": {
                            "value": 0,
                            "unit": "SEK",
                            "unitType": "MONETARY",
                            "decimalPrecision": 0,
                        },
                        "negativeAccruedInterest": {
                            "value": 0.0,
                            "unit": "SEK",
                            "unitType": "MONETARY",
                            "decimalPrecision": 4,
                        },
                        "currencyBalances": [
                            {
                                "balance": {
                                    "value": 0.88,
                                    "unit": "SEK",
                                    "unitType": "MONETARY",
                                    "decimalPrecision": 2,
                                },
                            },
                        ],
                    },
                    "isTradable": True,
                },
            ],
        }

        assert isinstance(AccountOverview(**mock_account_overview), AccountOverview)
