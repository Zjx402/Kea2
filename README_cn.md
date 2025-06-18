[![PyPI](https://img.shields.io/pypi/v/kea2-python.svg)](https://pypi.python.org/pypi/kea2-python)
[![PyPI Downloads](https://static.pepy.tech/badge/kea2-python)](https://pepy.tech/projects/kea2-python)
![Python](https://img.shields.io/badge/python-3.8%2B-blue)

<div>
    <img src="https://github.com/user-attachments/assets/1a64635b-a8f2-40f1-8f16-55e47b1d74e7" style="border-radius: 14px; width: 20%; height: 20%;"/> 
</div>

[中文文档](README_cn.md)

## 关于

Kea2 是一个易于使用的 Python 库，支持、定制和改进手机应用的自动化 UI 测试。Kea2 的创新之处在于能够融合人工编写的脚本与自动化 UI 测试工具，从而实现许多有趣且强大的功能。

Kea2 当前基于 [Fastbot](https://github.com/bytedance/Fastbot_Android) 和 [uiautomator2](https://github.com/openatx/uiautomator2) 构建，目标是针对 [Android](https://en.wikipedia.org/wiki/Android_(operating_system)) 应用。

## 重要特性
- **特性 1**(查找稳定性问题)：具备[Fastbot](https://github.com/bytedance/Fastbot_Android)的全部能力进行压力测试及查找*稳定性问题*（即*崩溃缺陷*）；

- **特性 2**(自定义测试场景\事件序列\黑白名单\黑白控件[^1])：在运行 Fastbot 时自定义测试场景（如测试特定应用功能、执行特定事件序列、进入特定 UI 页面、达到特定应用状态、黑名单特定活动/UI 控件/UI 区域），由 *python* 语言和 [uiautomator2](https://github.com/openatx/uiautomator2) 强大灵活的能力支持；

- **特性 3**(支持断言机制[^2])：基于继承自 [Kea](https://github.com/ecnusse/Kea) 的[基于性质的测试](https://en.wikipedia.org/wiki/Software_testing#Property_testing)思想，运行 Fastbot 时支持自动断言，以发现*逻辑错误*（即*非崩溃缺陷*）。

**Kea2 三大特性的能力对比**
|  | **特性 1** | **特性 2** | **特性 3** |
| --- | --- | --- | ---- |
| **发现崩溃** | :+1: | :+1: | :+1: |
| **深层状态发现崩溃** |  | :+1: | :+1: |
| **发现非崩溃功能（逻辑）缺陷** |  |  | :+1: |


<div align="center">
    <div style="max-width:80%; max-height:80%">
    <img src="docs/intro.png" style="border-radius: 14px; width: 80%; height: 80%;"/> 
    </div>
</div>



## 设计与路线图
Kea2 作为一个 Python 库发布，目前配合使用：
- 以 [unittest](https://docs.python.org/3/library/unittest.html) 作为测试框架；
- 以 [uiautomator2](https://github.com/openatx/uiautomator2) 作为 UI 测试驱动；
- 以 [Fastbot](https://github.com/bytedance/Fastbot_Android) 作为后端自动化 UI 测试工具。

未来，Kea2 将扩展支持：
- [pytest](https://docs.pytest.org/en/stable/)
- [Appium](https://github.com/appium/appium)、[Hypium](https://developer.huawei.com/consumer/cn/doc/harmonyos-guides/hypium-python-guidelines)（面向 HarmonyOS/Open Harmony）
- 以及其它自动化 UI 测试工具（不限于 Fastbot）


## 安装

运行环境：
- 支持 Windows、MacOS 和 Linux
- python 3.8+，Android 4.4+（已安装 Android SDK）
- **关闭 VPN**（特性 2 和 3 需要）

通过 `pip` 安装 Kea2：
```bash
python3 -m pip install kea2-python
```

通过运行以下命令查看 Kea2 的选项：
```bash
kea2 -h
```

## 快速测试

Kea2 连接并运行于 Android 设备。推荐您做快速测试以确保 Kea2 与您的设备兼容。

1. 连接一台真实 Android 设备或 Android 模拟器（一个设备即可），确认通过执行 `adb devices` 能看到连接设备。

2. 运行 `quicktest.py` 来测试示例应用 `omninotes`（该应用以 `omninotes.apk` 形式发布于 Kea2 仓库中）。该脚本会自动安装并短时间测试此示例应用。

在您喜欢的工作目录下初始化 Kea2：
```python
kea2 init
```

> 如果您是首次使用 Kea2，此步骤必须执行。

运行快速测试：
```python
python3 quicktest.py
```

若能看到 `omninotes` 应用成功运行并被测试，说明 Kea2 工作正常！
否则，请帮忙 [提交 Bug 报告](https://github.com/ecnusse/Kea2/issues) 并附上错误信息。感谢支持！



## 特性 1(运行基础版Fastbot：查找稳定性错误)

使用完整的 Fastbot 能力对您的应用进行压力测试，查找*稳定性问题*（即*崩溃缺陷*）；

```bash
kea2 run -s "emulator-5554" -p it.feio.android.omninotes.alpha --agent native --running-minutes 10 --throttle 200
```

有关上述选项含义请查阅[文档](docs/manual_en.md#launching-kea2)

> 用法类似于原始 Fastbot 的 [shell 命令](https://github.com/bytedance/Fastbot_Android?tab=readme-ov-file#run-fastbot-with-shell-command)。

更多选项请查看：
```bash
kea2 run -h
```

## 特性 2(运行增强版Fastbot：自定义测试场景\事件序列\黑白控件)

在运行 Fastbot 等自动化 UI 测试工具时，您可能发现某些特定 UI 页面或功能难以到达或覆盖。原因在于 Fastbot 对您的应用了解不足。幸运的是，脚本化测试在这方面优势明显。特性 2 中，Kea2 支持编写小脚本来指导 Fastbot 探索任意位置，也可使用脚本屏蔽特定控件。

在 Kea2 中，一个脚本由两个元素组成：
-  **前置条件（Precondition）：** 何时执行脚本。
- **交互场景（Interaction scenario）：** 脚本的测试方法中指定的交互逻辑，用于达到目标页面或状态。

### 简单示例

假设 `Privacy` 是自动化 UI 测试中较难到达的页面。Kea2 可轻松指导 Fastbot 到达此页面。

```python
    @prob(0.5)
    # precondition: when we are at the page `Home`
    @precondition(lambda self: 
        self.d(text="Home").exists
    )
    def test_goToPrivacy(self):
        """
        Guide Fastbot to the page `Privacy` by opening `Drawer`, 
        clicking the option `Setting` and clicking `Privacy`.
        """
        self.d(description="Drawer").click()
        self.d(text="Settings").click()
        self.d(text="Privacy").click()
```

- 通过装饰器 `@precondition`，指定脚本的前置条件——当处于 `Home` 页面时启用。
此处，`Home` 页面为 `Privacy` 页面的入口，且 Fastbot 易达，因此通过检测唯一控件 `Home` 的存在来激活脚本。
- 在脚本的测试方法 `test_goToPrivacy` 中，指定交互逻辑（打开 `Drawer`，点击 `Setting` 选项，再点击 `Privacy`）来引导 Fastbot 到达目标页面。
- 通过装饰器 `@prob`，向脚本设置概率——本示例为 50%，表示当在 `Home` 页面时，有一定概率执行此引导，且仍保留 Fastbot 探索其它页面的机会。

完整示例见脚本 `quicktest.py`，可通过如下命令运行该脚本并使用 Fastbot：

```bash
# 启动 Kea2 并加载单个脚本 quicktest.py。
kea2 run -s "emulator-5554" -p it.feio.android.omninotes.alpha --agent u2 --running-minutes 10 --throttle 200 --driver-name d unittest discover -p quicktest.py
```

## 特性 3(运行增强版Fastbot：加入自动断言)

Kea2 支持运行 Fastbot 时自动断言，以发现*逻辑错误*（即*非崩溃缺陷*）。您可在脚本中添加断言，当断言失败时，即触发疑似功能缺陷的报告。

在特性 3 中，脚本由三个元素组成：

- **前置条件（Precondition）：** 何时执行脚本。
- **交互场景（Interaction scenario）：** 脚本测试方法中的交互逻辑。
- **断言（Assertion）：** 期望的应用行为。

### 示例

在社交媒体应用中，发送消息是常用功能。发送页面中，当输入框非空时，`send` 按钮应始终出现。

<div align="center" >
    <div >
        <img src="docs/socialAppBug.png" style="border-radius: 14px; width:30%; height:40%;"/>
    </div>
    <p>期望的行为（上图）和有缺陷的行为（下图）。<p/>
</div>

针对以上“始终成立”的性质，我们可编写如下脚本验证功能正确性：当发送页面存在 `input_box` 控件时，输入任意非空字符串，并断言 `send_button` 应始终存在。

```python
    @precondition(
        lambda self: self.d(description="input_box").exists
    )
    def test_input_box(self):
        from hypothesis.strategies import text, ascii_letters
        random_str = text(alphabet=ascii_letters).example()
        self.d(description="input_box").set_text(random_str)
        assert self.d(description="send_button").exist

        # 我们还可以有更多断言，例如：
        #       输入的字符串应出现在发送页面中
        assert self.d(text=random_str).exist
```
> 我们使用 [hypothesis](https://github.com/HypothesisWorks/hypothesis) 生成随机文本。

您可用与特性 2 类似的命令行运行此示例。

## 文档（更多文档）

[更多文档](docs/manual_en.md)，包括：
- Kea2 案例教程（基于微信实例）、
- Kea2 脚本定义说明，支持的脚本装饰器（如 `@precondition`、`@prob`、`@max_tries`）、
- Kea2 启动方法、命令行选项
- 查看/理解 Kea2 运行结果（如界面截图、测试覆盖率、脚本执行成功情况）
- [如何黑白控件/区域](docs/blacklisting.md)

## Kea2 使用的开源项目

- [Fastbot](https://github.com/bytedance/Fastbot_Android)
- [uiautomator2](https://github.com/openatx/uiautomator2)
- [hypothesis](https://github.com/HypothesisWorks/hypothesis)

## Kea2 相关论文

> General and Practical Property-based Testing for Android Apps. ASE 2024. [pdf](https://dl.acm.org/doi/10.1145/3691620.3694986)

> An Empirical Study of Functional Bugs in Android Apps. ISSTA 2023. [pdf](https://dl.acm.org/doi/10.1145/3597926.3598138)

> Fastbot2: Reusable Automated Model-based GUI Testing for Android Enhanced by Reinforcement Learning. ASE 2022. [pdf](https://dl.acm.org/doi/10.1145/3551349.3559505)

> Guided, Stochastic Model-Based GUI Testing of Android Apps. ESEC/FSE 2017.  [pdf](https://dl.acm.org/doi/10.1145/3106237.3106298)

### 维护者/贡献者

Kea2 由 [ecnusse](https://github.com/ecnusse) 团队积极开发与维护：

- [Xixian Liang](https://xixianliang.github.io/resume/) ([@XixianLiang][])
- Bo Ma ([@majuzi123][])
- Chen Peng ([@Drifterpc][])
- [Ting Su](https://tingsu.github.io/) ([@tingsu][])

[@XixianLiang]: https://github.com/XixianLiang
[@majuzi123]: https://github.com/majuzi123
[@Drifterpc]: https://github.com/Drifterpc
[@tingsu]: https://github.com/tingsu

[Zhendong Su](https://people.inf.ethz.ch/suz/)、[Yiheng Xiong](https://xyiheng.github.io/)、[Xiangchen Shen](https://xiangchenshen.github.io/)、[Mengqian Xu](https://mengqianx.github.io/)、[Haiying Sun](https://faculty.ecnu.edu.cn/_s43/shy/main.psp)、[Jingling Sun](https://jinglingsun.github.io/)、[Jue Wang](https://cv.juewang.info/) 也积极参与并做出重大贡献！

同时，Kea2 也得到了来自字节跳动（[Zhao Zhang](https://github.com/zhangzhao4444)、Fastbot团队的 Yuhui Su）、OPay（Tiesong Liu）、微信（Haochuan Lu、Yuetang Deng）、华为、小米等多家业界人员的宝贵见解、建议、反馈和经验分享。致敬！

[^1]: 许多 UI 自动化测试工具提供“自定义事件序列”能力（如[Fastbot](https://github.com/bytedance/Fastbot_Android/blob/main/handbook-cn.md#%E8%87%AA%E5%AE%9A%E4%B9%89%E4%BA%8B%E4%BB%B6%E5%BA%8F%E5%88%97)和[AppCrawler](https://github.com/seveniruby/AppCrawler)），但实际使用中存在不少问题，如定制能力有限、使用不便等。此前许多 Fastbot 用户曾抱怨其“自定义事件序列”相关问题，如[#209](https://github.com/bytedance/Fastbot_Android/issues/209)、[#225](https://github.com/bytedance/Fastbot_Android/issues/225)、[#286](https://github.com/bytedance/Fastbot_Android/issues/286) 等。

[^2]: UI 自动化测试过程中支持自动断言是一项关键能力，但几乎暂无工具支持。我们注意到 [AppCrawler](https://ceshiren.com/t/topic/15801/5) 的开发者曾希望提供断言机制，受用户强烈期待，从2021年起多次催促，仍未实现。