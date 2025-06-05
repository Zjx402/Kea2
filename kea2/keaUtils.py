import json
import os
from pathlib import Path
import subprocess
import threading
import traceback
from typing import IO, Callable, Any, Dict, List, Literal, NewType, Union
from unittest import TextTestRunner, registerResult, TestSuite, TestCase, TextTestResult
import random
import warnings
from dataclasses import dataclass, asdict
import requests
from .absDriver import AbstractDriver
from functools import wraps
from time import sleep
from .adbUtils import push_file, pull_directory, run_adb_command
from .logWatcher import LogWatcher
from .utils import TimeStamp, getProjectRoot, getLogger
from .u2Driver import StaticU2UiObject, selector_to_xpath
import uiautomator2 as u2
import types
import time

PRECONDITIONS_MARKER = "preconds"
PROP_MARKER = "prop"
MAX_TRIES_MARKER = "max_tries"

logger = getLogger(__name__)


# Class Typing
PropName = NewType("PropName", str)
PropertyStore = NewType("PropertyStore", Dict[PropName, TestCase])

STAMP = TimeStamp().getTimeStamp()
LOGFILE: str
RESFILE: str

def precondition(precond: Callable[[Any], bool]) -> Callable:
    """the decorator @precondition

    @precondition specifies when the property could be executed.
    A property could have multiple preconditions, each of which is specified by @precondition.
    """
    def accept(f):
        @wraps(f)
        def precondition_wrapper(*args, **kwargs):
            return f(*args, **kwargs)

        preconds = getattr(f, PRECONDITIONS_MARKER, tuple())

        setattr(precondition_wrapper, PRECONDITIONS_MARKER, preconds + (precond,))

        return precondition_wrapper

    return accept

def prob(p: float):
    """the decorator @prob

    @prob specify the propbability of execution when a property is satisfied.
    """
    p = float(p)
    if not 0 < p <= 1.0:
        raise ValueError("The propbability should between 0 and 1")
    def accept(f):
        @wraps(f)
        def precondition_wrapper(*args, **kwargs):
            return f(*args, **kwargs)

        setattr(precondition_wrapper, PROP_MARKER, p)

        return precondition_wrapper

    return accept


def max_tries(n: int):
    """the decorator @max_tries

    @max_tries specify the maximum tries of executing a property.
    """
    n = int(n)
    if not n > 0:
        raise ValueError("The maxium tries should be a positive integer.")
    def accept(f):
        @wraps(f)
        def precondition_wrapper(*args, **kwargs):
            return f(*args, **kwargs)

        setattr(precondition_wrapper, MAX_TRIES_MARKER, n)

        return precondition_wrapper

    return accept


@dataclass
class Options:
    """
    Kea and Fastbot configurations
    """
    # the driver_name in script (if self.d, then d.) 
    driverName: str
    # the driver (only U2Driver available now)
    Driver: AbstractDriver
    # list of package names. Specify the apps under test
    packageNames: List[str]
    # target device
    serial: str = None
    # test agent. "native" for stage 1 and "u2" for stage 1~3
    agent: Literal["u2", "native"] = "u2"
    # max step in exploration (availble in stage 2~3)
    maxStep: Union[str, float] = float("inf")
    # time(mins) for exploration
    running_mins: int = 10
    # time(ms) to wait when exploring the app
    throttle: int = 200
    # the output_dir for saving logs and results
    output_dir: str = "output"
    # the stamp for log file and result file, default: current time stamp
    log_stamp: str = None
    # the profiling period to get the coverage result.
    profile_period: int = None
    # take screenshots for every step
    take_screenshots: bool = False
    # the debug mode
    debug: bool = False

    def __setattr__(self, name, value):
        if value is None:
            return
        super().__setattr__(name, value)

    def __post_init__(self):
        if self.serial and self.Driver:
            self.Driver.setDeviceSerial(self.serial)
        if self.take_screenshots and self.profile_period is None:
            self.profile_period = 50
        global LOGFILE, RESFILE, STAMP
        if self.log_stamp:
            STAMP = self.log_stamp
        LOGFILE = f"fastbot_{STAMP}.log"
        RESFILE = f"result_{STAMP}.json"
        _check_package_installation(self.serial, self.packageNames)


