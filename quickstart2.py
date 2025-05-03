import unittest
import uiautomator2 as u2

from time import sleep
from kea.keaUtils import precondition, prob, KeaTestRunner, Options
from kea.u2Driver import U2Driver


class Omni_Notes_Sample(unittest.TestCase):

    def setUp(self):
        self.d = u2.connect()

    @prob(0.7)  # The probability of executing the function when precondition is satisfied.
    @precondition(
        lambda self: self.d(text="Omni Notes Alpha").exists
        and self.d(text="Settings").exists
    )
    def test_goToPrivacy(self):
        """
        The ability to jump out of the UI tarpits

        precond:
            The drawer was opened
        action:
            go to settings -> privacy
        """
        print("trying to click Settings")
        self.d(text="Settings").click()
        sleep(0.5)
        print("trying to click Privacy")
        self.d(text="Privacy").click()

    @precondition(
        lambda self: self.d(resourceId="it.feio.android.omninotes.alpha:id/search_src_text").exists
    )
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
        sleep(2)
        self.d.set_orientation("n")
        sleep(2)
        assert self.d(resourceId="it.feio.android.omninotes.alpha:id/search_src_text").exists()


PACKAGE_NAME = "it.feio.android.omninotes.alpha"
FILE_NAME = "omninotes.apk"

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
    KeaTestRunner.setOptions(
        Options(
            driverName="d",
            maxStep=50000,
            Driver=U2Driver,
            packageNames=[PACKAGE_NAME],
        )
    )
    unittest.main(testRunner=KeaTestRunner)
