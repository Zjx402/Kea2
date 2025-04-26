## Usage

### Installation

Requirement:
-  `python 3.8+`, Recommand: `python 3.11`

- Android environment is installed

1. Create a workspace using mkdir. Clone this repo into the workspace.

```bash
mkdir FastbotKea && cd FastbotKea
git clone https://github.com/XixianLiang/KeaPlus.git
```

2. Setup python envirnment
```bash
python -m venv env
source env/bin/activate
```

3. Install requirnment (Android)
```bash
python -m pip install --upgrade pip
python -m pip install uiautomator2
``` 

4. Create a unittest script `mytest.py` in the workspace.

### Quick Start

1. Create and start an Android emulator (Android 12 -- API version 31).

```bash
sdkmanager "system-images;android-31;google_apis;x86_64"
avdmanager create avd --force --name Android12 --package 'system-images;android-31;google_apis;x86_64' --abi google_apis/x86_64 --sdcard 1024M --device 'Nexus 7'
emulator -avd Android12 -port 5554 &
```


We have a one-key start script `quickstart.py`. With this script,
You can download our sample app omninotes and try our tool.

```python
cd KeaPlus
python3 quickstart.py
```


### How to write the unittest script `mytest.py` ? - Step by step guide.

1. Extend the python unittest.TestCase module and write your own script

    ```python
    from kea.keaUtils import precondition KeaTestRunner, Options
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