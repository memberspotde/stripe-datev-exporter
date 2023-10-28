from datetime import datetime
import decimal
import json
from os import path
import unittest
from stripe_datev import config
from stripe_datev.helpers.invoicehelpers import get_creditnote_revenue_line_item

mockpath = path.join(path.dirname(path.realpath(__file__)), 'mocks')


class TestGetRevenueLineItemAmount(unittest.TestCase):

  def test_get_creditnote_revenue_line_item_1_return_cntime_as_recognition(self):
    with open(path.join(mockpath, 'creditnote_mock_1_norecognition.json')) as creditnote_file:
      creditnote_mock_1 = json.load(creditnote_file)

    with open(path.join(mockpath, 'invoice_mock_1_norecognition.json')) as invoice_file:
      invoice_mock_1 = json.load(invoice_file)

    rev_item = get_creditnote_revenue_line_item(
      creditnote_mock_1, invoice_mock_1,
      creditnote_mock_1["lines"]["data"][0],
      0
    )
    self.assertEqual(rev_item["line_item_idx"], 0)
    self.assertEqual(rev_item["recognition_start"], datetime.fromtimestamp(
      1698452121).astimezone(config.accounting_tz))
    self.assertEqual(rev_item["recognition_end"], datetime.fromtimestamp(
      1698452121).astimezone(config.accounting_tz))

    self.assertEqual(rev_item["amount_net"], decimal.Decimal("720.00"))
    self.assertEqual(rev_item["amount_with_tax"], decimal.Decimal("856.8"))

  def test_get_creditnote_revenue_line_item_2_return_invoice_item_as_recognition(self):

    with open(path.join(mockpath, 'creditnote_mock_2_2month_later_half.json')) as creditnote_file:
      creditnoe_mock_2_2month_later_half = json.load(creditnote_file)

    with open(path.join(mockpath, 'invoice_mock_2_2month_later_half.json')) as invoice_file:
      invoice_mock_2_2month_later_half = json.load(invoice_file)

    rev_item = get_creditnote_revenue_line_item(
      creditnoe_mock_2_2month_later_half, invoice_mock_2_2month_later_half,
      creditnoe_mock_2_2month_later_half["lines"]["data"][0],
      0
    )
    self.assertEqual(rev_item["line_item_idx"], 0)
    self.assertEqual(rev_item["recognition_start"], datetime.fromtimestamp(
      1692367077).astimezone(config.accounting_tz))
    self.assertEqual(rev_item["recognition_end"], datetime.fromtimestamp(
      1723989477).astimezone(config.accounting_tz))

    self.assertEqual(rev_item["amount_net"], decimal.Decimal("2000.00"))
    self.assertEqual(rev_item["amount_with_tax"], decimal.Decimal("2380"))


if __name__ == '__main__':
  unittest.main()
