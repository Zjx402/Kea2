import sys
import subprocess
import threading
from adbutils import AdbConnection
from dataclasses import asdict
import requests
from time import sleep

import uiautomator2.core

from kea2.adbUtils import ADBDevice
from pathlib import Path
from kea2.utils import getLogger
import uiautomator2
uiautomator2.core.U2_PORT = 8090

from typing import IO, TYPE_CHECKING, Generator, Optional, List, Union
if TYPE_CHECKING:
    from .keaUtils import Options

logger = getLogger(__name__)


class ADBStreamShell:
    def __init__(self, serial: str = None, transport_id: str = None):
        ADBDevice.setDevice(serial=serial, transport_id=transport_id)
        self.dev = ADBDevice()
        self._thread = None
        self._exit_code = 255

    def shell(
        self, cmdargs: Union[List[str], str],
        stdout: IO = None, stderr: IO = None,
        timeout: float = float("inf")
    ):
        self._finished = False
        self.stdout: IO = stdout if stdout else sys.stdout
        self.stderr: IO = stderr if stderr else sys.stderr
        self._generator = self._shell_v2(cmdargs, timeout)
        self._thread = threading.Thread(target=self._process_output, daemon=True)
        self._thread.start()

    def _process_output(self):
        try:
            for msg_type, data in self._generator:

                if msg_type == 'stdout':
                    self._write_stdout(data)
                elif msg_type == 'stderr':
                    self._write_stderr(data)
                elif msg_type == 'exit':
                    self._exit_code = data
                    break

        except Exception as e:
            print(f"ADBStreamShell execution error: {e}")
            self._exit_code = -1

    def _write_stdout(self, data: bytes):
        text = data.decode('utf-8', errors='ignore')
        sys.stdout.write(text)
        sys.stdout.flush()

    def _write_stderr(self, data: bytes):
        text = data.decode('utf-8', errors='ignore')
        self.stderr.write(text)
        self.stderr.flush()

    def _shell_v2(self, cmdargs: List[str], timeout) -> Generator:
        c: AdbConnection = self.dev.open_transport(timeout=timeout)
        cmd = " ".join(cmdargs)
        c.send_command(f"shell,v2:{cmd}")
        c.check_okay()
        try:
            while True:
                header = c.read_exact(5)
                msg_id = header[0]
                length = int.from_bytes(header[1:5], byteorder="little")

                if length == 0:
                    continue

                data = c.read_exact(length)

                if msg_id == 1:
                    yield ('stdout', data)
                elif msg_id == 2:
                    yield ('stderr', data)
                elif msg_id == 3:
                    yield ('exit', data[0])
                    break
        finally:
            c.close()

    def wait(self):
        if self._thread:
            self._thread.join()
        return self._exit_code

    def is_running(self) -> bool:
        return not self._finished


if __name__ == "__main__":
    ADBDevice.setDevice(serial="HMQNW20A27002747")
    dev = ADBDevice()

    adbshell = ADBStreamShell(serial="HMQNW20A27002747")
    adbshell.shell(["ls", "-l", "/sdcard/"], timeout=1000)
    print(adbshell.wait())
    sys.exit(0)


class FastbotManager:
    def __init__(self, options: "Options", log_file: str):
        self.options:"Options" = options
        self.log_file: str = log_file
        self.port = None
        self.thread = None
        ADBDevice.setDevice(options.serial, options.transport_id)
        self.dev = ADBDevice()


    def _activateFastbot(self) -> threading.Thread:
        """
        activate fastbot.
        :params: options: the running setting for fastbot
        :params: port: the listening port for script driver
        :return: the fastbot daemon thread
        """
        options = self.options
        cur_dir = Path(__file__).parent
        self.dev.push()
        self.dev.sync.push(
            Path.joinpath(cur_dir, "assets/monkeyq.jar"),
            "/sdcard/monkeyq.jar"
        )
        self.dev.sync.push(
            Path.joinpath(cur_dir, "assets/fastbot-thirdpart.jar"),
            "/sdcard/fastbot-thirdpart.jar",
        )
        self.dev.sync.push(
            Path.joinpath(cur_dir, "assets/framework.jar"), 
            "/sdcard/framework.jar",
        )
        self.dev.sync.push(
            Path.joinpath(cur_dir, "assets/fastbot_libs/arm64-v8a"),
            "/data/local/tmp",
        )
        self.dev.sync.push(
            Path.joinpath(cur_dir, "assets/fastbot_libs/armeabi-v7a"),
            "/data/local/tmp",
        )
        self.dev.sync.push(
            Path.joinpath(cur_dir, "assets/fastbot_libs/x86"),
            "/data/local/tmp",
        )
        self.dev.sync.push(
            Path.joinpath(cur_dir, "assets/fastbot_libs/x86_64"),
            "/data/local/tmp",
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
                uiautomator2.core._http_request(
                    dev=self.dev,
                    method="GET",
                    path="/ping",
                )
                return
            except requests.ConnectionError:
                logger.info("waiting for connection.")
                pass
        raise RuntimeError("Failed to connect fastbot")


    def _startFastbotService(self) -> threading.Thread:
        shell_command = [
            "CLASSPATH=/sdcard/monkeyq.jar:/sdcard/framework.jar:/sdcard/fastbot-thirdpart.jar",
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

        stream = self.dev.shell(shell_command, encoding="utf-8", stream=True, timeout=float("inf"))
        # process handler
        proc = subprocess.Popen(full_cmd, stdout=outfile, stderr=outfile)
        t = threading.Thread(target=self.close_on_exit, args=(proc, outfile), daemon=True)
        t.start()

        return t
    
    

    def close_on_exit(self, proc: subprocess.Popen, f: IO):
        self.return_code = proc.wait()
        f.close()
        if self.return_code != 0:
            raise RuntimeError(f"Fastbot Error: Terminated with [code {self.return_code}] See {self.log_file} for details.")

    def get_return_code(self):
        if self.thread:
            logger.info("Waiting for Fastbot to exit.")
            self.thread.join()
        return self.return_code

    def start(self):
        self.thread = self._activateFastbot()

    def join(self):
        if self.thread:
            self.thread.join()