def _check_package_installation(serial, packageNames):
    from .adbUtils import get_packages
    installed_packages = get_packages(device=serial)

    for package in packageNames:
        if package not in installed_packages:
            logger.error(f"package {package} not installed. Abort.")
            raise ValueError("package not installed")


@dataclass
class PropStatistic:
    precond_satisfied: int = 0
    executed: int = 0
    fail: int = 0
    error: int = 0

class PBTTestResult(dict):
    def __getitem__(self, key) -> PropStatistic:
        return super().__getitem__(key)


def getFullPropName(testCase: TestCase):
    return ".".join([
        testCase.__module__,
        testCase.__class__.__name__,
        testCase._testMethodName
    ])

class JsonResult(TextTestResult):
    res: PBTTestResult
    
    lastExecutedInfo: Dict = {
        "propName": "",
        "state": "",
    }

    @classmethod
    def setProperties(cls, allProperties: Dict):
        cls.res = dict()
        for testCase in allProperties.values():
            cls.res[getFullPropName(testCase)] = PropStatistic()

    def flushResult(self, outfile):
        json_res = dict()
        for propName, propStatitic in self.res.items():
            json_res[propName] = asdict(propStatitic)
        with open(outfile, "w", encoding="utf-8") as fp:
            json.dump(json_res, fp, indent=4)

    def addExcuted(self, test: TestCase):
        self.res[getFullPropName(test)].executed += 1
        self.lastExecutedInfo = {
            "propName": getFullPropName(test),
            "state": "start",
        }

    def addPrecondSatisfied(self, test: TestCase):
        self.res[getFullPropName(test)].precond_satisfied += 1

    def addFailure(self, test, err):
        super().addFailure(test, err)
        self.res[getFullPropName(test)].fail += 1
        self.lastExecutedInfo["state"] = "fail"

    def addError(self, test, err):
        super().addError(test, err)
        self.res[getFullPropName(test)].error += 1
        self.lastExecutedInfo["state"] = "error"

    def getExcuted(self, test: TestCase):
        return self.res[getFullPropName(test)].executed


def activateFastbot(options: Options, port=None) -> threading.Thread:
    """
    activate fastbot.
    :params: options: the running setting for fastbot
    :params: port: the listening port for script driver
    :return: the fastbot daemon thread
    """
    cur_dir = Path(__file__).parent
    push_file(
        Path.joinpath(cur_dir, "assets/monkeyq.jar"),
        "/sdcard/monkeyq.jar",
        device=options.serial
    )
    push_file(
        Path.joinpath(cur_dir, "assets/fastbot-thirdpart.jar"),
        "/sdcard/fastbot-thirdpart.jar",
        device=options.serial,
    )
    push_file(
        Path.joinpath(cur_dir, "assets/framework.jar"), 
        "/sdcard/framework.jar",
        device=options.serial
    )
    push_file(
        Path.joinpath(cur_dir, "assets/fastbot_libs/arm64-v8a"),
        "/data/local/tmp",
        device=options.serial
    )
    push_file(
        Path.joinpath(cur_dir, "assets/fastbot_libs/armeabi-v7a"),
        "/data/local/tmp",
        device=options.serial
    )
    push_file(
        Path.joinpath(cur_dir, "assets/fastbot_libs/x86"),
        "/data/local/tmp",
        device=options.serial
    )
    push_file(
        Path.joinpath(cur_dir, "assets/fastbot_libs/x86_64"),
        "/data/local/tmp",
        device=options.serial
    )

    t = startFastbotService(options)
    print("[INFO] Running Fastbot...", flush=True)

    return t


def check_alive(port):
    """
    check if the script driver and proxy server are alive.
    """
    for _ in range(10):
        sleep(2)
        try:
            requests.get(f"http://localhost:{port}/ping")
            return
        except requests.ConnectionError:
            print("[INFO] waiting for connection.", flush=True)
            pass
    raise RuntimeError("Failed to connect fastbot")


