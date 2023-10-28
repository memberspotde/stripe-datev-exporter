import asyncio
from math import ceil
import os
import aiohttp
import aiofiles


async def save_invoices(invoices, invoice_guid_dict, pdfDir):
  parallel = 50
  runs = ceil(len(invoices) / parallel)
  print("save_invoices: runs: {}, length: {}".format(runs, len(invoices)))
  for run in range(runs):
    start = run * parallel
    end = (run + 1) * parallel
    print("save_invoices: run: {} start: {} end: {}".format(run, start, end))
    await asyncio.gather(*[save_invoice(invoice, invoice_guid_dict, pdfDir) for invoice in invoices[run * parallel: (run + 1) * parallel]])


async def save_invoice(invoice, invoice_guid_dict, pdfDir):
  async with aiohttp.ClientSession() as session:
    pdfLink = invoice.invoice_pdf
    invNo = invoice.number

    fileName = invoice_guid_dict.get(invNo)["filename"]
    filePath = os.path.join(pdfDir, fileName)
    if os.path.exists(filePath):
      return

    async with session.get(pdfLink) as r:
      if r.status != 200:
        print("HTTP status {}".format(r.status))
        return

      f = await aiofiles.open(filePath, mode='wb')
      await f.write(await r.read())
      await f.close()


async def save_creditnotes(invoices, invoice_guid_dict, pdfDir):
  async with aiohttp.ClientSession() as session:
    for invoice in invoices:
      pdfLink = invoice.invoice_pdf
      invNo = invoice.number

      fileName = invoice_guid_dict.get(invNo)["filename"]
      filePath = os.path.join(pdfDir, fileName)
      if os.path.exists(filePath):
        # print("{} exists, skipping".format(filePath))
        continue

      print("Downloading {} to {}".format(pdfLink, filePath))
      async with session.get(pdfLink) as r:
        # r = requests.get(pdfLink)
        r.status
        if r.status != 200:
          print("HTTP status {}".format(r.status))
          continue
        with open(filePath, "wb") as fp:
          fp.write(r.content)
