import json
from stripe_datev import csv_export, recognition
import stripe
import decimal
import math
from datetime import datetime, timedelta, timezone

from stripe_datev.helpers.invoicehelpers import get_revenue_line_item, op_switcher
from stripe_datev.utils.print import print_json
from . import customer, output, dateparser, config
import datedelta

invoices_cached = {}


def listFinalizedInvoices(fromTime, toTime, customer=None):
  # return []

  invoices = stripe.Invoice.list(
    created={
      "gte": int(fromTime.timestamp()),
      "lt": int(toTime.timestamp())
    },
    customer=customer,
    # due_date={
    #     "gte": int(fromTime.timestamp()),
    # },
    expand=["data.customer", "data.customer.tax_ids"]
  ).auto_paging_iter()

  for invoice in invoices:
    if invoice.status == "draft":
      continue
    # finalized_date = datetime.fromtimestamp(
    #   invoice.status_transitions.finalized_at, timezone.utc).astimezone(config.accounting_tz)
    # if finalized_date < fromTime or finalized_date >= toTime:
    #   # print("Skipping invoice {}, created {} finalized {} due {}".format(invoice.id, created_date, finalized_date, due_date))
    #   continue
    invoices_cached[invoice.id] = invoice
    yield invoice


def retrieveInvoice(id):
  if isinstance(id, str):
    if id in invoices_cached:
      return invoices_cached[id]
    invoice = stripe.Invoice.retrieve(
      id, expand=["customer", "customer.tax_ids"])
    invoices_cached[invoice.id] = invoice
    return invoice
  elif isinstance(id, stripe.Invoice):
    invoices_cached[id.id] = id
    return id
  else:
    raise Exception("Unexpected retrieveInvoice() argument: {}".format(id))


tax_rates_cached = {}


def retrieveTaxRate(id):
  if id in tax_rates_cached:
    return tax_rates_cached[id]
  tax_rate = stripe.TaxRate.retrieve(id)
  tax_rates_cached[id] = tax_rate
  return tax_rate


def createRevenueItems(invs):
  revenue_items = []

  for invoice in invs:
    if invoice["metadata"].get("stripe-datev-exporter:ignore", "false") == "true":
      print("Skipping invoice {} (ignore)".format(invoice.id))
      continue

    voided_at = None
    marked_uncollectible_at = None
    if invoice.status == "void":
      voided_at = datetime.fromtimestamp(
        invoice.status_transitions.voided_at, timezone.utc).astimezone(config.accounting_tz)
    elif invoice.status == "uncollectible":
      marked_uncollectible_at = datetime.fromtimestamp(
        invoice.status_transitions.marked_uncollectible_at, timezone.utc).astimezone(config.accounting_tz)

    credited_at = None
    credited_amount = None
    # if invoice.post_payment_credit_notes_amount > 0 or invoice.pre_payment_credit_notes_amount > 0:
    #   cns = stripe.CreditNote.list(invoice=invoice.id).data
    #   assert len(cns) == 1
    #   credited_at = datetime.fromtimestamp(
    #     cns[0].created, timezone.utc).astimezone(config.accounting_tz)
    #   amount = 0
    #   if invoice.post_payment_credit_notes_amount > 0:
    #     amount += invoice.post_payment_credit_notes_amount
    #   if invoice.pre_payment_credit_notes_amount > 0:
    #     amount += invoice.pre_payment_credit_notes_amount
    #   credited_amount = decimal.Decimal(amount) / 100

    line_items = []

    cus = customer.retrieveCustomer(invoice.customer)
    accounting_props = customer.getAccountingProps(cus, invoice=invoice)
    amount_with_tax = decimal.Decimal(invoice.total) / 100
    amount_net = amount_with_tax
    if invoice.tax:
      amount_net -= decimal.Decimal(invoice.tax) / 100

    tax_percentage = None
    if len(invoice.total_tax_amounts) > 0:
      rate = retrieveTaxRate(invoice.total_tax_amounts[0]["tax_rate"])
      tax_percentage = decimal.Decimal(rate["percentage"])

    finalized_date = datetime.fromtimestamp(
      invoice.status_transitions.finalized_at, timezone.utc).astimezone(config.accounting_tz)

    is_subscription = invoice.get("subscription", None) is not None

    if invoice.lines.has_more or any(len(li.get("discounts", [])) > 0 for li in invoice.lines):
      lines = invoice.lines.list(expand=["data.discounts"]).auto_paging_iter()
    else:
      lines = invoice.lines

    for line_item_idx, line_item in enumerate(lines):
      line_items.append(get_revenue_line_item(
        invoice, line_item, line_item_idx))

    revenue_items.append({
      "id": invoice.id,
      "number": invoice.number,
      "created": finalized_date,
      "amount_net": amount_net,
      "accounting_props": accounting_props,
      "customer": cus,
      "amount_with_tax": amount_with_tax,
      "tax_percentage": tax_percentage,
      "text": "Invoice {}".format(invoice.number),
      "voided_at": voided_at,
      "credited_at": credited_at,
      "credited_amount": credited_amount,
      "marked_uncollectible_at": marked_uncollectible_at,
      "line_items": line_items,
      "is_subscription": is_subscription,
    })

  return revenue_items


