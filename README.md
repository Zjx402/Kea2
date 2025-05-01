## Intro 

Kea4Fastbot is a novel, automated UI testing tool for mobile apps which is able to fuse *scripted tests* and *fully automated GUI fuzzing*. It aims to combine the strengths of human knowledge on app business logics (encoded and customized by the scripted tests) and random fuzzing (powered by automated UI testing tools).

> Kea4Fastbot, a successor of [Kea](https://github.com/ecnusse/Kea), is inspired by many valuable insights, advices and lessons from experienced industrial practitioners. 
Kea itself is a UI testing tool based on the idea of [property-based testing](https://en.wikipedia.org/wiki/Software_testing#Property_testing) for finding functional (logic) bugs in mobile apps, in addition to crashing bugs.
Kea is built on top of [DroidBot](https://github.com/honeynet/droidbot) and 
supports Android and HarmonyOS.
Note that Kea4Fastbot also fully supports but is not limited to property-based testing. 

Kea4Fastbot is released as an easy-to-use Python library
and works with:

- [unittest](https://docs.python.org/3/library/unittest.html) as the testing framework;
- [uiautomator2](https://github.com/openatx/uiautomator2) as the UI test driver; 
- [Fastbot](https://github.com/bytedance/Fastbot_Android) as the backend automated GUI testing tool.

In the future, Kea4Fastbot is planned to support
- [pytest](https://docs.pytest.org/en/stable/)
- [Appium](https://github.com/appium/appium), [Hypium]()
- Any UI testing tools (not limited to Fastbot)



## Installation

Running requirements or environment:
- support Windows, MacOS and Linux
- python 3.8+
- Android SDK installed
- VPN disabled

1. Create a workspace and clone this repository into the workspace.

```bash
mkdir Kea4Fastbot && cd Kea4Fastbot
git clone https://github.com/XixianLiang/KeaPlus.git
cd KeaPlus
```

2. Setup python envirnment with uv
```bash
pip install --upgrade pip
pip install uv
uv sync
```

> [uv](https://docs.astral.sh/uv/) is a python package manager.

## Quick Start

1. Create and start an Android emulator (e.g., Android 12 -- API version 31).

```bash
sdkmanager "system-images;android-31;google_apis;x86_64"
avdmanager create avd --force --name Android12 --package 'system-images;android-31;google_apis;x86_64' --abi google_apis/x86_64 --sdcard 1024M --device 'Nexus 7'
emulator -avd Android12 -port 5554 &
```

or, prepare one real Android device (not two) with `Developer Options` enabled, connect this device to your machine, and make sure you can see the connected device by running `adb devices`.

2. run `quickstart.py` to fuzz a sample app `omninotes`.
The script will automatically download the sample app `omninotes`'s apk `omninotes.apk` and run.

```python
uv run quickstart.py
```

> [quickstart.py](https://github.com/XixianLiang/KeaPlus/blob/main/quickstart.py) gives a dead simple scripted test which is ready-to-go with Fastbot. You can customize this script test for testing your apps at your needs.

### How to understand and customize the script test `quickstart.py` ? - Step by step guide.

1. Extend the python unittest.TestCase module and write your own script

    ```python
    from kea.keaUtils import precondition, KeaTestRunner, Options
    from kea.u2Driver import U2Driver

    class MyTest(unittest.TestCase):
        # [Attention] Only the method starts with test will be found by unittest
        # [Attention] Only the test method decorated with precond will be loaded as a property
        @precondition(lambda self: ...)
        def test_func1(self):...
    ```

2. Set the Configurations.

    ```python
    KeaTestRunner.setOptions(
        Options(
            # what you written in script
            # if driver is (self.d), then driverName="d"
            # if driver is (self.device) then driverName="device"
            driverName="d",
            # Use the U2Driver
            Driver=U2Driver,
            ...
        )
    )
    ```

3. Use the KeaTestRunner. Save your script and run with `python3 <...>.py`.
   
    ```python
    unittest.main(testRunner=KeaTestRunner)
    ```


### `mytest.py` Full example

```python
import unittest
import uiautomator2 as u2

from kea.keaUtils import precondition, prob, KeaTestRunner, Options
from kea.u2Driver import U2Driver


class Test1(unittest.TestCase):

    def setUp(self):
        self.d = u2.connect()

    @prob(0.7) # The propbability to exec this proprety when precond statisfied is 0.7
    @precondition(lambda self: self.d(text="Omni Notes Alpha").exists and self.d(text="Settings").exists)
    def test_goToPrivacy(self):
        """
        The ability to jump out of the UI tarpits

        precond:
            The drawer was opened
        action:
            go to settings -> privacy
        """
        self.d(text="Settings").click()
        self.d(text="Privacy").click()

    @precondition(lambda self: self.d(resourceId = "it.feio.android.omninotes.alpha:id/search_src_text").exists)
    def test_rotation(self):
        """
        The ability to make assertion to find functional bug

        precond:
            The search input box is opened
        action:
            rotate the device (set it to landscape, then back to natural)
        assertion:
            The search input box is still being opened
        """
        self.d.set_orientation("l")
        self.d.set_orientation("n")
        assert self.d(resourceId="it.feio.android.omninotes.alpha:id/search_src_text").exists()


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

## Contributors/Maintainers

Kea4Fastbot has been actively developed and maintained by the people in [ecnusse](https://github.com/ecnusse).

### Open-source projects used by Kea4Fastbot

- [Fastbot](https://github.com/bytedance/Fastbot_Android)
- [uiautomator2](https://github.com/openatx/uiautomator2)
- [hypothesis](https://github.com/HypothesisWorks/hypothesis)

### Relevant projects

- [Kea](https://github.com/ecnusse/Kea)
- [appcrawler](https://github.com/seveniruby/AppCrawler)
