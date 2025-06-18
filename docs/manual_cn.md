# 文档

[中文文档](docs/manual_enh.md)

## Kea2 教程

1. 关于如何在 [WeChat](docs/Scenario_Examples_zh.md) 上应用 Kea2 的功能 2 和 3 的小教程。

## Kea2 脚本

Kea2 使用 [Unittest](https://docs.python.org/3/library/unittest.html) 来管理脚本。所有 Kea2 的脚本都遵循 unittest 规则（即测试方法应以 `test_` 开头，测试类应继承 `unittest.TestCase`）。

Kea2 使用 [Uiautomator2](https://github.com/openatx/uiautomator2) 操作 Android 设备。详细请参考 [Uiautomator2 的文档](https://github.com/openatx/uiautomator2?tab=readme-ov-file#quick-start)。

基本上，您可以通过以下两个步骤编写 Kea2 脚本：

1. 创建一个继承自 `unittest.TestCase` 的测试类。

```python
import unittest

class MyFirstTest(unittest.TestCase):
    ...
```

2. 通过定义测试方法编写您的脚本。

默认情况下，只有以 `test_` 开头的测试方法会被 unittest 发现。您可以用 `@precondition` 装饰器修饰函数。装饰器 `@precondition` 接受一个返回布尔值的函数作为参数。当该函数返回 `True`，前置条件满足，脚本将被激活，Kea2 会根据装饰器 `@prob` 定义的概率运行该脚本。

注意如果测试方法没有使用 `@precondition` 装饰，该测试方法在自动化 UI 测试中不会被激活，会被当作普通的 `unittest` 测试方法。因此，当测试方法始终需要执行时，您需要显式指定 `@precondition(lambda self: True)`。如果测试方法没有装饰 `@prob`，默认概率为 1（当前置条件满足时总是执行）。

```python
import unittest
from kea2 import precondition

class MyFirstTest(unittest.TestCase):

    @prob(0.7)
    @precondition(lambda self: ...)
    def test_func1(self):
        ...
```

您可以阅读 [Kea - Write your first property](https://kea-docs.readthedocs.io/en/latest/part-keaUserManuel/first_property.html) 获取更多详情。

## 装饰器

### `@precondition`

```python
@precondition(lambda self: ...)
def test_func1(self):
    ...
```

装饰器 `@precondition` 接受一个返回布尔值的函数作为参数。当该函数返回 `True`，前置条件被满足，函数 `test_func1` 将被激活，且 Kea2 会根据装饰器 `@prob` 指定的概率执行 `test_func1`。如果未指定 `@prob`，默认概率为 1，此时当前置条件满足时 `test_func1` 会始终执行。

### `@prob`

```python
@prob(0.7)
@precondition(lambda self: ...)
def test_func1(self):
    ...
```

装饰器 `@prob` 接受一个浮点数作为参数。该数表示当前置条件（由 `@precondition` 指定）满足时执行函数 `test_func1` 的概率，取值范围在 0 到 1 之间。如果未指定 `@prob`，默认概率为 1，函数会始终执行。

当多个函数的前置条件均满足时，Kea2 会基于它们的概率值随机选择其中一个函数执行。

具体来说，Kea2 会生成一个在 0 到 1 之间的随机值 `p`，并基于这些函数的概率值决定执行哪个函数。

例如，如果三个函数 `test_func1`、`test_func2` 与 `test_func3` 的前置条件均被满足，它们的概率值分别为 `0.2`、`0.4` 和 `0.6`：

- 情况 1：如果 `p` 随机赋值为 `0.3`，`test_func1` 因概率值 `0.2` 小于 `p` 将不会被选中，Kea2 会在 `test_func2` 和 `test_func3` 中 *随机* 选择一个执行。
- 情况 2：如果 `p` 随机赋值为 `0.1`，Kea2 会在 `test_func1`、`test_func2` 和 `test_func3` 中 *随机* 选择一个执行。
- 情况 3：如果 `p` 随机赋值为 `0.7`，Kea2 会忽略这三个函数 `test_func1`、`test_func2` 和 `test_func3`。

### `@max_tries`

```python
@max_tries(1)
@precondition(lambda self: ...)
def test_func1(self):
    ...
```

装饰器 `@max_tries` 接受一个整数作为参数，表示当前置条件满足时函数 `test_func1` 最大执行次数。默认值为 `inf`（无限次）。

## 启动 Kea2

我们提供两种方式启动 Kea2。

### 1. 通过 shell 命令启动

Kea2 与 `unittest` 框架兼容。您可以以 unittest 风格管理测试用例。可以使用 `kea2 run` 命令加上驱动参数和子命令 `unittest`（用于 unittest 选项）启动 Kea2。

Shell 命令格式：
```
kea2 run <Kea2 指令> unittest <unittest 指令> 
```

示例 shell 命令：

```bash
# 启动 Kea2 并加载单个脚本 quicktest.py
kea2 run -s "emulator-5554" -p it.feio.android.omninotes.alpha --agent u2 --running-minutes 10 --throttle 200 --driver-name d unittest discover -p quicktest.py

# 启动 Kea2 并从目录 mytests/omni_notes 加载多个脚本
kea2 run -s "emulator-5554" -p it.feio.android.omninotes.alpha --agent u2 --running-minutes 10 --throttle 200 --driver-name d unittest discover -s mytests/omni_notes -p test*.py
```

### `kea2 run` 参数

| 参数 | 含义 | 默认值 | 
| --- | --- | --- |
| -s | 设备序列号，可通过 `adb devices` 获取 | |
| -p | 被测应用的包名 (例如 com.example.app) | |
| -o | 日志和结果的输出目录 | `output` |
| --agent | 取值 {native, u2}。默认使用 `u2`，支持 Kea2 的三个重要功能。如果想运行原生 Fastbot，请使用 `native`。| `u2` |
| --running-minutes | 运行 Kea2 的时长（分钟） | `10` |
| --max-step | 发送的猴子事件最大数（仅 `--agent u2` 可用） | `inf`（无限） |
| --throttle | 两个猴子事件之间的延迟时间（毫秒） | `200` |
| --driver-name | 在 kea2 脚本中使用的驱动名称。如果指定为 `--driver-name d`，则应通过 `d` 来与设备交互，如 `self.d(..).click()`。 | |
| --log-stamp | 日志文件与结果文件的标记（例如指定 `--log-stamp 123`，日志文件名将为 `fastbot_123.log`，结果文件为 `result_123.json`） | 当前时间戳 |
| --profile-period | 覆盖率和 UI 截图采集周期（以猴子事件数计）。UI 截图存储于设备 SD 卡，需根据设备存储容量合理设置。 | `25` |
| --take-screenshots | 每个猴子事件时截取 UI 截图，并定期自动从手机拉取到主机（周期由 `--profile-period` 指定）。 | |
| unittest | 指定要加载的脚本。子命令 `unittest` 完全兼容 unittest，更多参数见 `python3 -m unittest -h`。仅 `--agent u2` 可用。 | |

### `kea` 参数

| 参数 | 含义 | 默认值 | 
| --- | --- | --- |
| -d | 启用调试模式 | |

> ```bash
> # 添加 -d 启用调试模式
> kea2 -d run -s "emulator-5554" -p it.feio.android.omninotes.alpha --agent u2 --running-minutes 10 --throttle 200 --driver-name d unittest discover -p quicktest.py
> ```

### 2. 通过 `unittest.main` 启动

与 unittest 类似，我们可以通过调用 `unittest.main` 方法启动 Kea2。

示例（文件名 `mytest.py`），选项直接在脚本中定义：

```python
import unittest

from kea2 import KeaTestRunner, Options
from kea2.u2Driver import U2Driver

class MyTest(unittest.TestCase):
    ...
    # <你的测试方法>

if __name__ == "__main__":
    KeaTestRunner.setOptions(
        Options(
            driverName="d",
            Driver=U2Driver,
            packageNames=[PACKAGE_NAME],
            # serial="emulator-5554",   # 指定序列号
            maxStep=100,
            # running_mins=10,  # 指定最大运行时间（分钟），默认 10 分钟
            # throttle=200,     # 指定事件间隔（毫秒），默认 200 毫秒
            # agent='native'    # 原生 Fastbot 使用 'native'
        )
    )
    # 声明 KeaTestRunner
    unittest.main(testRunner=KeaTestRunner)
```

通过运行脚本即可启动 Kea2，如：

```python
python3 mytest.py
```

`Options` 里的所有可用选项：

```python
# 脚本里的 driver 名称（例如 self.d，则是 d）
driverName: str
# 驱动（目前仅支持 U2Driver）
Driver: U2Driver
# 被测应用包名列表
packageNames: List[str]
# 目标设备序列号
serial: str = None
# 测试代理。默认是 "u2"
agent: "u2" | "native" = "u2"
# 探索的最大步数（阶段 2~3 可用）
maxStep: int # 默认 "inf"
# 探索时间（分钟）
running_mins: int = 10
# 探索时等待间隔（毫秒）
throttle: int = 200
# 日志和结果输出目录
output_dir: str = "output"
# 日志及结果文件标记，默认当前时间戳
log_stamp: str = None
# 覆盖率统计周期
profile_period: int = 25
# 每步是否截屏
take_screenshots: bool = False
# 是否启用调试模式
debug: bool = False
```

## 查看脚本运行统计信息

如果想查看脚本是否被执行或者执行了多少次，测试结束后打开文件 `result.json`。

示例：

```json
{
    "test_goToPrivacy": {
        "precond_satisfied": 8,
        "executed": 2,
        "fail": 0,
        "error": 1
    },
    ...
}
```

**如何阅读 `result.json`**

字段 | 说明 | 含义
--- | --- | --- |
precond_satisfied | 在探索过程中，测试方法的前置条件满足次数 | 表示是否达到该状态 |
executed | UI 测试中测试方法的执行次数 | 是否执行过该测试方法 |
fail | 测试方法断言失败的次数 | 失败时，测试方法很可能发现了一个功能性缺陷 |
error | 测试方法在 UI 测试中因意外错误中断的次数（例如测试用到的 UI 控件无法找到） | 发生错误时，脚本需更新修复，以避免意外错误 |

## 配置文件

执行 `Kea2 init` 后，会在 `configs` 目录生成一些配置文件。

这些配置文件属于 `Fastbot`，具体说明见 [配置文件介绍](https://github.com/bytedance/Fastbot_Android/blob/main/handbook-cn.md#%E4%B8%93%E5%AE%B6%E7%B3%BB%E7%BB%9F)。

## 应用崩溃缺陷

Kea2 会将触发的崩溃缺陷记录在指定输出目录（通过 `-o` 指定）下的 `fastbot_*.log` 文件中。

您可在 `fastbot_*.log` 中搜索关键词 `FATAL EXCEPTION` 来查找崩溃缺陷的具体信息。

这些崩溃缺陷也会被设备记录。详见 [Fastbot 手册](https://github.com/bytedance/Fastbot_Android/blob/main/handbook-cn.md#%E7%BB%93%E6%9E%9C%E8%AF%B4%E6%98%8E)。