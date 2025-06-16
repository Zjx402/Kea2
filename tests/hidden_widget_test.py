import unittest
from kea2.u2Driver import _HindenWidgetFilter, U2Driver
from lxml import etree
from pathlib import Path


XML_PATH = Path(__file__).parent / "hidden_widget_test.xml"


def get_static_checker():
    xml: etree._ElementTree = etree.parse(XML_PATH)
    d = U2Driver.getStaticChecker(xml)
    return d


class TestHiddenWidget(unittest.TestCase):

    def test_hidden_widget(self):
        d = get_static_checker()
        assert not d(text="微信(690)").exist


class TestWidget(unittest.TestCase):

    def test_widget(self):
        d = get_static_checker()
        


if __name__ == "__main__":
    unittest.main()
