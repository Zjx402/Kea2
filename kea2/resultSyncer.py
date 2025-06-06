import threading
from .adbUtils import adb_shell, pull_file
from .utils import getLogger

logger = getLogger(__name__)


class ResultSyncer:

    def __init__(self, device_output_dir, output_dir):
        self.device_output_dir = device_output_dir
        self.output_dir = output_dir
        self.running = False
        self.thread = None
        self.sync_event = threading.Event()

    def run(self):
        """Start a background thread to sync device data when triggered"""
        self.running = True
        self.thread = threading.Thread(target=self._sync_thread, daemon=True)
        self.thread.start()

    def _sync_thread(self):
        """Thread function that waits for sync event and then syncs data"""
        while self.running:
            # Wait for sync event with a timeout to periodically check if still running
            if self.sync_event.wait(timeout=3):
                self._sync_device_data()
                self.sync_event.clear()

    def close(self):
        self.running = False
        self.sync_event.set()
        if self.thread and self.thread.is_alive():
            self.thread.join(timeout=10)
        self._sync_device_data()
        try:
            logger.debug(f"Removing device output directory: {self.device_output_dir}")
            remove_device_dir = ["rm", "-rf", self.device_output_dir]
            adb_shell(remove_device_dir)
        except Exception as e:
            logger.error(f"Error removing device output directory: {e}", flush=True)

    def _sync_device_data(self):
        """
        Sync the device data to the local directory.
        """
        try:
            logger.debug("Syncing data")

            pull_file(self.device_output_dir, str(self.output_dir))

            remove_pulled_screenshots = ["find", self.device_output_dir, "-name", "\"*.png\"", "-delete"]
            adb_shell(remove_pulled_screenshots)
        except Exception as e:
            logger.error(f"Error in data sync: {e}", flush=True)
