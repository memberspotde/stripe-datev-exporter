import datetime
import os
import unittest

import dotenv
import stripe
from stripe_datev import config

from stripe_datev.balance_transactions import find_all_with_fees, list_charges, list_payment_refunds, list_payments, list_refunds, list_dispute_chargebacks

dotenv.load_dotenv()


class TestDisputes(unittest.TestCase):

  def __init__(self, *args, **kwargs):
    super(TestDisputes, self).__init__(*args, **kwargs)
    stripe.api_key = os.environ["STRIPE_API_KEY"]
    print(os.environ["STRIPE_API_KEY"])
    stripe.api_version = "2020-08-27"
    self.start = datetime.datetime(2023, 9, 1).astimezone(config.accounting_tz)
    self.end = datetime.datetime(2023, 10, 1).astimezone(config.accounting_tz)

  # def test_list_disputes(self):
  #   disputes = list(list_dispute_chargebacks(self.start, self.end))
  #   dispute_sum = sum(dispute["fee"] for dispute in disputes)
  #   print("dispute fees", dispute_sum)

  #   payment_refunds = list_payment_refunds(self.start, self.end)
  #   payment_refund_sum = sum(payment_refund["fee"]
  #                            for payment_refund in payment_refunds)
  #   print("payment refund fees", payment_refund_sum)

  #   refunds = list_refunds(self.start, self.end)
  #   refund_sum = sum(refund["fee"] for refund in refunds)
  #   print("refund fees", refund_sum)

  #   payments = list_payments(self.start, self.end)
  #   payment_sum = sum(payment["fee"] for payment in payments)
  #   print("payment fees", payment_sum)

  #   charges = list_charges(self.start, self.end)
  #   charge_sum = sum(charge["fee"] for charge in charges)
  #   print("charge fees", charge_sum)

  #   all = find_all_with_fees(self.start, self.end)
  #   all_sum = sum(charge["fee"] for charge in all)
  #   print("all fees", all_sum)
  #
  def test_find_type(self):
    trans = list_payment_refunds(self.start, self.end)
    for t in trans:
      if t.id == "txn_1NlVQBDc6Ds2E1iCmGuHtv7C":
        print("found transaction")

  # def test_find_trans(self):

  #   all = find_all_with_fees(self.start, self.end)
  #   for a in all:
  #     if len(a.fee_details) > 1:
  #       print('a.fee_details', a)

  #     if a.type == "stripe_fee":
  #       continue

  #     if not a.source:
  #       print("found transaction without source", a)
  #       continue

  #     if a.source.object == "charge" and a.source.id == "py_1NqQ39Dc6Ds2E1iCHofGnZUr":
  #       print("found transaction", a)

  #     if a.source.object == "charge" and not a.source.invoice:
  #       print("found transaction without invoice", a)


if __name__ == '__main__':

  unittest.main()
