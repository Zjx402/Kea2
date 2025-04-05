import uiautomator2 as u2
from typing import Dict
from xml.etree import ElementTree
from .absDriver import AbstractScriptDriver
from .adbUtils import list_forwards, remove_forward, create_forward


class U2ScriptDriver(AbstractScriptDriver):

    deviceSerial: str = None
    
    @classmethod
    def setDeviceSerial(cls, deviceSerial):
        cls.deviceSerial = deviceSerial
    
    def __init__(self):
        self.d = None

    def getInstance(self):
        """
        Singleton design
        """
        if self.d is None:
            self.d = (
                u2.connect() if self.deviceSerial is None
                else u2.connect(self.deviceSerial)
            )
            
            forwardLists = list_forwards(device=self.deviceSerial)
            for forward in forwardLists:
                if forward["remote"] == "tcp:9008":
                    forward_local = forward["local"]
                    print("uiautomator2 server local port %s" % forward_local)
                    remove_forward(local_spec=forward_local, device=self.deviceSerial)
                    create_forward(local_spec=forward_local, remote_spec="tcp:8090", device=self.deviceSerial)
                    print("rewrite the uiautomator2 server remote port to %s" % "tcp:8090")
                    self.d.port = forward_local.split(":")[-1]
                    break
        return self.d
    
    def getForwardList(self):
        pass
    
    def switchForward(self):
        pass


class StaticU2UiObject(u2.UiObject):
    def __init__(self, session, selector):
        self.session: U2StaticChecker = session
        self.selector = selector

    @property
    def exists(self):
        def filterU2Keys(originKey):
            filterDict = {
                "resourceId": "resource-id"
            }
            if filterDict.get(originKey, None):
                return filterDict[originKey]
            return originKey
        
        def getXPath(kwargs: Dict[str, str]):
            attrLocs = list()
            SPECIAL_KEY = {"mask", "childOrSibling", "childOrSiblingSelector"}
            for key, val in kwargs.items():
                if key in SPECIAL_KEY:
                    continue
                key = filterU2Keys(key)
                attrLocs.append(f"[@{key}='{val}']")
            xpath = f".//node{''.join(attrLocs)}"
            return xpath

        xpath = getXPath(self.selector)
        return self.session.xml.find(xpath) is not None


class U2StaticChecker(u2.Device):
    def __init__(self, xml):
        self.xml: ElementTree = xml

    def __call__(self, **kwargs):
        return StaticU2UiObject(session=self, selector=u2.Selector(**kwargs))