import json
from pathlib import Path
import subprocess
from typing import Callable, Any, Dict, List
from unittest import TextTestRunner, registerResult, TestSuite, TestCase
import random
import warnings
from xml.etree import ElementTree
from dataclasses import dataclass
import requests
from .absDriver import AbstractDriver
from functools import wraps
from time import sleep
from .adbUtils import push_file, run_adb_command
import types
PRECONDITIONS_MARKER = "preconds"
PROP_MARKER = "prop"


def precondition(precond: Callable[[Any], bool]) -> Callable:
    """the decorator @precondition

    The precondition specifies when the property could be executed.
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

    The prob specify the propbability of execution when a property is satisfied.
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


@dataclass
class Options:
    driverName: str
    Driver: AbstractDriver
    packageNames: List[str]
    maxStep: int = 500


class KeaTestRunner(TextTestRunner):

    options: Options = None

    @classmethod
    def setOptions(cls, options: Options):
        if not isinstance(options.packageNames, list) and len(options.packageNames) > 0:
            raise ValueError("packageNames should be given in a list.")
        cls.options = options

    def run(self, test):

        result = self._makeResult()
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

            # setUp for the u2 driver
            self.scriptDriver = self.options.Driver.getScriptDriver()
            # self.activateFastbot()
            self.allProperties = dict()
            self.collectAllProperties(test)

            if len(self.allProperties) == 0:
                print("No property has been found, terminated.")
                return

            for step in range(self.options.maxStep):
                print("sending monkeyEvent (%d/%d)" % (step+1, self.options.maxStep))
                propsSatisfiedPrecond = self.getValidProperties()
                print(f"{len(propsSatisfiedPrecond)} precond satisfied.")
                if propsSatisfiedPrecond:
                    p = random.random()
                    propsNameFilteredByP = [
                        propName for propName, func in propsSatisfiedPrecond.items()
                        if getattr(func, "p", 0.5) >= p
                    ]

                    if len(propsNameFilteredByP) == 0:
                        print("Not executed any property due to probability.")
                        continue
                    execPropName = random.choice(propsNameFilteredByP)
                    test = propsSatisfiedPrecond[execPropName]
                    # Dependency Injection. driver when doing scripts
                    self.scriptDriver = self.options.Driver.getScriptDriver()
                    setattr(test, self.options.driverName, self.scriptDriver)
                    print("execute property %s." % execPropName)

                    try:
                        test(result)
                    finally:
                        result.printErrors()
            print(f"finish sending {self.options.maxStep} events.")

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

    def activateFastbot(self):
        cur_dir = Path(__file__).parent
        push_file(Path.joinpath(cur_dir, "assets/monkeyq.jar"), "/sdcard/monkeyq.jar")
        push_file(Path.joinpath(cur_dir, "assets/fastbot-thirdpart.jar"), "/sdcard/fastbot-thirdpart.jar")
        push_file(Path.joinpath(cur_dir, "assets/framework.jar"), "/sdcard/framework.jar")
        push_file(Path.joinpath(cur_dir, "assets/fastbot_libs/arm64-v8a"), "/data/local/tmp")
        push_file(Path.joinpath(cur_dir, "assets/fastbot_libs/armeabi-v7a"), "/data/local/tmp")
        push_file(Path.joinpath(cur_dir, "assets/fastbot_libs/x86"), "/data/local/tmp")
        push_file(Path.joinpath(cur_dir, "assets/fastbot_libs/x86_64"), "/data/local/tmp")

        self.startFastbotService()

        for i in range(10):
            sleep(1)
            try:
                r=requests.get(f"http://localhost:{self.scriptDriver.port}/ping")
                return
            except requests.ConnectionError:
                pass
        raise RuntimeError("Failed to connect fastbot")

    def startFastbotService(self):
        command = [
            "adb",
            "shell",
            "CLASSPATH=/sdcard/monkeyq.jar:/sdcard/framework.jar:/sdcard/fastbot-thirdpart.jar",
            "exec", "app_process",
            "/system/bin", "com.android.commands.monkey.Monkey",
            "-p", *self.options.packageNames,
            "--agent-u2", "reuseq", "--running-minutes", "100", "--throttle", "200", "-v", "-v", "-v"
        ]

        # log file
        outfile = open("fastbot.log", "w")

        process = subprocess.Popen(command, stdout=outfile, stderr=outfile)

        # 如果在程序中后续需要访问进程句柄，可以返回 process 对象
        return process

    def stepMonkey(self) -> ElementTree:
        r = requests.get(f"http://localhost:{self.scriptDriver.port}/stepMonkey")

        res = json.loads(r.content)
        with open("temp.xml", "w") as fp:
            fp.write(res["result"])
        tree = ElementTree.parse("temp.xml")
        return tree

    def getValidProperties(self) -> Dict[str, TestSuite]:

        xmlTree = self.stepMonkey()
        staticCheckerDriver = self.options.Driver.getStaticChecker(hierarchy=xmlTree)

        validProps = dict()
        for propName, testSuite in self.allProperties.items():
            valid = True
            prop = getattr(testSuite, propName)
            # check if all preconds passed
            for precond in prop.preconds:
                # Dependency injection. Static driver checker for precond
                setattr(testSuite, self.options.driverName, staticCheckerDriver)
                # excecute the precond
                if not precond(testSuite):
                    valid = False
                    break
            # if all the precond passed. make it the candidate prop.
            if valid:
                validProps[propName] = testSuite
        return validProps

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
            testCase = types.MethodType(tearDown, testCase)

        for subtest in test._tests:
            # subtest._tests: List["TestSuite"]
            for _testCaseClass in subtest._tests:
                if isinstance(_testCaseClass, TestSuite):
                    self.collectAllProperties(_testCaseClass._tests)
                testMethodName = _testCaseClass._testMethodName
                testMethod = getattr(_testCaseClass, testMethodName)
                if hasattr(testMethod, PRECONDITIONS_MARKER):
                    self.allProperties[testMethodName] = _testCaseClass
                    remove_setUp(_testCaseClass)
                    remove_tearDown(_testCaseClass)
