
invoice_mock_1 = {
  "created": 1698449000,
  "id": "invoice_id_1"
}

line_item_mock_1 = {
    "id": "il_1O5zQRDc6Ds2E1iCEYYefuxS",
    "object": "line_item",
    "amount": 20000,
    "amount_excluding_tax": 20000,
    "currency": "eur",
    "description": "AddOn API",
    "discount_amounts": [
          {
            "amount": 2000,
            "discount": "di_1O5zOdDc6Ds2E1iC808nFibF"
          }
    ],
    "discountable": True,
    "discounts": [],
    "invoice_item": "ii_1O5zQRDc6Ds2E1iCcV2qhtdI",
    "livemode": False,
    "metadata": {},
    "period": {
        "end": 1698449207,
        "start": 1698449207
    },
    "plan": None,
    "price": {
        "id": "price_1O5zQQDc6Ds2E1iCeKOWXnL3",
        "object": "price",
        "active": True,
        "billing_scheme": "per_unit",
        "created": 1698449206,
        "currency": "eur",
        "custom_unit_amount": None,
        "livemode": False,
        "lookup_key": None,
        "metadata": {},
        "nickname": None,
        "product": "prod_OI8LYyvbVpW7io",
        "recurring": None,
        "tax_behavior": "unspecified",
        "tiers_mode": None,
        "transform_quantity": None,
        "type": "one_time",
        "unit_amount": 20000,
        "unit_amount_decimal": "20000"
    },
    "proration": False,
    "proration_details": {
        "credited_items": None
    },
    "quantity": 1,
    "subscription": None,
    "tax_amounts": [
        {
            "amount": 3600,
            "inclusive": False,
            "tax_rate": "txr_1Js241Dc6Ds2E1iCZFOn1Wik",
            "taxability_reason": None,
            "taxable_amount": 18000
          }
    ],
    "tax_rates": [
        {
            "id": "txr_1Js241Dc6Ds2E1iCZFOn1Wik",
            "object": "tax_rate",
            "active": True,
            "country": "BG",
            "created": 1636017413,
            "description": None,
            "display_name": "Umsatzsteuer",
            "effective_percentage": None,
            "inclusive": False,
            "jurisdiction": None,
            "livemode": False,
            "metadata": {},
            "percentage": 20.0,
            "state": None,
            "tax_type": None
          }
    ],
    "type": "invoiceitem",
    "unit_amount_excluding_tax": "20000"
}

line_item_mock_2 = {
    "id": "il_1O5zfCDc6Ds2E1iCotpRxZIc",
    "object": "line_item",
    "amount": 200000,
    "amount_excluding_tax": 200000,
    "currency": "eur",
    "description": "Premium-V3",
    "discount_amounts": [],
    "discountable": True,
    "discounts": [],
    "invoice_item": "ii_1O5zfCDc6Ds2E1iCbWxG6wVN",
    "livemode": False,
    "metadata": {},
    "period": {
          "end": 1727109079,
          "start": 1695486679
    },
    "plan": None,
    "price": {
        "id": "price_1O5qMLDc6Ds2E1iCaQ6kQcYc",
        "object": "price",
        "active": True,
        "billing_scheme": "per_unit",
        "created": 1698414357,
        "currency": "eur",
        "custom_unit_amount": None,
        "livemode": False,
        "lookup_key": None,
        "metadata": {},
        "nickname": None,
        "product": "prod_OPGzg63nRzSI2z",
        "recurring": None,
        "tax_behavior": "unspecified",
        "tiers_mode": None,
        "transform_quantity": None,
        "type": "one_time",
        "unit_amount": 200000,
        "unit_amount_decimal": "200000"
    },
    "proration": False,
    "proration_details": {
        "credited_items": None
    },
    "quantity": 1,
    "subscription": None,
    "tax_amounts": [],
    "tax_rates": [],
    "type": "invoiceitem",
    "unit_amount_excluding_tax": "200000"
}
