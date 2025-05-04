## Intro 

Kea4Fastbot is an easy-to-use Python library for supporting and customizing automated UI testing for mobile apps. The library is currently built on top of [Fastbot](https://github.com/bytedance/Fastbot_Android) and [uiautomator2](https://github.com/openatx/uiautomator2), and targeting [Android](https://en.wikipedia.org/wiki/Android_(operating_system)) apps.

It has these important features:
- coming with the full capability of [Fastbot](https://github.com/bytedance/Fastbot_Android) for finding *stability problems* (i.e., *crashing bugs*); 
- customizing specific testing scenarios (自定义测试场景或事件序列[^1], e.g., testing specific app functionalities, executing specific event traces, entering difficult-to-reach areas, creating specific app states) with the full capability and flexibility powered by *python* language and [uiautomator2](https://github.com/openatx/uiautomator2);
- supporting auto-assertions (断言机制[^2]) during automated GUI testing, based on the idea of [property-based testing](https://en.wikipedia.org/wiki/Software_testing#Property_testing) inheritted from [Kea](https://github.com/ecnusse/Kea), for finding *logic bugs* (i.e., *non-crashing bugs*)

> In essence, Kea4Fastbot is designed to be capable of fusing the (property-based) *scripted tests* (e.g., written in uiautomator2) with automated UI testing tools (e.g., Fastbot), thus combining the strengths of human knowledge on app's business logics (empowered by the scripted tests) and random fuzzing. Many useful features (e.g., mimicing exploratory testing) can be implemented based on such a capability.
 
Kea4Fastbot, released as a Python library, currently works with:
- [unittest](https://docs.python.org/3/library/unittest.html) as the testing framework;
- [uiautomator2](https://github.com/openatx/uiautomator2) as the UI test driver; 
- [Fastbot](https://github.com/bytedance/Fastbot_Android) as the backend automated GUI testing tool.

In the future, Kea4Fastbot is planned to additionally support
- [pytest](https://docs.pytest.org/en/stable/)
- [Appium](https://github.com/appium/appium), [Hypium]()
- other automated UI testing tools (not limited to Fastbot)

> Kea4Fastbot is inspired by many valuable insights, advices and lessons shared by experienced industrial practitioners. Kudos!

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


if __name__ == "__main__":
    KeaTestRunner.setOptions(
        Options(
            driverName="d",
            maxStep=500,
            Driver=U2Driver,
            packageNames=["it.feio.android.omninotes.alpha"]
        )
    )
    unittest.main(testRunner=KeaTestRunner)
```

### Run mutiple properties with unittest.

Kea is compatible with `unittest` framework. You can manage your test cases in unittest style.

To do so, launch Kea4Fastbot with `kea_launcher.py`. And set the args in `unittest` sub-commands.

You will have the following two sub-commands.

- **driver** : Settings of kea options.
- **unittest** : Settings of unittest.

Launch kea with 
```
python3 kea_launcher.py driver <fastbot cmds> unittest <unittest cmds> 
```

Sample commands:

```bash
# Launch fastbot with command followed by driver (Same in `options`). Load the properties (testCases) from directory mytests/omni_notes
python3 kea_launcher.py driver -s "emulator-5554" -p it.feio.android.omninotes.alpha --agent u2 --running-minutes 10 --throttle 200 --driver-name d unittest discover -s mytests/omni_notes

# Launch fastbot and load properties from quickstart2.py.
python3 kea_launcher.py driver <...> unittest quickstart2.py
```

> Hint: All commands in unittest is compatible in kea_launcher's sub-commands. See `python3 -m unittest -h` for details.

## Contributors/Maintainers

Kea4Fastbot has been actively developed and maintained by the people in [ecnusse](https://github.com/ecnusse).

### Open-source projects used by Kea4Fastbot

- [Fastbot](https://github.com/bytedance/Fastbot_Android)
- [uiautomator2](https://github.com/openatx/uiautomator2)
- [hypothesis](https://github.com/HypothesisWorks/hypothesis)

[^1]: 不少UI自动化测试工具提供了“自定义事件序列”能力（如[Fastbot](https://github.com/bytedance/Fastbot_Android/blob/main/handbook-cn.md#%E8%87%AA%E5%AE%9A%E4%B9%89%E4%BA%8B%E4%BB%B6%E5%BA%8F%E5%88%97) 和[AppCrawler](https://github.com/seveniruby/AppCrawler)），但在实际使用中存在不少问题，如自定义能力有限、使用不灵活等。此前不少Fastbot用户抱怨过其“自定义事件序列”在使用中的问题，如[#209](https://github.com/bytedance/Fastbot_Android/issues/209), [#225](https://github.com/bytedance/Fastbot_Android/issues/225), [#286](https://github.com/bytedance/Fastbot_Android/issues/286)等。

[^2]: 在UI自动化测试过程中支持自动断言是一个很重要的能力，但几乎没有测试工具提供这样的能力。我们注意到[AppCrawler](https://ceshiren.com/t/topic/15801/5)的开发者曾经希望提供一种断言机制，得到了用户的热切响应，不少用户从21年就开始催更，但始终未能实现。