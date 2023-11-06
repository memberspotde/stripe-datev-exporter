

from datetime import datetime, timezone
import decimal

import stripe

from stripe_datev import config, dateparser


def op_switcher(op: str, amount: decimal.Decimal):
  if (op != "S" and op != "H"):
    raise Exception("Invalid OP")
  if op == "S":
    return "S" if amount >= 0 else "H"
  if op == "H":
    return "H" if amount >= 0 else "S"


def get_invoice_recognition_range(invoice: stripe.Invoice):
  if invoice.lines.has_more or any(len(li.get("discounts", [])) > 0 for li in invoice.lines):
    lines = invoice.lines.list(expand=["data.discounts"]).auto_paging_iter()
  else:
    lines = invoice.lines

  start = None
  end = None
  for line_item_idx, line_item in enumerate(lines):

    created = datetime.fromtimestamp(invoice.created, timezone.utc)

    if "period" in line_item:
      start = datetime.fromtimestamp(
        line_item["period"]["start"], timezone.utc)
      end = datetime.fromtimestamp(line_item["period"]["end"], timezone.utc)
      break
    if start == end:
      start = None
      end = None
      break

    if start is None and end is None:
      try:
        date_range = dateparser.find_date_range(line_item.get(
          "description"), created, tz=config.accounting_tz)
        if date_range is not None:
          start, end = date_range

      except Exception as ex:
        print(ex)
        pass

    if start is None and end is None:
      print("Warning: unknown period for line item --",
            invoice.id, line_item.get("description"))
      start = created
      end = created

  return start.astimezone(config.accounting_tz), end.astimezone(config.accounting_tz)


def get_line_item_recognition_range(line_item, invoice):
  created = datetime.fromtimestamp(invoice["created"], timezone.utc)

  start = None
  end = None
  if "period" in line_item:
    start = datetime.fromtimestamp(line_item["period"]["start"], timezone.utc)
    end = datetime.fromtimestamp(line_item["period"]["end"], timezone.utc)
  if start == end:
    start = None
    end = None

  if start is None and end is None:
    try:
      date_range = dateparser.find_date_range(line_item.get(
        "description"), created, tz=config.accounting_tz)
      if date_range is not None:
        start, end = date_range

    except Exception as ex:
      print(ex)
      pass

  if start is None and end is None:
    print("Warning: unknown period for line item --",
          invoice["id"], line_item.get("description"))
    start = created
    end = created

  return start.astimezone(config.accounting_tz), end.astimezone(config.accounting_tz)


def get_line_item_amounts(line_item):
  li_amount_net = None
  li_total = None

  if len(line_item["tax_amounts"]) > 0:
    assert len(line_item["tax_amounts"]) == 1
    line_item_tax = line_item["tax_amounts"][0]
    if line_item_tax["inclusive"]:
      raise Exception("Inclusive tax not supported")
    else:
      li_amount_net = line_item_tax["taxable_amount"]
      li_total = li_amount_net + line_item_tax["amount"]

  # In other cases there is no taxes on the invoice
  elif len(line_item["discount_amounts"]) > 0:
    discount_sum = sum(discount["amount"]
                       for discount in line_item["discount_amounts"])
    li_amount_net = line_item["amount"] - discount_sum
    li_total = li_amount_net
  else:
    li_amount_net = line_item["amount"]
    li_total = li_amount_net

  return decimal.Decimal(li_amount_net) / 100, decimal.Decimal(li_total) / 100


def get_revenue_line_item(invoice, line_item, line_item_idx):
  text = "Invoice {} / {}".format(invoice.number,
                                  line_item.get("description", ""))
  start, end = get_line_item_recognition_range(line_item, invoice)

  li_amount_net, li_total = get_line_item_amounts(line_item)

  return {
      "line_item_idx": line_item_idx,
      "recognition_start": start,
      "recognition_end": end,
      "amount_net": li_amount_net,
      "text": text,
      "amount_with_tax": li_total
  }


def get_creditnote_revenue_line_item(creditnote, invoice, line_item, line_item_idx):
  text = "Creditnote {} / Invoice {} / {}".format(
    creditnote["number"],
    invoice["number"],
    line_item.get("description", "")
  )

  invoice_line_item = next(
    (li for li in invoice["lines"]["data"] if li["id"] == line_item.get("invoice_line_item", "")), None)

  start, end = get_line_item_recognition_range(
    invoice_line_item or line_item, creditnote)

  li_amount_net, li_total = get_line_item_amounts(line_item)

  return {
      "line_item_idx": line_item_idx,
      "recognition_start": start,
      "recognition_end": end,
      "amount_net": li_amount_net,
      "text": text,
      "amount_with_tax": li_total
  }
