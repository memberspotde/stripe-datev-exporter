import asyncio
import decimal
from functools import reduce
import sys
import argparse
from datetime import datetime, timedelta, timezone
import uuid
import datedelta
import stripe
from stripe_datev import save_files
from stripe_datev.csv_combine import combine_revenue_extf_csvs
from stripe_datev.helpers.processing import chunker
import stripe_datev.invoices
import stripe_datev.creditnotes
import stripe_datev.balance_transactions
import \
  stripe_datev.charges, \
  stripe_datev.customer, \
  stripe_datev.payouts, \
  stripe_datev.recognition, \
  stripe_datev.output, \
  stripe_datev.config, \
  stripe_datev.transfers \

import os
import os.path
import dotenv
from stripe_datev.utils.print import print_json

from stripe_datev.xml import create_xml
from stripe_datev.zip import zip_compressed_pdfs


dotenv.load_dotenv()

if "STRIPE_API_KEY" not in os.environ:
  print("Require STRIPE_API_KEY environment variable to be set")
  sys.exit(1)

stripe.api_key = os.environ["STRIPE_API_KEY"]
stripe.api_version = "2020-08-27"

out_dir = os.path.join(os.path.dirname(os.path.realpath(__file__)), 'out')
if stripe.api_key.startswith("sk_test"):
  out_dir = os.path.join(out_dir, "test")
if not os.path.exists(out_dir):
  os.mkdir(out_dir)


