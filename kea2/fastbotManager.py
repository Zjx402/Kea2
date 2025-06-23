import subprocess
import threading
from dataclasses import asdict
import requests
from time import sleep


from uiautomator2.core import HTTPResponse, _http_request
from kea2.adbUtils import ADBDevice, ADBStreamShell_V2
from pathlib import Path
from kea2.utils import getLogger


from typing import IO, TYPE_CHECKING, Dict
if TYPE_CHECKING:
    from .keaUtils import Options


logger = getLogger(__name__)


class FastbotManager:
    def __init__(self, options: "Options", log_file: str):
        self.options:"Options" = options
        self.log_file: str = log_file
        self.port = None
        self.thread = None
        self._device_output_dir = None
        ADBDevice.setDevice(options.serial, options.transport_id)
        self.dev = ADBDevice()

    def _activateFastbot(self) -> ADBStreamShell_V2:
        """
        activate fastbot.
        :params: options: the running setting for fastbot
        :params: port: the listening port for script driver
        :return: the fastbot daemon thread
        """
        cur_dir = Path(__file__).parent
        self.dev.sync.push(
            Path.joinpath(cur_dir, "assets/monkeyq.jar"),
            "/sdcard/monkeyq.jar"
        )
        self.dev.sync.push(
            Path.joinpath(cur_dir, "assets/fastbot-thirdpart.jar"),
            "/sdcard/fastbot-thirdpart.jar",
        )
        self.dev.sync.push(
            Path.joinpath(cur_dir, "assets/kea2-thirdpart.jar"),
            "/sdcard/kea2-thirdpart.jar",
        )
        self.dev.sync.push(
            Path.joinpath(cur_dir, "assets/framework.jar"),
            "/sdcard/framework.jar",
        )
        self.dev.sync.push(
            Path.joinpath(cur_dir, "assets/fastbot_libs/arm64-v8a/libfastbot_native.so"),
            "/data/local/tmp/arm64-v8a/libfastbot_native.so",
        )
        self.dev.sync.push(
            Path.joinpath(cur_dir, "assets/fastbot_libs/armeabi-v7a/libfastbot_native.so"),
            "/data/local/tmp/armeabi-v7a/libfastbot_native.so",
        )
        self.dev.sync.push(
            Path.joinpath(cur_dir, "assets/fastbot_libs/x86/libfastbot_native.so"),
            "/data/local/tmp/x86/libfastbot_native.so",
        )
        self.dev.sync.push(
            Path.joinpath(cur_dir, "assets/fastbot_libs/x86_64/libfastbot_native.so"),
            "/data/local/tmp/x86_64/libfastbot_native.so",
        )

        t = self._startFastbotService()
        logger.info("Running Fastbot...")

        return t


    def check_alive(self):
        """
        check if the script driver and proxy server are alive.
        """

        for _ in range(10):
            sleep(2)
            try:
                _http_request(
                    dev=self.dev,
                    device_port=8090,
                    method="GET",
                    path="/ping",
                )
                return
            except requests.ConnectionError:
                logger.info("waiting for connection.")
                pass
        raise RuntimeError("Failed to connect fastbot")

    def request(self, method: str, path: str, data: Dict=None, timeout: int=10) -> HTTPResponse:
        return _http_request(self.dev, 8090, method, path, data, timeout)

    def init(self, options: "Options", stamp):
        post_data = {
            "takeScreenshots": options.take_screenshots,
            "Stamp": stamp,
            "deviceOutputRoot": options.device_output_root,
        }
        r = _http_request(
            self.dev,
            device_port=8090,
            method="POST",
            path="/init",
            data=post_data
        )
        print(f"[INFO] Init fastbot: {post_data}", flush=True)
        import re
        self._device_output_dir = re.match(r"outputDir:(.+)", r.text).group(1)
        print(f"[INFO] Fastbot initiated. outputDir: {r.text}", flush=True)
    
    def stepMonkey(self, monkeyStepInfo):
        r = self.request(
            method="POST",
            path="/stepMonkey",
            data=monkeyStepInfo
        )
        return r.json()["result"]

    def stopMonkey(self):
        """
        send a stop monkey request to the server.
        """
        r = self.request(
            method="GET",
            path="/stopMonkey",
        )

        print(f"[Server INFO] {r.text}", flush=True)
    
    def logScript(self, execution_info: Dict):
        r = self.request(
            method="POST",
            path="/logScript",
            data=execution_info
        )
        res = r.text
        if res != "OK":
            print(f"[ERROR] Error when logging script: {execution_info}", flush=True)

    @property
    def device_output_dir(self):
        return self._device_output_dir

    def _startFastbotService(self) -> ADBStreamShell_V2:
        shell_command = [
            "CLASSPATH="
            "/sdcard/monkeyq.jar:"
            "/sdcard/framework.jar:"
            "/sdcard/fastbot-thirdpart.jar:"
            "/sdcard/kea2-thirdpart.jar",

            "exec", "app_process",
            "/system/bin", "com.android.commands.monkey.Monkey",
            "-p", *self.options.packageNames,
            "--agent-u2" if self.options.agent == "u2" else "--agent",
            "reuseq",
            "--running-minutes", f"{self.options.running_mins}",
            "--throttle", f"{self.options.throttle}",
            "--bugreport",
        ]

        if self.options.profile_period:
            shell_command += ["--profile-period", f"{self.options.profile_period}"]

        shell_command += ["-v", "-v", "-v"]

        full_cmd = ["adb"] + (["-s", self.options.serial] if self.options.serial else []) + ["shell"] + shell_command


        outfile = open(self.log_file, "w", encoding="utf-8", buffering=1)

        logger.info("Options info: {}".format(asdict(self.options)))
        logger.info("Launching fastbot with shell command:\n{}".format(" ".join(full_cmd)))
        logger.info("Fastbot log will be saved to {}".format(outfile.name))

        # stream = self.dev.shell(shell_command, encoding="utf-8", stream=True, timeout=float("inf"))
        # process handler
        t = self.dev.stream_shell(shell_command, stdout=outfile, stderr=outfile)
        # proc = subprocess.Popen(full_cmd, stdout=outfile, stderr=outfile)
        # t = threading.Thread(target=self.close_on_exit, args=(proc, outfile), daemon=True)
        # t.start()
        return t

    def close_on_exit(self, proc: ADBStreamShell_V2, f: IO):
        self.return_code = proc.wait()
        f.close()
        if self.return_code != 0:
            raise RuntimeError(f"Fastbot Error: Terminated with [code {self.return_code}] See {self.log_file} for details.")

    def get_return_code(self):
        if self.thread.is_running():
            logger.info("Waiting for Fastbot to exit.")
            return self.thread.wait()
        return self.thread.poll()

    def start(self):
        self.thread = self._activateFastbot()

    def join(self):
        self.thread.join()




