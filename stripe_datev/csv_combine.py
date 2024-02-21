import pandas as pd
import os
from collections import defaultdict


def combine_revenue_extf_csvs(out_path: str, out_dir_dl: str, month: str):

  file_names = []
  csv_files = []

  for root, dirs, files in os.walk(out_path, topdown=False):
    for name in files:
      if name.startswith(f"EXTF_{month}_Revenue") and name.endswith(".csv"):
        # print('file', name)
        # print('file', os.path.join(root, name))
        file_names.append(name)
        csv_files.append(os.path.join(root, name))

  if len(file_names) != len(set(file_names)):
    print("duplicate files found")

  lines = ""

  for csv in csv_files:
    with open(csv, 'r', encoding="latin1") as f:

      if csv.endswith(f"EXTF_{month}_Revenue.csv"):
        print("found correct header file", csv)
        lines += f.readline()
        lines += f.readline()
        break

  for csv in csv_files:
    with open(csv, 'r', encoding="latin1") as f:

      next(f)
      next(f)

      for line in f:
        lines += line

  print("combine following csv into one")
  for f in file_names:
    print(f"- {f}")
  output_path = os.path.join(out_dir_dl, f"EXTF_{month}_combined_revenue.csv")
  with open(output_path, 'w', encoding="latin1", errors="replace", newline="\r\n") as fp:
    fp.write(lines)


# combine_revenue_extf_csvs(r"/Users/benny/angular/stripe-datev-exporter/out",
#                           r"/Users/benny/angular/stripe-datev-exporter/out/2023-10",
#                           "2023-10"
#                           )
