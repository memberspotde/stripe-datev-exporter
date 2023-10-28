import json

from stripe_datev.helpers.invoicehelpers import get_creditnote_revenue_line_item, get_invoice_recognition_range, get_line_item_recognition_range, get_revenue_line_item
from stripe_datev import recognition, csv
import stripe
import decimal
import math
from datetime import datetime, timedelta, timezone
from . import customer, output, dateparser, config
import datedelta


def list_creditnotes(from_time: datetime, to_time: datetime):
  all_creditnotes = stripe.CreditNote.list(
    # customer="cus_NHytio7HhdSVRq",
  ).auto_paging_iter()
  creditnotes = []

  for creditnote in all_creditnotes:
    created = datetime.fromtimestamp(
      creditnote.created).astimezone(config.accounting_tz)
    if created > to_time:
      continue
    if created < from_time:
      break
    creditnotes.append(creditnote)

  return creditnotes


def create_revenue_item_creditnote(creditnotes):
  revenue_items = []
  for creditnote in creditnotes:
    invoice = stripe.Invoice.retrieve(creditnote["invoice"])

    line_items = []

    cus = customer.retrieveCustomer(invoice["customer"])
    accounting_props = customer.getAccountingProps(cus, invoice=invoice)
    amount_with_tax = decimal.Decimal(creditnote["total"]) / 100
    amount_net = decimal.Decimal(creditnote["total_excluding_tax"]) / 100
    amount_net = amount_with_tax

    finalized_date = datetime.fromtimestamp(
      creditnote["created"], timezone.utc).astimezone(config.accounting_tz)

    for line_item_idx, line_item in enumerate(creditnote["lines"]["data"]):
      line_items.append(get_creditnote_revenue_line_item(
        creditnote, invoice, line_item, line_item_idx))

    revenue_items.append({
      "id": creditnote.id,
      "number": invoice.number,
      "created": finalized_date,
      "amount_net": amount_net,
      "accounting_props": accounting_props,
      "customer": cus,
      "amount_with_tax": amount_with_tax,
      "text": "Creditnote {}".format(creditnote.number),
      "line_items": line_items,
    })

  return revenue_items


def create_creditnote_accounting_records(revenue_item):
  created = revenue_item["created"]
  amount_with_tax = revenue_item["amount_with_tax"]
  accounting_props = revenue_item["accounting_props"]
  line_items = revenue_item["line_items"]
  text = revenue_item["text"]
  number = revenue_item["number"]
  eu_vat_id = accounting_props["vat_id"] or ""

  if accounting_props["tax_exempt"] == "none" and accounting_props["country"] != "DE":
    eu_vat_id = accounting_props["country"] or ""

  records = []

  records.append({
    "date": created,
    "Umsatz (ohne Soll/Haben-Kz)": output.formatDecimal(amount_with_tax),
    "Soll/Haben-Kennzeichen": "H",
    "WKZ Umsatz": "EUR",
    "Konto": accounting_props["customer_account"],
    "Gegenkonto (ohne BU-Schlüssel)": accounting_props["revenue_account"],
    "BU-Schlüssel": accounting_props["datev_tax_key"],
    "Buchungstext": "Erstattung {}".format(text),
    "Belegfeld 1": number,
    "EU-Land u. UStID": eu_vat_id,
  })

  for line_item in line_items:
    amount_with_tax = line_item["amount_with_tax"]
    recognition_start = line_item["recognition_start"]
    recognition_end = line_item["recognition_end"]
    text = line_item["text"]

    months = recognition.split_months(
      recognition_start, recognition_end, [amount_with_tax])

    base_months = list(filter(lambda month: month["start"] <= created, months))
    base_amount = sum(map(lambda month: month["amounts"][0], base_months))

    forward_amount = amount_with_tax - base_amount

    forward_months = list(
      filter(lambda month: month["start"] > created, months))

    if len(forward_months) > 0 and forward_amount != 0:
      records.append({
        "date": created,
        "Umsatz (ohne Soll/Haben-Kz)": output.formatDecimal(forward_amount),
        "Soll/Haben-Kennzeichen": "H",
        "WKZ Umsatz": "EUR",
        "Konto": accounting_props["revenue_account"],
        "Gegenkonto (ohne BU-Schlüssel)": config.account_prap,
        "Buchungstext": "pRAP nach {} / {}".format("{}..{}".format(forward_months[0]["start"].strftime("%Y-%m"), forward_months[-1]["start"].strftime("%Y-%m")) if len(forward_months) > 1 else forward_months[0]["start"].strftime("%Y-%m"), text),
        "Belegfeld 1": number,
        "EU-Land u. UStID": eu_vat_id,
      })

    for month in forward_months:
      records.append({
        "date": month["start"],
        "Umsatz (ohne Soll/Haben-Kz)": output.formatDecimal(month["amounts"][0]),
        "Soll/Haben-Kennzeichen": "H",
        "WKZ Umsatz": "EUR",
        "Konto": config.account_prap,
        "Gegenkonto (ohne BU-Schlüssel)": accounting_props["revenue_account"],
        "Buchungstext": "pRAP aus {} / {}".format(created.strftime("%Y-%m"), text),
        "Belegfeld 1": number,
        "EU-Land u. UStID": eu_vat_id,
      })

  return records