def createAccountingRecords(revenue_item):
  created = revenue_item["created"]
  amount_with_tax = revenue_item["amount_with_tax"]
  accounting_props = revenue_item["accounting_props"]
  line_items = revenue_item["line_items"]
  text = revenue_item["text"]
  voided_at = revenue_item.get("voided_at", None)
  credited_at = revenue_item.get("credited_at", None)
  credited_amount = revenue_item.get("credited_amount", None)
  marked_uncollectible_at = revenue_item.get("marked_uncollectible_at", None)
  number = revenue_item["number"]
  eu_vat_id = accounting_props["vat_id"] or ""

  if accounting_props["tax_exempt"] == "none" and accounting_props["country"] != "DE":
    eu_vat_id = accounting_props["country"] or ""

  records = []

  if amount_with_tax == 0 and config.book_0_invoices:
    for key in ["S", "H"]:
      records.append({
        "date": created,
        "Umsatz (ohne Soll/Haben-Kz)": output.formatDecimal(0.01),
        "Soll/Haben-Kennzeichen": key,
        "WKZ Umsatz": "EUR",
        "Konto": accounting_props["customer_account"],
        "Gegenkonto (ohne BU-Schlüssel)": accounting_props["revenue_account"],
        "BU-Schlüssel": accounting_props["datev_tax_key"],
        "Buchungstext": text,
        "Belegfeld 1": number,
        "EU-Land u. UStID": eu_vat_id,
      })
    return records

  if amount_with_tax != 0:
    records.append({
      "date": created,
      "Umsatz (ohne Soll/Haben-Kz)": output.formatDecimal(abs(amount_with_tax)),
      "Soll/Haben-Kennzeichen": op_switcher("S", amount_with_tax),
      "WKZ Umsatz": "EUR",
      "Konto": accounting_props["customer_account"],
      "Gegenkonto (ohne BU-Schlüssel)": accounting_props["revenue_account"],
      "BU-Schlüssel": accounting_props["datev_tax_key"],
      "Buchungstext": text,
      "Belegfeld 1": number,
      "EU-Land u. UStID": eu_vat_id,
    })

    if voided_at is not None:
      print("Voided", text, "Created", created, 'Voided', voided_at)
      records.append({
        "date": voided_at,
        "Umsatz (ohne Soll/Haben-Kz)": output.formatDecimal(abs(amount_with_tax)),
        "Soll/Haben-Kennzeichen": op_switcher("H", amount_with_tax),
        "WKZ Umsatz": "EUR",
        "Konto": accounting_props["customer_account"],
        "Gegenkonto (ohne BU-Schlüssel)": accounting_props["revenue_account"],
        "BU-Schlüssel": accounting_props["datev_tax_key"],
        "Buchungstext": "Storno {}".format(text),
        "Belegfeld 1": number,
        "EU-Land u. UStID": eu_vat_id,
      })

    elif marked_uncollectible_at is not None:
      print("Uncollectible", text, "Created", created,
            'Marked uncollectible', marked_uncollectible_at)
      records.append({
        "date": marked_uncollectible_at,
        "Umsatz (ohne Soll/Haben-Kz)": output.formatDecimal(amount_with_tax),
        "Soll/Haben-Kennzeichen": "H",
        "WKZ Umsatz": "EUR",
        "Konto": accounting_props["customer_account"],
        "Gegenkonto (ohne BU-Schlüssel)": accounting_props["revenue_account"],
        "BU-Schlüssel": accounting_props["datev_tax_key"],
        "Buchungstext": "Storno {}".format(text),
        "Belegfeld 1": number,
        "EU-Land u. UStID": eu_vat_id,
      })

    elif credited_at is not None:
      print("Refunded", text, "Created", created, 'Refunded', credited_at)
      records.append({
        "date": credited_at,
        "Umsatz (ohne Soll/Haben-Kz)": output.formatDecimal(credited_amount),
        "Soll/Haben-Kennzeichen": "H",
        "WKZ Umsatz": "EUR",
        "Konto": accounting_props["customer_account"],
        "Gegenkonto (ohne BU-Schlüssel)": accounting_props["revenue_account"],
        "BU-Schlüssel": accounting_props["datev_tax_key"],
        "Buchungstext": "Erstattung {}".format(text),
        "Belegfeld 1": number,
        "EU-Land u. UStID": eu_vat_id,
      })

  # If invoice was voided, marked uncollectible or credited fully in same month,
  # don't bother with pRAP
  if voided_at is not None and voided_at.strftime("%Y-%m") == created.strftime("%Y-%m") or \
          marked_uncollectible_at is not None and marked_uncollectible_at.strftime("%Y-%m") == created.strftime("%Y-%m") or \
          credited_at is not None and credited_at.strftime("%Y-%m") == created.strftime("%Y-%m") and credited_amount == amount_with_tax:
    return records

  for line_item in line_items:
    amount_net = line_item["amount_net"]
    recognition_start = line_item["recognition_start"]
    recognition_end = line_item["recognition_end"]
    text = line_item["text"]

    months = recognition.split_months(
      recognition_start, recognition_end, [amount_net])

    base_months = list(filter(lambda month: month["start"] <= created, months))
    base_amount = sum(map(lambda month: month["amounts"][0], base_months))

    forward_amount = amount_net - base_amount

    forward_months = list(
      filter(lambda month: month["start"] > created, months))

    if len(forward_months) > 0 and forward_amount != 0:
      records.append({
        "date": created,
        "Umsatz (ohne Soll/Haben-Kz)": output.formatDecimal(abs(forward_amount)),
        "Soll/Haben-Kennzeichen": op_switcher("S", forward_amount),
        "WKZ Umsatz": "EUR",
        "Konto": accounting_props["revenue_account"],
        "Gegenkonto (ohne BU-Schlüssel)": config.account_prap,
        "BU-Schlüssel": accounting_props["prap_datev_tax_key"],
        "Buchungstext": "pRAP nach {} / {}".format("{}..{}".format(forward_months[0]["start"].strftime("%Y-%m"), forward_months[-1]["start"].strftime("%Y-%m")) if len(forward_months) > 1 else forward_months[0]["start"].strftime("%Y-%m"), text),
        "Belegfeld 1": number,
        "EU-Land u. UStID": eu_vat_id,
      })

      for month in forward_months:
        records.append({
          # If invoice was voided/etc., resolve all pRAP in that month, don't keep going into the future
          "date": voided_at or marked_uncollectible_at or credited_at or month["start"],
          "Umsatz (ohne Soll/Haben-Kz)": output.formatDecimal(abs(month["amounts"][0])),
          "Soll/Haben-Kennzeichen": op_switcher("S", month["amounts"][0]),
          "WKZ Umsatz": "EUR",
          "Konto": config.account_prap,
          "Gegenkonto (ohne BU-Schlüssel)": accounting_props["revenue_account"],
          "BU-Schlüssel": accounting_props["prap_datev_tax_key"],
          "Buchungstext": "pRAP aus {} / {}".format(created.strftime("%Y-%m"), text),
          "Belegfeld 1": number,
          "EU-Land u. UStID": eu_vat_id,
        })

  return records