def startFastbotService(options: Options) -> threading.Thread:
    shell_command = [
        "CLASSPATH=/sdcard/monkeyq.jar:/sdcard/framework.jar:/sdcard/fastbot-thirdpart.jar",
        "exec", "app_process",
        "/system/bin", "com.android.commands.monkey.Monkey",
        "-p", *options.packageNames,
        "--agent-u2" if options.agent == "u2" else "--agent",
        "reuseq",
        "--running-minutes", f"{options.running_mins}",
        "--throttle", f"{options.throttle}",
        "--bugreport",
    ]

    if options.profile_period:
        shell_command += ["--profile-period", f"{options.profile_period}"]

    shell_command += ["-v", "-v", "-v"]

    full_cmd = ["adb"] + (["-s", options.serial] if options.serial else []) + ["shell"] + shell_command

    outfile = open(LOGFILE, "w", encoding="utf-8", buffering=1)

    print("[INFO] Options info: {}".format(asdict(options)), flush=True)
    print("[INFO] Launching fastbot with shell command:\n{}".format(" ".join(full_cmd)), flush=True)
    print("[INFO] Fastbot log will be saved to {}".format(outfile.name), flush=True)

    # process handler
    proc = subprocess.Popen(full_cmd, stdout=outfile, stderr=outfile)
    t = threading.Thread(target=close_on_exit, args=(proc, outfile), daemon=True)
    t.start()

    return t


def close_on_exit(proc: subprocess.Popen, f: IO):
    proc.wait()
    f.close()
  

