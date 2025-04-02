import abc
from xml.etree import ElementTree

class AbstractScriptDriver(abc.ABC):
    def getInstace(self):
        pass

class AbstractStaticChecker(abc.ABC):
    def __init__(self, xml: ElementTree):
        pass