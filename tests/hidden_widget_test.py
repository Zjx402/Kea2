import unittest
from kea2.u2Driver import _HindenWidgetFilter
from lxml import etree
from pathlib import Path


XML_PATH = Path(__file__).parent / "hidden_widget_test.xml"


class TestHiddenWidget(unittest.TestCase):

    def test_hidden_widget(self):
        xml: etree._ElementTree = etree.parse(XML_PATH)
        self.xml: etree._Element = xml.getroot()
        _HindenWidgetFilter(self.xml)