class StripeDatevCli(object):

  def run(self, argv):
    parser = argparse.ArgumentParser(
      description='Stripe utility',
    )
    parser.add_argument('command', type=str, help='Subcommand to run', choices=[
      'download',
      'validate_customers',
      'fill_account_numbers',
      'list_accounts',
      'opos'
    ])

    args = parser.parse_args(argv[1:2])
    getattr(self, args.command)(argv[2:])

  def download(self, argv):
    parser = argparse.ArgumentParser(prog="stripe-datev-cli.py download")
    parser.add_argument('year', type=int, help='year to download data for')
    parser.add_argument('month', type=int, help='month to download data for')
    parser.add_argument('customer', type=str,
                        help='customer to download data for', default=None, nargs='?')

    args = parser.parse_args(argv)

    year = int(args.year)
    month = int(args.month)
    customer = args.customer

    if customer:
      print("receive data for customer: {}".format(customer))

    if month > 0:
      fromTime = stripe_datev.config.accounting_tz.localize(
        datetime(year, month, 1, 0, 0, 0, 0))
      toTime = fromTime + datedelta.MONTH
      # toTime = fromTime + timedelta(days=2)
    else:
      fromTime = stripe_datev.config.accounting_tz.localize(
        datetime(year, 1, 1, 0, 0, 0, 0))
      toTime = fromTime + datedelta.YEAR
    print("Retrieving data between {} and {}".format(fromTime.strftime(
      "%Y-%m-%d"), (toTime - timedelta(0, 1)).strftime("%Y-%m-%d")))
    thisMonth = fromTime.astimezone(
      stripe_datev.config.accounting_tz).strftime("%Y-%m")

    out_dir_dl = os.path.join(out_dir, thisMonth)
    if not os.path.exists(out_dir_dl):
      os.mkdir(out_dir_dl)

    invoices = list(
      reversed(list(stripe_datev.invoices.listFinalizedInvoices(fromTime, toTime, customer))))
    print("Retrieved {} invoice(s), total {} EUR".format(
      len(invoices), sum([decimal.Decimal(i.total) / 100 for i in invoices])))

    revenue_items = stripe_datev.invoices.createRevenueItems(
      invoices)

    creditnotes = list(
      reversed(list(stripe_datev.creditnotes.list_creditnotes(fromTime, toTime, customer) or [])))
    print("Retrieved {} creditnote(s), total {} EUR".format(
      len(creditnotes), sum([decimal.Decimal(i.total) / 100 for i in creditnotes])))

    creditnote_revenue_items = stripe_datev.creditnotes.create_revenue_item_creditnote(
      creditnotes)

    invoice_guid_dict = {}

    for invoice in invoices:
      finalized_date = datetime.fromtimestamp(
          invoice.status_transitions.finalized_at, timezone.utc
      ).astimezone(stripe_datev.config.accounting_tz)
      creditNo = invoice.number

      invoice_guid_dict[creditNo] = {
        "guid": str(uuid.uuid4()),
        "filename": "{}_{}.pdf".format(finalized_date.strftime("%Y-%m-%d"), creditNo)
      }

    for creditnote in creditnotes:
      finalized_date = datetime.fromtimestamp(
          creditnote.created, timezone.utc
      ).astimezone(stripe_datev.config.accounting_tz)
      creditNo = creditnote["number"]

      invoice_guid_dict[creditNo] = {
        "guid": str(uuid.uuid4()),
        "filename": "{}_{}.pdf".format(finalized_date.strftime("%Y-%m-%d"), creditNo),
        "invoice_number": next(
          rev["number"] for rev in creditnote_revenue_items if rev["id"] == creditnote["id"]
        )
      }

    # charges = list(stripe_datev.charges.listChargesRaw(fromTime, toTime))
    # print("Retrieved {} charge(s), total {} EUR".format(
    #   len(charges), sum([decimal.Decimal(c.amount) / 100 for c in charges])))

    # direct_charges = list(filter(
    #   lambda charge: not stripe_datev.charges.chargeHasInvoice(charge), charges))
    # revenue_items += stripe_datev.charges.createRevenueItems(direct_charges)

    # Balance Transactions

    disputes = list(
      stripe_datev.balance_transactions.list_dispute_chargebacks(fromTime, toTime, customer))
    print("Retrieved {} dispute(s), total {} EUR, fees {} EUR".format(
      len(disputes), sum([decimal.Decimal(c.amount) / 100 for c in disputes]), sum([decimal.Decimal(c.fee) / 100 for c in disputes])))

    pay_refunds = list(
      stripe_datev.balance_transactions.list_payment_refunds(fromTime, toTime, customer))
    print("Retrieved {} pay_refunds(s), total {} EUR, fees {} EUR".format(
      len(pay_refunds), sum([decimal.Decimal(c.amount) / 100 for c in pay_refunds]), sum([decimal.Decimal(c.fee) / 100 for c in pay_refunds])))

    refunds = list(
      stripe_datev.balance_transactions.list_refunds(fromTime, toTime, customer))
    print("Retrieved {} refunds(s), total {} EUR, fees {} EUR".format(
      len(refunds), sum([decimal.Decimal(c.amount) / 100 for c in refunds]), sum([decimal.Decimal(c.fee) / 100 for c in refunds])))

    payments = list(
      stripe_datev.balance_transactions.list_payments(fromTime, toTime, customer))
    print("Retrieved {} payments(s), total {} EUR, fees {} EUR".format(
      len(payments), sum([decimal.Decimal(c.amount) / 100 for c in payments]), sum([decimal.Decimal(c.fee) / 100 for c in payments])))

    chargetrans = list(
      stripe_datev.balance_transactions.list_charges(fromTime, toTime, customer))
    print("Retrieved {} chargetrans(s), total {} EUR, fees {} EUR".format(
      len(chargetrans), sum([decimal.Decimal(c.amount) / 100 for c in chargetrans]), sum([decimal.Decimal(c.fee) / 100 for c in chargetrans])))

    # Write Files

    overview_dir = os.path.join(out_dir_dl, "overview")
    if not os.path.exists(overview_dir):
      os.mkdir(overview_dir)

    with open(os.path.join(overview_dir, "overview-{:04d}-{:02d}.csv".format(year, month)), "w", encoding="utf-8") as fp:
      fp.write(stripe_datev.invoices.to_csv(invoices))
      print("Wrote {} invoices      to {}".format(
        str(len(invoices)).rjust(4, " "), os.path.relpath(fp.name, os.getcwd())))

    monthly_recognition_dir = os.path.join(out_dir_dl, "monthly_recognition")
    if not os.path.exists(monthly_recognition_dir):
      os.mkdir(monthly_recognition_dir)

    with open(os.path.join(monthly_recognition_dir, "monthly_recognition-{}.csv".format(thisMonth)), "w", encoding="utf-8") as fp:
      fp.write(stripe_datev.invoices.to_recognized_month_csv2(revenue_items))
      print("Wrote {} revenue items to {}".format(
        str(len(revenue_items)).rjust(4, " "), os.path.relpath(fp.name, os.getcwd())))

    datevDir = os.path.join(out_dir_dl, 'datev')
    if not os.path.exists(datevDir):
      os.mkdir(datevDir)

    # Datev Revenue

    records = []
    for revenue_item in revenue_items:
      records += stripe_datev.invoices.createAccountingRecords(
        revenue_item)

    for creditnote_rev_item in creditnote_revenue_items:
      records += stripe_datev.creditnotes.create_creditnote_accounting_records(
        creditnote_rev_item)

    records_by_month = {}
    for record in records:
      rev_month = record["date"].strftime("%Y-%m")
      records_by_month[rev_month] = records_by_month.get(
        rev_month, []) + [record]

    for rev_month, records in records_by_month.items():
      if rev_month == thisMonth:
        name = "EXTF_{}_Revenue.csv".format(thisMonth)
      else:
        name = "EXTF_{}_Revenue_From_{}.csv".format(rev_month, thisMonth)
      stripe_datev.output.writeRecords(os.path.join(
        datevDir, name), records, invoice_guid_dict, bezeichung="Stripe Revenue {} from {}".format(rev_month, thisMonth))

    combine_revenue_extf_csvs(out_dir, out_dir_dl, thisMonth)

    # Datev balance transactions

    balance_trans_records = stripe_datev.balance_transactions.create_accounting_records(
      disputes)
    balance_trans_records += stripe_datev.balance_transactions.create_accounting_records(
      pay_refunds)
    balance_trans_records += stripe_datev.balance_transactions.create_accounting_records(
      refunds)
    balance_trans_records += stripe_datev.balance_transactions.create_accounting_records(
      payments)
    balance_trans_records += stripe_datev.balance_transactions.create_accounting_records(
      chargetrans)

    balance_trans_by_month = {}
    for record in balance_trans_records:
      trans_month = record["date"].strftime("%Y-%m")
      balance_trans_by_month[trans_month] = balance_trans_by_month.get(
        trans_month, []) + [record]

    for trans_month, records in balance_trans_by_month.items():
      if trans_month == thisMonth:
        name = "EXTF_{}_Balance_Transactions.csv".format(thisMonth)
      else:
        name = "EXTF_{}_Balance_Transactions_From_{}.csv".format(
          trans_month, thisMonth)
      stripe_datev.output.writeRecords(os.path.join(
        datevDir, name), records, bezeichung="Stripe Charges/Fees {} from {}".format(trans_month, thisMonth))

    # Datev charges

    # charge_records = stripe_datev.charges.createAccountingRecords(charges)

    # charges_by_month = {}
    # for record in charge_records:
    #   month = record["date"].strftime("%Y-%m")
    #   charges_by_month[month] = charges_by_month.get(month, []) + [record]

    # for month, records in charges_by_month.items():
    #   if month == thisMonth:
    #     name = "EXTF_{}_Charges.csv".format(thisMonth)
    #   else:
    #     name = "EXTF_{}_Charges_From_{}.csv".format(month, thisMonth)
    #   stripe_datev.output.writeRecords(os.path.join(
    #     datevDir, name), records, bezeichung="Stripe Charges/Fees {} from {}".format(month, thisMonth))

    # Datev transfers

    transfers = list(stripe_datev.transfers.listTransfersRaw(fromTime, toTime))
    print("Retrieved {} transfer(s), total {} EUR".format(
      len(transfers), sum([decimal.Decimal(c.amount) / 100 for c in transfers])))

    transfer_records = stripe_datev.transfers.createAccountingRecords(
      transfers)
    stripe_datev.output.writeRecords(os.path.join(datevDir, "EXTF_{}_Transfers.csv".format(
      thisMonth)), transfer_records, bezeichung="Stripe Transfers {}".format(thisMonth))

    # Datev payouts

    payoutObjects = list(stripe_datev.payouts.listPayouts(fromTime, toTime))
    print("Retrieved {} payout(s), total {} EUR".format(
      len(payoutObjects), sum([r["amount"] for r in payoutObjects])))

    payout_records = stripe_datev.payouts.createAccountingRecords(
      payoutObjects)
    stripe_datev.output.writeRecords(os.path.join(datevDir, "EXTF_{}_Payouts.csv".format(
      thisMonth)), payout_records, bezeichung="Stripe Payouts {}".format(thisMonth))

    balance_transactions = list(stripe.BalanceTransaction.list(
      created={
        "lt": int(toTime.timestamp()),
        "gte": int(fromTime.timestamp()),
      },
      type="contribution",
    ).auto_paging_iter())
    print("Retrieved {} contribution(s), total {} EUR".format(len(balance_transactions), sum(
      [-decimal.Decimal(b["amount"]) / 100 for b in balance_transactions])))

    contribution_records = stripe_datev.payouts.createAccountingRecordsContributions(
      balance_transactions)
    stripe_datev.output.writeRecords(os.path.join(datevDir, "EXTF_{}_Contributions.csv".format(
      thisMonth)), contribution_records, bezeichung="Stripe Contributions {}".format(thisMonth))

    # PDF

    pdfDir = os.path.join(out_dir_dl, 'pdf')
    if not os.path.exists(pdfDir):
      os.mkdir(pdfDir)

    asyncio.run(save_files.save_files(
      invoices, "invoice_pdf", invoice_guid_dict, pdfDir))
    asyncio.run(save_files.save_files(
      creditnotes, "pdf", invoice_guid_dict, pdfDir))

    keys = list(invoice_guid_dict.keys())
    for i, work_set in enumerate(chunker(keys, 500)):
      create_xml(pdfDir, work_set, i, invoice_guid_dict, year, month)
      zip_compressed_pdfs(os.path.join(out_dir_dl, f"{thisMonth}_XML_compr_{i}.zip"),
                          pdfDir, i, work_set, thisMonth)

    # for charge in charges:
    #   fileName = "{} {}.html".format(datetime.fromtimestamp(
    #     charge.created, timezone.utc).strftime("%Y-%m-%d"), charge.receipt_number or charge.id)
    #   filePath = os.path.join(pdfDir, fileName)
    #   if os.path.exists(filePath):
    #     # print("{} exists, skipping".format(filePath))
    #     continue

    #   pdfLink = charge["receipt_url"]
    #   print("Downloading {} to {}".format(pdfLink, filePath))
    #   r = requests.get(pdfLink)
    #   if r.status_code != 200:
    #     print("HTTP status {}".format(r.status_code))
    #     continue
    #   with open(filePath, "wb") as fp:
    #     fp.write(r.content)

  def validate_customers(self, argv):
    stripe_datev.customer.validate_customers()

  def fill_account_numbers(self, argv):
    stripe_datev.customer.fill_account_numbers()

  def list_accounts(self, argv):
    stripe_datev.customer.list_account_numbers(
      argv[0] if len(argv) > 0 else None)

  def opos(self, argv):
    if len(argv) > 0:
      ref = datetime(*list(map(int, argv))) + \
          timedelta(days=1) - timedelta(seconds=1)
      status = None
    else:
      ref = datetime.now() - timedelta(days=30)
      status = "open"

    print("Unpaid invoices as of", stripe_datev.config.accounting_tz.localize(ref))

    invoices = stripe.Invoice.list(
      created={
        "lte": int(ref.timestamp()),
        # "gte": int((ref - datedelta.YEAR).timestamp()),
      },
      status=status,
      expand=["data.customer"]
    ).auto_paging_iter()

    totals = []
    for invoice in invoices:
      finalized_at = invoice.status_transitions.get("finalized_at", None)
      if finalized_at is None or datetime.utcfromtimestamp(finalized_at) > ref:
        continue
      marked_uncollectible_at = invoice.status_transitions.get(
        "marked_uncollectible_at", None)
      if marked_uncollectible_at is not None and datetime.utcfromtimestamp(marked_uncollectible_at) <= ref:
        continue
      voided_at = invoice.status_transitions.get("voided_at", None)
      if voided_at is not None and datetime.utcfromtimestamp(voided_at) <= ref:
        continue
      paid_at = invoice.status_transitions.get("paid_at", None)
      if paid_at is not None and datetime.utcfromtimestamp(paid_at) <= ref:
        continue

      customer = stripe_datev.customer.retrieveCustomer(invoice.customer)
      due_date = datetime.utcfromtimestamp(
        invoice.due_date if invoice.due_date else invoice.created)
      total = decimal.Decimal(invoice.total) / 100
      totals.append(total)
      print(invoice.number.ljust(13, " "), format(total, ",.2f").rjust(10, " "), "EUR", customer.email.ljust(
        35, " "), "due", due_date.date(), "({} overdue)".format(ref - due_date) if due_date < ref else "")

    total = reduce(lambda x, y: x + y, totals, decimal.Decimal(0))
    print("TOTAL        ", format(total, ",.2f").rjust(10, " "), "EUR")


if __name__ == '__main__':
  StripeDatevCli().run(sys.argv)
