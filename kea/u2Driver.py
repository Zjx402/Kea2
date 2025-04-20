import random
import socket
import uiautomator2 as u2
import types
from typing import Dict, Union
from xml.etree import ElementTree
from .absDriver import AbstractScriptDriver, AbstractStaticChecker, AbstractDriver
from .adbUtils import list_forwards, remove_forward, create_forward


class U2ScriptDriver(AbstractScriptDriver):

    deviceSerial: str = None
    
    @classmethod
    def setDeviceSerial(cls, deviceSerial):
        cls.deviceSerial = deviceSerial
    
    def __init__(self):
        self.d = None

    def getInstance(self):
        if self.d is None:
            self.d = (
                u2.connect() if self.deviceSerial is None
                else u2.connect(self.deviceSerial)
            )
            
            def rewrite_forward_port():
                """rewrite forward_port mothod to avoid the relocation of port 
                """
                print("Rewriting forward_port method")
                self.d._dev.forward_port = types.MethodType(
                                forward_port, self.d._dev)
                lport = self.d._dev.forward_port(8090)
                setattr(self.d._dev, "msg", "meta")
                print(f"local port: {lport}")
                
                self.d.port = lport
            
            def remove_9008_forward_port():
                """remove the forward to tcp:9008
                """
                forwardLists = list_forwards(device=self.deviceSerial)
                for forward in forwardLists:
                    if forward["remote"] == "tcp:9008":
                        forward_local = forward["local"]
                        print("uiautomator2 server local port %s" % forward_local)
                        remove_forward(local_spec=forward_local, device=self.deviceSerial)
                        create_forward(local_spec=forward_local, remote_spec="tcp:8090", device=self.deviceSerial)
                        print("rewrite the uiautomator2 server remote port to %s" % "tcp:8090")
                        self.d.port = forward_local.split(":")[-1]
            
            rewrite_forward_port()
            remove_9008_forward_port()

        return self.d


class StaticU2UiObject(u2.UiObject):
    def __init__(self, session, selector):
        self.session: U2StaticDevice = session
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

class U2StaticDevice(u2.Device):
    def __init__(self):
        self.xml_raw = None
        self.xml = None

    def __call__(self, **kwargs):
        return StaticU2UiObject(session=self, selector=u2.Selector(**kwargs))

    @property
    def xpath(self) -> u2.xpath.XPathEntry:
        def get_page_source(self):
            print("using new get_page_source")
            return u2.xpath.PageSource.parse(self._d.xml_raw)
        xpathEntry = u2.xpath.XPathEntry(self)
        xpathEntry.get_page_source = types.MethodType(
            get_page_source, xpathEntry
        )
        return xpathEntry


class U2StaticChecker(AbstractStaticChecker):

    def __init__(self):
        self.d = U2StaticDevice() 

    def setHierarchy(self, hierarchy: str):
        self.d.xml_raw = hierarchy
        with open("tmp.xml", "w") as fp:
            fp.write(hierarchy)
            fp.flush()
        self.d.xml = ElementTree.parse("tmp.xml")

    def getInstance(self, hierarchy: str):
        self.setHierarchy(hierarchy)
        return self.d


class U2Driver(AbstractDriver):
    scriptDriver = None
    staticChecker = None
    
    @classmethod
    def setDeviceSerial(cls, deviceSerial):
        U2ScriptDriver.setDeviceSerial(deviceSerial)

    @classmethod
    def getScriptDriver(self):
        if self.scriptDriver is None:
            self.scriptDriver = U2ScriptDriver()
        return self.scriptDriver.getInstance()

    @classmethod
    def getStaticChecker(self, hierarchy):
        if self.staticChecker is None:
            self.staticChecker = U2StaticChecker()
        return self.staticChecker.getInstance(hierarchy)


def forward_port(self, remote: Union[int, str]) -> int:
        """forward remote port to local random port"""
        remote = 8090
        if isinstance(remote, int):
            remote = "tcp:" + str(remote)
        for f in self.forward_list():
            if (
                f.serial == self._serial
                and f.remote == remote
                and f.local.startswith("tcp:")
            ):  # yapf: disable
                return int(f.local[len("tcp:") :])
        local_port = get_free_port()
        self.forward("tcp:" + str(local_port), remote)
        return local_port


def is_port_in_use(port: int) -> bool:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        return s.connect_ex(('127.0.0.1', port)) == 0


def get_free_port():
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.bind(('127.0.0.1', 0))
        try:
            return s.getsockname()[1]
        finally:
            s.close()
    except OSError:
        # bind 0 will fail on Manjaro, fallback to random port
        # https://github.com/openatx/adbutils/issues/85
        for _ in range(20):
            port = random.randint(10000, 20000)
            if not is_port_in_use(port):
                return port
        raise RuntimeError("No free port found")
