## Usage

Take uiautomator2 as ScriptDriver for example.

```python
import unittest
import uiautomator2 as u2
from kea.keaUtils import precondition, KeaTestRunner, Options
from kea.u2Driver import U2ScriptDriver, U2StaticChecker

class Test1(unittest.TestCase):

    def setUp(self):
        self.d = u2.connect()

    def test_noPre01(self):
        print("noPre01")
        assert "noPre01" == "noPre01"

    @precondition(lambda self: self.d(text="Cr").exists)
    def test_01(self):
        self.d(text="Cr").click()
        print("this is from the test")
        assert self.d(text="Add reminder").exists(timeout=3)


KeaTestRunner.setOptions(
    Options(
        driverName="d",
        maxStep=500,
        StaticChecker=U2StaticChecker,
        ScriptDriver=U2ScriptDriver,
    )
)

if __name__ == "__main__":
    unittest.main(testRunner=KeaTestRunner)
```