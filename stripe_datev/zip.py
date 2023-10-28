import datetime
import shutil
import os.path
from zipfile import ZipFile


def zip_pdfs(outfile: str, path: str):

  archived = shutil.make_archive(outfile, 'zip', path)


def zip_compressed_pdfs(outfile: str, path: str, month: str):
  print("Zip files", month)
  with ZipFile(outfile, 'w') as zip_object:
    # Traverse all files in directory
    for folder_name, sub_folders, file_names in os.walk(path):
      for filename in file_names:
        if not filename.startswith(month) and not filename == "document.xml":
          continue
        # Create filepath of files in directory
        file_path = os.path.join(folder_name, filename)
        # Add files to zip file
        zip_object.write(file_path, os.path.basename(file_path))