class KeaTestRunner(TextTestRunner):

    resultclass: JsonResult
    allProperties: PropertyStore
    options: Options = None
    _block_funcs: Dict[Literal["widgets", "trees"], List[Callable]] = None
    # _block_trees_funcs = None
    _sync_thread: threading.Thread = None
    _sync_stop_event: threading.Event = None

    @classmethod
    def setOptions(cls, options: Options):
        if not isinstance(options.packageNames, list) and len(options.packageNames) > 0:
            raise ValueError("packageNames should be given in a list.")
        if options.Driver is not None and options.agent == "native":
            print("[Warning] Can not use any Driver when runing native mode.", flush=True)
            options.Driver = None
        cls.options = options

    def _setOuputDir(self):
        output_dir = Path(self.options.output_dir).absolute()
        output_dir.mkdir(parents=True, exist_ok=True)
        global LOGFILE, RESFILE
        LOGFILE = output_dir / Path(LOGFILE)
        RESFILE = output_dir / Path(RESFILE)
        logger.debug(f"Log file: {LOGFILE}")
        logger.debug(f"Result file: {RESFILE}")

    def run(self, test):

        self.allProperties = dict()
        self.collectAllProperties(test)

        if len(self.allProperties) == 0:
            print("[Warning] No property has been found.", flush=True)

        self._setOuputDir()

        JsonResult.setProperties(self.allProperties)
        self.resultclass = JsonResult

        result: JsonResult = self._makeResult()
        registerResult(result)
        result.failfast = self.failfast
        result.buffer = self.buffer
        result.tb_locals = self.tb_locals

        with warnings.catch_warnings():
            if self.warnings:
                # if self.warnings is set, use it to filter all the warnings
                warnings.simplefilter(self.warnings)
                # if the filter is 'default' or 'always', special-case the
                # warnings from the deprecated unittest methods to show them
                # no more than once per module, because they can be fairly
                # noisy.  The -Wd and -Wa flags can be used to bypass this
                # only when self.warnings is None.
                if self.warnings in ["default", "always"]:
                    warnings.filterwarnings(
                        "module",
                        category=DeprecationWarning,
                        message=r"Please use assert\w+ instead.",
                    )

            t = activateFastbot(options=self.options)
            log_watcher = LogWatcher(LOGFILE)
            if self.options.agent == "native":
                t.join()
            else:
                # initialize the result.json file
                result.flushResult(outfile=RESFILE)
                # setUp for the u2 driver
                self.scriptDriver = self.options.Driver.getScriptDriver()
                check_alive(port=self.scriptDriver.lport)
                self._init()

                end_by_remote = False
                self.stepsCount = 0
                while self.stepsCount < self.options.maxStep:

                    self.stepsCount += 1
                    print("[INFO] Sending monkeyEvent {}".format(
                        f"({self.stepsCount} / {self.options.maxStep})" if self.options.maxStep != float("inf")
                        else f"({self.stepsCount})"
                        )
                    , flush=True)

                    try:
                        xml_raw = self.stepMonkey()
                        propsSatisfiedPrecond = self.getValidProperties(xml_raw, result)
                    except requests.ConnectionError:
                        print(
                            "[INFO] Exploration times up (--running-minutes)."
                        , flush=True)
                        end_by_remote = True
                        break

                    print(f"{len(propsSatisfiedPrecond)} precond satisfied.", flush=True)

                    # Go to the next round if no precond satisfied
                    if len(propsSatisfiedPrecond) == 0:
                        continue

                    # get the random probability p
                    p = random.random()
                    propsNameFilteredByP = []
                    # filter the properties according to the given p
                    for propName, test in propsSatisfiedPrecond.items():
                        result.addPrecondSatisfied(test)
                        if getattr(test, "p", 1) >= p:
                            propsNameFilteredByP.append(propName)

                    if len(propsNameFilteredByP) == 0:
                        print("Not executed any property due to probability.", flush=True)
                        continue

                    execPropName = random.choice(propsNameFilteredByP)
                    test = propsSatisfiedPrecond[execPropName]
                    # Dependency Injection. driver when doing scripts
                    self.scriptDriver = self.options.Driver.getScriptDriver()
                    setattr(test, self.options.driverName, self.scriptDriver)
                    print("execute property %s." % execPropName, flush=True)

                    result.addExcuted(test)
                    self._logScript(result.lastExecutedInfo)
                    try:
                        test(result)
                    finally:
                        result.printErrors()

                    self._logScript(result.lastExecutedInfo)
                    result.flushResult(outfile=RESFILE)

                if not end_by_remote:
                    self.stopMonkey()
                result.flushResult(outfile=RESFILE)

                # 停止数据同步线程
                self._stop_sync_thread()
                
                # 最后一次拉取测试结果，确保获取所有数据
                print("[INFO] Performing final test results pull...", flush=True)
                self.pull_test_results()

            print(f"Finish sending monkey events.", flush=True)
            log_watcher.close()
            
            # 自动拉取测试结果
            if self.options.agent != "native" and hasattr(self, 'device_output_dir'):
                print("[INFO] Pulling test results from device...", flush=True)
                self.pull_test_results()

        # Source code from unittest Runner
        # process the result
        expectedFails = unexpectedSuccesses = skipped = 0
        try:
            results = map(
                len,
                (result.expectedFailures, result.unexpectedSuccesses, result.skipped),
            )
        except AttributeError:
            pass
        else:
            expectedFails, unexpectedSuccesses, skipped = results

        infos = []
        if not result.wasSuccessful():
            self.stream.write("FAILED")
            failed, errored = len(result.failures), len(result.errors)
            if failed:
                infos.append("failures=%d" % failed)
            if errored:
                infos.append("errors=%d" % errored)
        else:
            self.stream.write("OK")
        if skipped:
            infos.append("skipped=%d" % skipped)
        if expectedFails:
            infos.append("expected failures=%d" % expectedFails)
        if unexpectedSuccesses:
            infos.append("unexpected successes=%d" % unexpectedSuccesses)
        if infos:
            self.stream.writeln(" (%s)" % (", ".join(infos),))
        else:
            self.stream.write("\n")
        self.stream.flush()
        return result

    def stepMonkey(self) -> str:
        """
        send a step monkey request to the server and get the xml string.
        """
        block_dict = self._getBlockedWidgets()
        block_widgets: List[str] = block_dict['widgets']
        block_trees: List[str] = block_dict['trees']
        URL = f"http://localhost:{self.scriptDriver.lport}/stepMonkey"
        logger.debug(f"Sending request: {URL}")
        logger.debug(f"Blocking widgets: {block_widgets}")
        logger.debug(f"Blocking trees: {block_trees}")
        r = requests.post(
            url=URL,
            json={
                "steps_count": self.stepsCount,
                "block_widgets": block_widgets,
                "block_trees": block_trees
            }
        )

        res = json.loads(r.content)
        xml_raw = res["result"]
        return xml_raw

    def stopMonkey(self) -> str:
        """
        send a stop monkey request to the server and get the xml string.
        """
        URL = f"http://localhost:{self.scriptDriver.lport}/stopMonkey"
        logger.debug(f"Sending request: {URL}")
        r = requests.get(URL)

        res = r.content.decode(encoding="utf-8")
        print(f"[Server INFO] {res}", flush=True)

    def getValidProperties(self, xml_raw: str, result: JsonResult) -> PropertyStore:

        staticCheckerDriver = self.options.Driver.getStaticChecker(hierarchy=xml_raw)

        validProps: PropertyStore = dict()
        for propName, test in self.allProperties.items():
            valid = True
            prop = getattr(test, propName)
            # check if all preconds passed
            for precond in prop.preconds:
                # Dependency injection. Static driver checker for precond
                setattr(test, self.options.driverName, staticCheckerDriver)
                # excecute the precond
                try:
                    if not precond(test):
                        valid = False
                        break
                except Exception as e:
                    print(f"[ERROR] Error when checking precond: {getFullPropName(test)}", flush=True)
                    traceback.print_exc()
                    valid = False
                    break
            # if all the precond passed. make it the candidate prop.
            if valid:
                logger.debug(f"precond satisfied: {getFullPropName(test)}")
                if result.getExcuted(test) >= getattr(prop, MAX_TRIES_MARKER, float("inf")):
                    logger.debug(f"{getFullPropName(test)} has reached its max_tries. Skip.")
                    continue
                validProps[propName] = test
        return validProps

    def _logScript(self, execution_info:Dict):
        URL = f"http://localhost:{self.scriptDriver.lport}/logScript"
        r = requests.post(
            url=URL,
            json=execution_info
        )
        res = r.content.decode(encoding="utf-8")
        if res != "OK":
            print(f"[ERROR] Error when logging script: {execution_info}", flush=True)

    def _init(self):
        URL = f"http://localhost:{self.scriptDriver.lport}/init"
        data = {
            "takeScreenshots": self.options.take_screenshots,
            "logStamp": STAMP
        }
        print(f"[INFO] Init fastbot: {data}", flush=True)
        r = requests.post(
            url=URL,
            json=data
        )
        res = r.content.decode(encoding="utf-8")
        import re
        device_output_dir = re.match(r"outputDir:(.+)", res).group(1)
        print(f"[INFO] Fastbot initiated. Device outputDir: {res}", flush=True)
        # 保存设备输出目录路径以便之后使用
        self.device_output_dir = device_output_dir
        
        # 启动数据同步线程
        self._start_sync_thread()
        
    def _start_sync_thread(self):
        """
        启动数据同步线程，定期从设备拉取测试数据
        """
        if self._sync_thread is not None and self._sync_thread.is_alive():
            print("[WARNING] Sync thread is already running", flush=True)
            return
            
        self._sync_stop_event = threading.Event()
        self._sync_thread = threading.Thread(
            target=self._sync_data_from_device,
            daemon=True
        )
        self._sync_thread.start()
        print("[INFO] Data sync thread started", flush=True)
        
    def _stop_sync_thread(self):
        """
        停止数据同步线程
        """
        if self._sync_thread is not None and self._sync_thread.is_alive():
            print("[INFO] Stopping data sync thread...", flush=True)
            self._sync_stop_event.set()
            self._sync_thread.join(timeout=5)
            if self._sync_thread.is_alive():
                print("[WARNING] Sync thread did not terminate gracefully", flush=True)
            else:
                print("[INFO] Data sync thread stopped", flush=True)
                
    def _sync_data_from_device(self):
        """
        数据同步线程函数，定期从设备拉取数据并删除已拉取的数据
        每个profile_period来进行一次数据的拉取，特别处理screenshots目录
        """
        if not hasattr(self, 'device_output_dir') or not self.device_output_dir:
            print("[ERROR] Device output directory not found. Cannot start sync thread.", flush=True)
            return
            
        local_output_dir = Path(self.options.output_dir).absolute()
        local_output_dir.mkdir(parents=True, exist_ok=True)
        
        # 创建专门用于保存截图的目录
        screenshots_dir = local_output_dir / "screenshots"
        screenshots_dir.mkdir(parents=True, exist_ok=True)
        
        # 记录已拉取的文件列表
        synced_files = set()
        synced_screenshots = set()
        
        # 使用profile_period作为同步间隔的基础值
        # 将秒转换为一个合理的间隔，最小10秒，最大60秒
        sync_interval = min(max(self.options.profile_period * 0.2, 10), 60)
        print(f"[INFO] Data sync interval set to {sync_interval} seconds based on profile_period", flush=True)
        
        while not self._sync_stop_event.is_set():
            try:
                # 1. 先处理常规文件
                list_cmd = ["-s", self.options.serial, "shell", "find", self.device_output_dir, "-type", "f", "-not", "-path", f"{self.device_output_dir}/screenshots/*"]
                result = run_adb_command(list_cmd)
                
                if result and not result.startswith("Error:"):
                    device_files = [f.strip() for f in result.splitlines() if f.strip()]
                    
                    # 过滤出未拉取的文件
                    new_files = [f for f in device_files if f not in synced_files]
                    
                    if new_files:
                        print(f"[INFO] Found {len(new_files)} new files to sync", flush=True)
                        
                        for file_path in new_files:
                            # 确保本地目录结构与设备上一致
                            rel_path = os.path.relpath(file_path, self.device_output_dir)
                            local_file_dir = os.path.dirname(os.path.join(local_output_dir, rel_path))
                            os.makedirs(local_file_dir, exist_ok=True)
                            
                            # 拉取文件
                            pull_result = run_adb_command([
                                "-s", self.options.serial, "pull", 
                                file_path, os.path.join(local_output_dir, rel_path)
                            ])
                            
                            if pull_result and pull_result.startswith("Error:"):
                                print(f"[WARNING] Failed to pull file {file_path}: {pull_result}", flush=True)
                                continue
                                
                            # 删除已拉取的文件
                            delete_result = run_adb_command([
                                "-s", self.options.serial, "shell",
                                "rm", file_path
                            ])
                            
                            if delete_result and delete_result.startswith("Error:"):
                                print(f"[WARNING] Failed to delete file {file_path}: {delete_result}", flush=True)
                                continue
                                
                            synced_files.add(file_path)
                            print(f"[INFO] Synced and deleted file: {rel_path}", flush=True)
                
                # 2. 处理screenshots目录
                list_screenshots_cmd = ["-s", self.options.serial, "shell", "find", f"{self.device_output_dir}/screenshots", "-type", "f", "-name", "*.png"]
                screenshots_result = run_adb_command(list_screenshots_cmd)
                
                if screenshots_result and not screenshots_result.startswith("Error:"):
                    device_screenshots = [f.strip() for f in screenshots_result.splitlines() if f.strip()]
                    
                    # 过滤出未拉取的截图
                    new_screenshots = [f for f in device_screenshots if f not in synced_screenshots]
                    
                    if new_screenshots:
                        print(f"[INFO] Found {len(new_screenshots)} new screenshots to sync", flush=True)
                        
                        for screenshot_path in new_screenshots:
                            # 获取截图文件名
                            screenshot_name = os.path.basename(screenshot_path)
                            local_screenshot_path = os.path.join(screenshots_dir, screenshot_name)
                            
                            # 拉取截图
                            pull_result = run_adb_command([
                                "-s", self.options.serial, "pull", 
                                screenshot_path, local_screenshot_path
                            ])
                            
                            if pull_result and pull_result.startswith("Error:"):
                                print(f"[WARNING] Failed to pull screenshot {screenshot_path}: {pull_result}", flush=True)
                                continue
                                
                            # 删除已拉取的截图
                            delete_result = run_adb_command([
                                "-s", self.options.serial, "shell",
                                "rm", screenshot_path
                            ])
                            
                            if delete_result and delete_result.startswith("Error:"):
                                print(f"[WARNING] Failed to delete screenshot {screenshot_path}: {delete_result}", flush=True)
                                continue
                                
                            synced_screenshots.add(screenshot_path)
                            print(f"[INFO] Synced and deleted screenshot: {screenshot_name}", flush=True)
                
            except Exception as e:
                print(f"[ERROR] Error in sync thread: {str(e)}", flush=True)
                traceback.print_exc()
                
            time.sleep(sync_interval)
            
        print("[INFO] Sync thread exiting", flush=True)

    def collectAllProperties(self, test: TestSuite):
        """collect all the properties to prepare for PBT
        """

        def remove_setUp(testCase: TestCase):
            """remove the setup function in PBT
            """
            def setUp(self): ...
            testCase.setUp = types.MethodType(setUp, testCase)

        def remove_tearDown(testCase: TestCase):
            """remove the tearDown function in PBT
            """
            def tearDown(self): ...
            testCase.tearDown = types.MethodType(tearDown, testCase)
        
        def iter_tests(suite):
            for test in suite:
                if isinstance(test, TestSuite):
                    yield from iter_tests(test)
                else:
                    yield test

        # Traverse the TestCase to get all properties
        for t in iter_tests(test):
            testMethodName = t._testMethodName
            # get the test method name and check if it's a property
            testMethod = getattr(t, testMethodName)
            if hasattr(testMethod, PRECONDITIONS_MARKER):
                # remove the hook func in its TestCase
                remove_setUp(t)
                remove_tearDown(t)
                # save it into allProperties for PBT
                self.allProperties[testMethodName] = t
                print(f"[INFO] Load property: {getFullPropName(t)}", flush=True)

    @property
    def _blockWidgetFuncs(self):
        """
        load and process blocking functions from widget.block.py configuration file.

        Returns:
            dict: A dictionary containing two lists:
                - 'widgets': List of functions that block individual widgets
                - 'trees': List of functions that block widget trees
        """
        if self._block_funcs is None:
            self._block_funcs = {"widgets": list(), "trees": list()}
            root_dir = getProjectRoot()
            if root_dir is None or not os.path.exists(
                    file_block_widgets := root_dir / "configs" / "widget.block.py"
            ):
                print(f"[WARNING] widget.block.py not find", flush=True)

            def __get_block_widgets_module():
                import importlib.util
                module_name = "block_widgets"
                spec = importlib.util.spec_from_file_location(module_name, file_block_widgets)
                mod = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(mod)
                return mod

            mod = __get_block_widgets_module()

            import inspect
            for func_name, func in inspect.getmembers(mod, inspect.isfunction):
                if func_name == "global_block_widgets":
                    self._block_funcs["widgets"].append(func)
                    setattr(func, PRECONDITIONS_MARKER, (lambda d: True,))
                    continue
                if func_name == "global_block_tree":
                    self._block_funcs["trees"].append(func)
                    setattr(func, PRECONDITIONS_MARKER, (lambda d: True,))
                    continue
                if func_name.startswith("block_") and not func_name.startswith("block_tree_"):
                    if getattr(func, PRECONDITIONS_MARKER, None) is None:
                        logger.warning(f"No precondition in block widget function: {func_name}. Default globally active.")
                        setattr(func, PRECONDITIONS_MARKER, (lambda d: True,))
                    self._block_funcs["widgets"].append(func)
                    continue
                if func_name.startswith("block_tree_"):
                    if getattr(func, PRECONDITIONS_MARKER, None) is None:
                        logger.warning(f"No precondition in block tree function: {func_name}. Default globally active.")
                        setattr(func, PRECONDITIONS_MARKER, (lambda d: True,))
                    self._block_funcs["trees"].append(func)

        return self._block_funcs


    def _getBlockedWidgets(self):
        """
           Executes all blocking functions to get lists of widgets and trees to be blocked during testing.

           Returns:
               dict: A dictionary containing:
                   - 'widgets': List of XPath strings for individual widgets to block
                   - 'trees': List of XPath strings for widget trees to block
           """
        def _get_xpath_widgets(func):
            blocked_set = set()
            try:
                script_driver = self.options.Driver.getScriptDriver()
                preconds = getattr(func, PRECONDITIONS_MARKER, [])
                if all(precond(script_driver) for precond in preconds):
                    _widgets = func(self.options.Driver.getStaticChecker())
                    _widgets = _widgets if isinstance(_widgets, list) else [_widgets]
                    for w in _widgets:
                        if isinstance(w, StaticU2UiObject):
                            xpath = selector_to_xpath(w.selector, True)
                            blocked_set.add(xpath)
                        elif isinstance(w, u2.xpath.XPathSelector):
                            xpath = w._parent.xpath
                            blocked_set.add(xpath)
                        else:
                            logger.warning(f"{w} Not supported")
            except Exception as e:
                logger.error(f"Error processing blocked widgets: {e}")
                traceback.print_exc()
            return blocked_set

        res = {
            "widgets": set(),
            "trees": set()
        }


        for func in self._blockWidgetFuncs["widgets"]:
            widgets = _get_xpath_widgets(func)
            res["widgets"].update(widgets)


        for func in self._blockWidgetFuncs["trees"]:
            trees = _get_xpath_widgets(func)
            res["trees"].update(trees)


        res["widgets"] = list(res["widgets"] - res["trees"])
        res["trees"] = list(res["trees"])

        return res


    def __del__(self):
        """tearDown method. Cleanup the env.
        """
        # 确保停止同步线程
        self._stop_sync_thread()
        
        if self.options.Driver:
            self.options.Driver.tearDown()

    def pull_test_results(self):
        """
        从设备拉取测试结果到本地output目录
        
        将设备中的测试结果文件夹(由_init方法获取的device_output_dir)拉取到本地的output目录中，
        并删除设备上已经拉取的数据
        
        Returns:
            str: 操作结果信息
        """
        if not hasattr(self, 'device_output_dir') or not self.device_output_dir:
            print("[ERROR] Device output directory not found. Was _init() called?", flush=True)
            return "Error: Device output directory not found"
        
        # 确保输出目录存在
        output_dir = Path(self.options.output_dir).absolute()
        output_dir.mkdir(parents=True, exist_ok=True)
        
        # 确保截图目录存在
        screenshots_dir = output_dir / "screenshots"
        screenshots_dir.mkdir(parents=True, exist_ok=True)
        
        # 检查设备上是否还有screenshots目录
        check_screenshots_cmd = ["-s", self.options.serial, "shell", "ls", f"{self.device_output_dir}/screenshots"]
        check_result = run_adb_command(check_screenshots_cmd)
        has_screenshots = check_result and not check_result.startswith("No such file") and not check_result.startswith("Error")
        
        # 从设备拉取普通文件
        print(f"[INFO] Pulling test results from {self.device_output_dir} to {output_dir}", flush=True)
        result = pull_directory(self.device_output_dir, str(output_dir), device=self.options.serial)
        
        # 如果有截图目录，单独处理
        if has_screenshots:
            print(f"[INFO] Pulling screenshots to {screenshots_dir}", flush=True)
            # 单独拉取截图目录中的文件到专门的screenshots目录
            screenshots_pull_cmd = ["-s", self.options.serial, "pull", f"{self.device_output_dir}/screenshots/", str(screenshots_dir)]
            screenshots_result = run_adb_command(screenshots_pull_cmd)
            
            if screenshots_result and screenshots_result.startswith("Error"):
                print(f"[WARNING] Failed to pull screenshots: {screenshots_result}", flush=True)
        
        if result and not result.startswith("Error:"):
            print(f"[INFO] Test results successfully pulled to {output_dir}", flush=True)
            
            # 删除设备上已拉取的数据
            delete_result = run_adb_command([
                "-s", self.options.serial, "shell",
                "rm", "-rf", f"{self.device_output_dir}/*"
            ])
            
            if delete_result and delete_result.startswith("Error:"):
                print(f"[WARNING] Failed to delete device data: {delete_result}", flush=True)
                return f"Warning: Test results pulled but failed to delete device data: {delete_result}"
            else:
                print(f"[INFO] Device data deleted successfully", flush=True)
                return f"Success: Test results pulled to {output_dir} and device data deleted"
        else:
            print(f"[ERROR] Failed to pull test results: {result}", flush=True)
            return f"Error: {result}"
