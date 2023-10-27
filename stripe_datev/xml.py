from datetime import datetime
from os import path
import xml.etree.ElementTree as ET

def create_xml(pdfDir: str, invoice_guid_dict: dict = None, year=None, month=None):
  
  root = ET.Element('archive',  xmlns="http://xml.datev.de/bedi/tps/document/v05.0", version="5.0", generatingSystem="custom")
  root.attrib["xmlns:xsi"] = "http://www.w3.org/2001/XMLSchema-instance"
  root.attrib["xsi:schemaLocation"] = "http://xml.datev.de/bedi/tps/document/v05.0 Document_v050.xsd"

  header = ET.SubElement(root, 'header')
  date = ET.SubElement(header, 'date')
  date.text = datetime.now().strftime("%Y-%m-%d")

  content = ET.SubElement(root, 'content')

  for key in invoice_guid_dict:

    inv = invoice_guid_dict[key]

    document = ET.SubElement(content, 'document', processID="2")
    document.attrib["guid"]=inv["guid"]

    keywords = ET.SubElement(document, 'keywords')
    keywords.text = "RgNr.: {}".format(key)

    extension = ET.SubElement(document, 'extension')
    extension.attrib["xsi:type"] = "File"
    extension.attrib["name"] = inv["filename"]


    repository = ET.SubElement(document, 'repository')
    ET.SubElement(repository, 'level', id="1", name="custom - Stripe Billing")
    ET.SubElement(repository, 'level', id="2", name="Belege")
    ET.SubElement(repository, 'level', id="3", name="{}/{}".format(year, month))

  

  tree = ET.ElementTree(root)

  out = open(path.join(pdfDir, "document.xml"), 'wb')
  out.write(b'<?xml version="1.0" encoding="UTF-8" standalone = "yes"?>\n')
  tree.write(out, encoding = 'UTF-8', xml_declaration = False)
  out.close()