def to_csv(inv):
  lines = [[
    "invoice_id",
    "invoice_number",
    "date",

    "total_before_tax",
    "tax",
    "tax_percent",
    "total",

    "customer_id",
    "customer_name",
    "country",
    "vat_region",
    "vat_id",
    "tax_exempt",

    "customer_account",
    "revenue_account",
    "datev_tax_key",
  ]]
  for invoice in inv:
    if invoice.status == "void":
      continue
    cus = customer.retrieveCustomer(invoice.customer)
    props = customer.getAccountingProps(cus, invoice=invoice)

    total = decimal.Decimal(invoice.total) / 100
    tax = decimal.Decimal(invoice.tax) / 100 if invoice.tax else None
    total_before_tax = total
    if tax is not None:
      total_before_tax -= tax

    lines.append([
      invoice.id,
      invoice.number,
      datetime.fromtimestamp(invoice.status_transitions.finalized_at, timezone.utc).astimezone(
        config.accounting_tz).strftime("%Y-%m-%d"),

      format(total_before_tax, ".2f"),
      format(tax, ".2f") if tax else None,
      format(decimal.Decimal(invoice.tax_percent),
             ".0f") if "tax_percent" in invoice and invoice.tax_percent else None,
      format(total, ".2f"),

      cus.id,
      customer.getCustomerName(cus),
      props["country"],
      props["vat_region"],
      props["vat_id"],
      props["tax_exempt"],

      props["customer_account"],
      props["revenue_account"],
      props["datev_tax_key"],
    ])

  return csv_export.lines_to_csv(lines)


