from datetime import datetime
import decimal
import json
from os import path
import unittest
from unittest.mock import patch
from stripe_datev import config
from stripe_datev.creditnotes import create_creditnote_accounting_records, create_revenue_item_creditnote
from dotmap import DotMap

mockpath = path.join(path.dirname(path.realpath(__file__)), 'mocks')


class TestGetCreditnoteAccountingRecords(unittest.TestCase):

  @patch('stripe_datev.customer.retrieveCustomer')
  @patch('stripe.Customer.list_tax_ids')
  @patch('stripe.Invoice.retrieve')
  def test_get_creditnote_accounting_records_1(self, mock_invoice_retrieve, mock_list_tax_ids, mock_customer_retrieve):
    with open(path.join(mockpath, 'mock_3_creditnote_inv_02_cn_05.json')) as creditnote_file:
      creditnote_mock_1 = json.load(creditnote_file)

    with open(path.join(mockpath, 'mock_3_invoice_inv_02_cn_05.json')) as invoice_file:
      invoice_mock_1 = json.load(invoice_file)

    with open(path.join(mockpath, 'mock_3_customer_inv_02_cn_05.json')) as customer_file:
      customer_mock_1 = json.load(customer_file)

    with open(path.join(mockpath, 'mock_3_taxids_inv_02_cn_05.json')) as taxids_file:
      taxids_mock = json.load(taxids_file)

    mock_invoice_retrieve.return_value = DotMap(invoice_mock_1)
    mock_customer_retrieve.return_value = DotMap(customer_mock_1)
    mock_list_tax_ids.return_value = DotMap(taxids_mock)

    rev_items = create_revenue_item_creditnote(
      [DotMap(creditnote_mock_1)])

    accounting_items = create_creditnote_accounting_records(rev_items[0])

    self.assertEqual(len(accounting_items), 11)

    el0 = accounting_items[0]
    self.assertEqual(el0["Soll/Haben-Kennzeichen"], "H")
    self.assertEqual(el0["Umsatz (ohne Soll/Haben-Kz)"], "915,06")
    self.assertEqual(
      el0["date"], datetime.fromtimestamp(1684825652).astimezone(config.accounting_tz))

    el1 = accounting_items[1]
    self.assertEqual(el1["Soll/Haben-Kennzeichen"], "H")
    self.assertEqual(el1["Umsatz (ohne Soll/Haben-Kz)"], "627,63")
    self.assertEqual(
      el1["date"], datetime.fromtimestamp(1684825652).astimezone(config.accounting_tz))

    sumPrap = sum(
      decimal.Decimal(item["Umsatz (ohne Soll/Haben-Kz)"].replace(",", ".")) for item in accounting_items[2:]
    )
    self.assertEqual(sumPrap, decimal.Decimal(
      el1["Umsatz (ohne Soll/Haben-Kz)"].replace(",", ".")))
    print(sumPrap)


if __name__ == '__main__':
  unittest.main()
