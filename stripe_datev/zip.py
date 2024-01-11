import os.path
from typing import List
from zipfile import ZipFile, ZIP_DEFLATED


def zip_compressed_pdfs(outfile: str, path: str, run: int, invoices: List[str], month: str):
  print("Zip files", month, path)
  with ZipFile(outfile, 'w', ZIP_DEFLATED) as zip_object:
    # Traverse all files in directory
    files: List[str] = []
    for folder_name, sub_folders, file_names in os.walk(path):
      for filename in file_names:
        if filename.startswith("document") and not filename == f"document_{run}.xml":
          continue
        # Create filepath of files in directory
        file_path = os.path.join(folder_name, filename)
        files.append(file_path)

    xml_path = next(f for f in files if f.endswith(f"document_{run}.xml"))
    zip_object.write(xml_path, "document.xml")

    for invoice in invoices:
        # Add files to zip file
      try:
        file_path = next(f for f in files if f.endswith(f"{invoice}.pdf"))
      except:
        print(invoices)
        print("Error: ", invoice)
        raise Exception("Sorry")

      file_path = next(f for f in files if f.endswith(f"{invoice}.pdf"))
      zip_object.write(file_path, os.path.basename(file_path))