def to_recognized_month_csv2(revenue_items):
  lines = [[
    "invoice_id",
    "invoice_number",
    "invoice_date",
    "recognition_start",
    "recognition_end",
    "recognition_month",

    "line_item_idx",
    "line_item_desc",
    "line_item_net",

    "customer_id",
    "customer_name",
    "country",

    "accounting_date",
    "revenue_type",
    "is_recurring",
  ]]

  for revenue_item in revenue_items:
    amount_with_tax = revenue_item.get("amount_with_tax")
    voided_at = revenue_item.get("voided_at", None)
    credited_at = revenue_item.get("credited_at", None)
    credited_amount = revenue_item.get("credited_amount", None)
    marked_uncollectible_at = revenue_item.get("marked_uncollectible_at", None)

    last_line_item_recognition_end = max(
      (line_item["recognition_end"] for line_item in revenue_item["line_items"]), default=None)
    if last_line_item_recognition_end is not None and revenue_item["created"] + timedelta(days=1) < last_line_item_recognition_end:
      revenue_type = "Prepaid"
    else:
      revenue_type = "PayPerUse"
    is_recurring = revenue_item.get("is_subscription", False)

    for line_item in revenue_item["line_items"]:
      end = voided_at or marked_uncollectible_at or credited_at or line_item["recognition_end"]
      for month in recognition.split_months(line_item["recognition_start"], line_item["recognition_end"], [line_item["amount_net"]]):
        accounting_date = max(
          revenue_item["created"], end if end < month["start"] else month["start"])

        lines.append([
          revenue_item["id"],
          revenue_item.get("number", ""),
          revenue_item["created"].strftime("%Y-%m-%d"),
          line_item["recognition_start"].strftime("%Y-%m-%d"),
          line_item["recognition_end"].strftime("%Y-%m-%d"),
          month["start"].strftime("%Y-%m") + "-01",

          str(line_item.get("line_item_idx", 0) + 1),
          line_item["text"],
          format(month["amounts"][0], ".2f"),

          revenue_item["customer"]["id"],
          customer.getCustomerName(revenue_item["customer"]),
          revenue_item["customer"].get("address", {}).get("country", ""),

          accounting_date.strftime("%Y-%m-%d"),
          revenue_type,
          "true" if is_recurring else "false",
        ])

        if voided_at is not None:
          reverse = lines[-1].copy()
          reverse[8] = format(month["amounts"][0] * -1, ".2f")
          reverse[12] = max(revenue_item["created"], end if end <
                            month["end"] else month["start"]).strftime("%Y-%m-%d")
          lines.append(reverse)

        elif marked_uncollectible_at is not None:
          reverse = lines[-1].copy()
          reverse[8] = format(month["amounts"][0] * -1, ".2f")
          reverse[12] = max(revenue_item["created"], end if end <
                            month["end"] else month["start"]).strftime("%Y-%m-%d")
          lines.append(reverse)

        elif credited_at is not None:
          reverse = lines[-1].copy()
          reverse[8] = format(month["amounts"][0] * -1 *
                              (credited_amount / amount_with_tax), ".2f")
          reverse[12] = max(revenue_item["created"], end if end <
                            month["end"] else month["start"]).strftime("%Y-%m-%d")
          lines.append(reverse)

  return csv_export.lines_to_csv(lines)


