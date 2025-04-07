## Usage

Take uiautomator2 as ScriptDriver for example.

```python
import unittest
import uiautomator2 as u2

from kea.keaUtils import precondition, prob, KeaTestRunner, Options
from kea.u2Driver import U2Driver


class Test1(unittest.TestCase):

    def setUp(self):
        self.d = u2.connect()

    @prob(0.7)
    @precondition(lambda self: self.d(text="Omni Notes Alpha").exists and self.d(text="Settings").exists)
    def test_goToPrivacy(self):
        self.d(text="Settings").click()
        self.d(text="Privacy").click()

    @precondition(lambda self: self.d(resourceId = "it.feio.android.omninotes.alpha:id/search_src_text").exists)
    def test_rotation(self):
        self.d.set_orientation("l")
        self.d.set_orientation("n")
        assert self.d(resourceId="it.feio.android.omninotes.alpha:id/search_src_text").exists()


class Test2(unittest.TestCase):
    def test_NoPre02(self):
        print("NoPre02")
        assert 1 == 1

    @precondition(lambda self: self.d(text="Am").exists)
    def test_Pre02(self):
        print("Pre02")
        assert 3 == 3


KeaTestRunner.setOptions(
    Options(
        driverName="d",
        maxStep=500,
        Driver=U2Driver,
        packageNames=["it.feio.android.omninotes.alpha"]
    )
)

if __name__ == "__main__":
    unittest.main(testRunner=KeaTestRunner)
```