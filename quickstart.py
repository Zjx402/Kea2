import unittest
import uiautomator2 as u2

from time import sleep
from kea.keaUtils import precondition, prob, KeaTestRunner, Options
from kea.u2Driver import U2Driver

PACKAGE_NAME = "it.feio.android.omninotes.alpha"
FILE_NAME = "omninotes.apk"

KeaTestRunner.setOptions(
    Options(
        driverName="d",
        maxStep=50000,
        Driver=U2Driver,
        packageNames=[PACKAGE_NAME],
    )
)

def check_installation():
    d = u2.connect()
    # automatically install omni-notes
    if PACKAGE_NAME not in d.app_list():
        from pathlib import Path
        # If omninotes.apk not find, download it.
        if not list(Path(".").glob(FILE_NAME)):
            import requests
            URL = "https://raw.githubusercontent.com/ecnusse/Kea/refs/heads/main/example/omninotes.apk"

            resp = requests.get(URL)
            resp.raise_for_status()

            with open(FILE_NAME, "wb") as f:
                f.write(resp.content)
                f.flush()

        d.app_install(FILE_NAME)

if __name__ == "__main__":
    check_installation()
    unittest.main(testRunner=KeaTestRunner)