def roundCentsDown(dec):
  return math.floor(dec * 100) / 100


def accrualRecords(invoiceDate, invoiceAmount, customerAccount, revenueAccount, text, firstRevenueDate, revenueSpreadMonths, includeOriginalInvoice=True):
  records = []

  if includeOriginalInvoice:
    records.append({
      "date": invoiceDate,
      "Umsatz (ohne Soll/Haben-Kz)": output.formatDecimal(invoiceAmount),
      "Soll/Haben-Kennzeichen": "S",
      "WKZ Umsatz": "EUR",
      "Konto": str(customerAccount),
      "Gegenkonto (ohne BU-Schlüssel)": str(revenueAccount),
      "Buchungstext": text,
    })

  revenuePerPeriod = roundCentsDown(invoiceAmount / revenueSpreadMonths)
  if invoiceDate < firstRevenueDate:
    accrueAmount = invoiceAmount
    accrueText = "{} / Rueckstellung ({} Monate)".format(text,
                                                         revenueSpreadMonths)
    periodsBooked = 0
    periodDate = firstRevenueDate
  else:
    accrueAmount = invoiceAmount - revenuePerPeriod
    accrueText = "{} / Rueckstellung Anteilig ({}/{} Monate)".format(
      text, revenueSpreadMonths - 1, revenueSpreadMonths)
    periodsBooked = 1
    periodDate = firstRevenueDate + datedelta.MONTH

  records.append({
    "date": invoiceDate,
    "Umsatz (ohne Soll/Haben-Kz)": output.formatDecimal(accrueAmount),
    "Soll/Haben-Kennzeichen": "S",
    "WKZ Umsatz": "EUR",
    "Konto": str(revenueAccount),
    "Gegenkonto (ohne BU-Schlüssel)": config.account_prap,
    "Buchungstext": accrueText,
  })

  remainingAmount = accrueAmount

  while periodsBooked < revenueSpreadMonths:
    if periodsBooked < revenueSpreadMonths - 1:
      periodAmount = revenuePerPeriod
    else:
      periodAmount = remainingAmount

    records.append({
      "date": periodDate,
      "Umsatz (ohne Soll/Haben-Kz)": output.formatDecimal(periodAmount),
      "Soll/Haben-Kennzeichen": "S",
      "WKZ Umsatz": "EUR",
      "Konto": config.account_prap,
      "Gegenkonto (ohne BU-Schlüssel)": str(revenueAccount),
      "Buchungstext": "{} / Aufloesung Rueckstellung Monat {}/{}".format(text, periodsBooked + 1, revenueSpreadMonths),
    })

    periodDate = periodDate + datedelta.MONTH
    periodsBooked += 1
    remainingAmount -= periodAmount

  return records
