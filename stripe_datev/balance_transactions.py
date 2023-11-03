import stripe
import decimal
from datetime import datetime, timezone
from . import customer, dateparser, output, config, invoices


def list_dispute_chargebacks(fromTime: datetime, toTime: datetime, customer=None):
  disputes = stripe.BalanceTransaction.list(
    created={
      "gte": int(fromTime.timestamp()),
      "lt": int(toTime.timestamp())
    },
    type="adjustment",
    expand=["data.source", "data.source.charge"],
  ).auto_paging_iter()
  for trans in disputes:
    if trans.source == None and trans.reporting_category == "other_adjustment":
      continue
    charge = trans.source if trans.source.object == "charge" else trans.source.charge
    if customer is not None and charge.customer != customer:
      continue
    yield trans


def list_payment_refunds(fromTime: datetime, toTime: datetime, customer=None):
  disputes = stripe.BalanceTransaction.list(
    created={
      "gte": int(fromTime.timestamp()),
      "lt": int(toTime.timestamp())
    },
    type="payment_refund",
    expand=["data.source", "data.source.charge"],
  ).auto_paging_iter()
  for trans in disputes:
    charge = trans.source if trans.source.object == "charge" else trans.source.charge
    if customer is not None and charge.customer != customer:
      continue
    yield trans


def list_refunds(fromTime: datetime, toTime: datetime, customer=None):
  disputes = stripe.BalanceTransaction.list(
    created={
      "gte": int(fromTime.timestamp()),
      "lt": int(toTime.timestamp())
    },
    type="refund",
    expand=["data.source", "data.source.charge"],
  ).auto_paging_iter()
  for trans in disputes:
    charge = trans.source if trans.source.object == "charge" else trans.source.charge
    if customer is not None and charge.customer != customer:
      continue
    yield trans


def list_payments(fromTime: datetime, toTime: datetime, customer=None):
  disputes = stripe.BalanceTransaction.list(
    created={
      "gte": int(fromTime.timestamp()),
      "lt": int(toTime.timestamp())
    },
    type="payment",
    expand=["data.source", "data.source.charge"],
  ).auto_paging_iter()
  for trans in disputes:
    charge = trans.source if trans.source.object == "charge" else trans.source.charge
    if customer is not None and charge.customer != customer:
      continue
    yield trans


def list_charges(fromTime: datetime, toTime: datetime, customer=None):
  disputes = stripe.BalanceTransaction.list(
    created={
      "gte": int(fromTime.timestamp()),
      "lt": int(toTime.timestamp())
    },
    type="charge",
    expand=["data.source", "data.source.charge"],
  ).auto_paging_iter()
  for trans in disputes:
    charge = trans.source if trans.source.object == "charge" else trans.source.charge
    if customer is not None and charge.customer != customer:
      continue
    yield trans


def find_all_with_fees(fromTime: datetime, toTime: datetime, customer=None):
  disputes = stripe.BalanceTransaction.list(
    created={
      "gte": int(fromTime.timestamp()),
      "lt": int(toTime.timestamp())
    },
    expand=["data.source", "data.source.charge"],
    # type="charge",
  ).auto_paging_iter()
  for trans in disputes:
    charge = trans.source if trans.source.object == "charge" else trans.source.charge
    if customer is not None and charge.customer != customer:
      continue
    yield trans


def create_accounting_records(balance_trans: list):
  records = []

  for trans in balance_trans:
    charge = trans.source if trans.source.object == "charge" else trans.source.charge

    acc_props = customer.getAccountingProps(
      customer.retrieveCustomer(charge.customer))
    created = datetime.fromtimestamp(
      trans.created, timezone.utc).astimezone(config.accounting_tz)

    assert trans.currency == "eur"

    invoice_id = charge.invoice
    if invoice_id:
      invoice = invoices.retrieveInvoice(invoice_id)
      number = invoice.number
    else:
      number = charge.receipt_number

    records.append({
      "date": created,
      "Umsatz (ohne Soll/Haben-Kz)": output.formatDecimal(decimal.Decimal(trans.amount) / 100),
      "Soll/Haben-Kennzeichen": "S",
      "WKZ Umsatz": "EUR",
      "Konto": config.stripe_transit_account,
      "Gegenkonto (ohne BU-Schlüssel)": acc_props["customer_account"],
      "Buchungstext": "Stripe Payment ({})".format(trans.id),
      "Belegfeld 1": number,
    })

    fee_amount = decimal.Decimal(trans.fee) / 100
    if fee_amount != decimal.Decimal(0):
      fee_desc = trans.fee_details[0].description
      records.append({
        "date": created,
        "Umsatz (ohne Soll/Haben-Kz)": output.formatDecimal(fee_amount),
        "Soll/Haben-Kennzeichen": "S",
        "WKZ Umsatz": "EUR",
        "Konto": config.stripe_fees_account,
        "Gegenkonto (ohne BU-Schlüssel)": config.stripe_transit_account,
        "BU-Schlüssel": config.stripe_fees_datev_tax_key,
        "Buchungstext": "{} ({})".format(fee_desc or "Stripe Fee", trans.id),
      })

  return records
