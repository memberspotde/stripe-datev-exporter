import datetime
import os
import unittest

import dotenv
import stripe
from stripe_datev.creditnotes import listCreditedInvoices
from stripe_datev.xml import create_xml

dotenv.load_dotenv()


class TestCreditNotes(unittest.TestCase):

  def test_list_invoices(self):
    stripe.api_key = os.environ["STRIPE_API_KEY"]
    print(os.environ["STRIPE_API_KEY"])
    stripe.api_version = "2020-08-27"
    listCreditedInvoices(datetime.datetime(2023, 5, 1),
                         datetime.datetime(2023, 5, 30)),


if __name__ == '__main__':

  unittest.main()
