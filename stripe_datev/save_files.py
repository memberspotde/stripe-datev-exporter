import asyncio
from math import ceil
import os
import aiohttp
import aiofiles

parallel = 50


async def save_files(inv_or_credit: list, pdf_prop: str, invoice_guid_dict, pdf_dir):
  runs = ceil(len(inv_or_credit) / parallel)
  print("save_files: runs: {}, length: {}".format(runs, len(inv_or_credit)))
  for run in range(runs):
    start = run * parallel
    end = (run + 1) * parallel
    print("save_files: run: {} start: {} end: {}".format(run, start, end))

    pdf_futures = []
    for item in inv_or_credit[run * parallel: (run + 1) * parallel]:
      pdf_futures.append(
        download_file(item[pdf_prop], invoice_guid_dict.get(item["number"])["filename"], pdf_dir))
    await asyncio.gather(*pdf_futures)


async def download_file(file_link: str, file_name: str, dl_dir):
  async with aiohttp.ClientSession() as session:

    file_path = os.path.join(dl_dir, file_name)
    if os.path.exists(file_path):
      return

    async with session.get(file_link) as r:
      if r.status != 200:
        print("HTTP status {}".format(r.status))
        return

      f = await aiofiles.open(file_path, mode='wb')
      await f.write(await r.read())
      await f.close()
