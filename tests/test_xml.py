import unittest
from stripe_datev.xml import create_xml


class TestCreateXml(unittest.TestCase):

  def test_create_xml(self):
    create_xml("/Users/benny/angular/stripe-datev-exporter_ori/out/xml")


if __name__ == '__main__':
  unittest.main()
