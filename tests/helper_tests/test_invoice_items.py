from datetime import datetime
import decimal
import unittest
from stripe_datev import config
from stripe_datev.helpers.invoicehelpers import get_line_item_amounts, get_line_item_recognition_range
from tests.helper_tests.mocks.invoice_line_item_mocks import line_item_mock_1, line_item_mock_2, invoice_mock_1


class TestGetLineItemAmount(unittest.TestCase):

  def test_get_line_item_amount_1(self):
    li_net, li_total = get_line_item_amounts(line_item_mock_1)
    self.assertEqual(li_net, decimal.Decimal('180.00'))
    self.assertEqual(li_total, decimal.Decimal('216.00'))

  def test_get_line_item_amount_2(self):
    li_net, li_total = get_line_item_amounts(line_item_mock_2)
    self.assertEqual(li_net, decimal.Decimal('2000.00'))
    self.assertEqual(li_total, decimal.Decimal('2000.00'))


class TestGetLineItemRecognition(unittest.TestCase):

  def test_get_line_item_recognition_1(self):
    start, end = get_line_item_recognition_range(
      line_item_mock_1, invoice_mock_1)
    self.assertEqual(start, datetime.fromtimestamp(
      1698449000).astimezone(config.accounting_tz))
    self.assertEqual(end, datetime.fromtimestamp(
      1698449000).astimezone(config.accounting_tz))

  def test_get_line_item_recognition_2(self):
    start, end = get_line_item_recognition_range(
      line_item_mock_2, invoice_mock_1)
    self.assertEqual(start, datetime.fromtimestamp(
      1695486679).astimezone(config.accounting_tz))
    self.assertEqual(end, datetime.fromtimestamp(
      1727109079).astimezone(config.accounting_tz))


if __name__ == '__main__':
  unittest.main()
