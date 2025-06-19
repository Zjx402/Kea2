[![PyPI](https://img.shields.io/pypi/v/kea2-python.svg)](https://pypi.python.org/pypi/kea2-python)
[![PyPI Downloads](https://static.pepy.tech/badge/kea2-python)](https://pepy.tech/projects/kea2-python)
![Python](https://img.shields.io/badge/python-3.8%2B-blue)


<div>
    <img src="https://github.com/user-attachments/assets/aa5839fc-4542-46f6-918b-c9f891356c84" style="border-radius: 14px; width: 20%; height: 20%;"/> 
</div>

[中文文档](README_cn.md)

## 关于

Kea2 是一个易用的 Python 库，用于支持、自定义和提升移动应用的自动化 UI 测试。Kea2 的创新点在于能够融合由人类编写的脚本与自动化 UI 测试工具，从而实现许多有趣且强大的功能。

Kea2 目前基于 [Fastbot](https://github.com/bytedance/Fastbot_Android) 和 [uiautomator2](https://github.com/openatx/uiautomator2) 构建，目标是 [Android](https://en.wikipedia.org/wiki/Android_(operating_system)) 应用。

## 主要特性
- **特性 1**(查找稳定性问题)：具备 [Fastbot](https://github.com/bytedance/Fastbot_Android) 的全部能力，用于压力测试和发现*稳定性问题*（即*崩溃类错误*）；

- **特性 2**(自定义测试场景\事件序列\黑白名单\黑白控件[^1])：在运行 Fastbot 时自定义测试场景（例如，测试特定应用功能、执行特定事件序列、进入特定 UI 页面、达到特定应用状态、黑名单特定 Activity/UI 控件/UI 区域），通过 *python* 语言和 [uiautomator2](https://github.com/openatx/uiautomator2) 提供的完整能力与灵活性实现；

- **特性 3**(支持断言机制[^2])：运行 Fastbot 时支持自动断言机制，基于继承自 [Kea](https://github.com/ecnusse/Kea) 的[基于性质的测试](https://en.wikipedia.org/wiki/Software_testing#Property_testing)思想，用来发现*逻辑错误*（即*非崩溃类错误*）。

**Kea2 三大特性的能力**

|  | **特性 1** | **特性 2** | **特性 3** |
| --- | --- | --- | ---- |
| **发现崩溃** | :+1: | :+1: | :+1: |
| **在深层状态发现崩溃** |  | :+1: | :+1: |
| **发现非崩溃的功能（逻辑）缺陷** |  |  | :+1: |


<div align="center">
    <div style="max-width:80%; max-height:80%">
    <img src="docs/intro.png" style="border-radius: 14px; width: 80%; height: 80%;"/> 
    </div>
</div>



## 设计与规划

Kea2 以 Python 库形式发布，目前支持：
- 使用 [unittest](https://docs.python.org/3/library/unittest.html) 作为测试框架；
- 使用 [uiautomator2](https://github.com/openatx/uiautomator2) 作为 UI 测试驱动器；
- 使用 [Fastbot](https://github.com/bytedance/Fastbot_Android) 作为后台自动化 UI 测试工具。

未来，Kea2 将扩展支持：
- [pytest](https://docs.pytest.org/en/stable/)
- [Appium](https://github.com/appium/appium)、[Hypium](https://developer.huawei.com/consumer/cn/doc/harmonyos-guides/hypium-python-guidelines)（针对 HarmonyOS/Open Harmony）
- 其他自动化 UI 测试工具（不限于 Fastbot）


## 安装

运行环境：
- 支持 Windows、MacOS 和 Linux
- python 3.8+，Android 5.0+（需安装 Android SDK）
- **关闭 VPN**（特性 2 和 3 需要）

通过 `pip` 安装 Kea2：
```bash
python3 -m pip install kea2-python
```

运行以下命令查看 Kea2 的选项：
```bash
kea2 -h
```

## 快速测试

Kea2 连接并运行于 Android 设备上。建议你做一次快速测试以确保 Kea2 与你的设备兼容。

1. 连接真实 Android 设备或 Android 模拟器（只需一个设备），并通过执行 `adb devices` 确认设备已连接。

2. 运行 `quicktest.py` 来测试示例应用 `omninotes`（已随 Kea2 仓库发布为 `omninotes.apk`）。`quicktest.py` 会自动安装并进行短时间测试。

在你偏好的工作目录下初始化 Kea2：
```python
kea2 init
```

> 如果你是首次运行 Kea2，此步必做。

运行快速测试：
```python
python3 quicktest.py
```

如果你看到应用 `omninotes` 成功运行且被测试，表示 Kea2 工作正常！
否则，请[提交 bug 报告](https://github.com/ecnusse/Kea2/issues)并附带错误信息。谢谢！


## 特性 1 (运行基础版 Fastbot：查找稳定性错误)

使用 Fastbot 的全部能力对你的应用进行压力测试并寻找*稳定性问题*（即*崩溃类错误*）；

```bash
kea2 run -s "emulator-5554" -p it.feio.android.omninotes.alpha --agent native --running-minutes 10 --throttle 200
```

理解上述选项含义请查看[文档](docs/manual_en.md#launching-kea2)

> 用法与原始 Fastbot 的[shell 命令](https://github.com/bytedance/Fastbot_Android?tab=readme-ov-file#run-fastbot-with-shell-command)类似。

更多选项请执行
```bash
kea2 run -h
```

## 特性 2 (运行增强版 Fastbot：自定义测试场景\事件序列\黑白控件)

当用 Fastbot 等自动化 UI 测试工具测试应用时，你可能会发现某些特定 UI 页面或功能很难被触达或覆盖。原因是 Fastbot 对你应用缺乏足够认知。幸运的是，这正是脚本测试的优势。在特性 2 中，Kea2 支持编写小脚本来引导 Fastbot 探索我们想要到达的地方。你也可以用这些小脚本在 UI 测试中屏蔽特定控件。

在 Kea2 中，脚本由两个要素组成：
- **前置条件（Precondition）：** 何时执行脚本。
- **交互场景：** 脚本的测试方法中指定的交互逻辑（interaction logic），用以达到目标。

### 简单示例

假设 `Privacy` 是自动化 UI 测试中难以触达的 UI 页面。Kea2 可以轻松引导 Fastbot 到达该页面。

```python
    @prob(0.5)
    # precondition: 当我们位于 `Home` 页面时
    @precondition(lambda self: 
        self.d(text="Home").exists
    )
    def test_goToPrivacy(self):
        """
        通过打开 `Drawer`，点击 `Settings` 选项，再点击 `Privacy`，
        引导 Fastbot 到达 `Privacy` 页面。
        """
        self.d(description="Drawer").click()
        self.d(text="Settings").click()
        self.d(text="Privacy").click()
```

- 通过装饰器 `@precondition`，我们指定前置条件——当我们在 `Home` 页面时执行脚本。此处 `Home` 页面是进入 `Privacy` 页的入口，且 Fastbot 容易达到。于是脚本会判断页面是否存在唯一控件 `Home` 来激活该脚本。
- 在脚本的测试方法 `test_goToPrivacy` 中，我们指定交互逻辑（即打开 `Drawer`，点击 `Settings`，点击 `Privacy`）来引导 Fastbot 到达 `Privacy` 页面。
- 通过装饰器 `@prob`，我们设置当处在 `Home` 页面时以 50% 的概率执行该引导操作，从而让 Kea2 同时允许 Fastbot 探索其它页面。

你可以在脚本 `quicktest.py` 中找到完整示例，并使用命令 `kea2 run` 运行这段脚本：

```bash
# 启动 Kea2 并加载单个脚本 quicktest.py。
kea2 run -s "emulator-5554" -p it.feio.android.omninotes.alpha --agent u2 --running-minutes 10 --throttle 200 --driver-name d unittest discover -p quicktest.py
```

## 特性 3 (运行增强版 Fastbot：加入自动断言)

Kea2 支持运行 Fastbot 时自动断言机制，用以发现*逻辑错误*（即*非崩溃类错误*）。实现方式是你可以在脚本中添加断言。当自动化 UI 测试中断言失败时，即检测到一个潜在的功能性缺陷。

在特性 3 中，脚本由三个要素组成：

- **前置条件（Precondition）：** 何时运行脚本。
- **交互场景（Interaction scenario）：** 脚本的测试方法中指定的交互逻辑。
- **断言（Assertion）：** 期望的应用行为。

### 示例

在一款社交应用中，消息发送是一个常见功能。在消息发送页面，当输入框非空时，`send` 按钮应始终出现。

<div align="center" >
    <div >
        <img src="docs/socialAppBug.png" style="border-radius: 14px; width:30%; height:40%;"/>
    </div>
    <p>期望行为（上图）与错误行为（下图）。</p>
</div>

对于上述持续保持的性质，我们可以编写以下脚本验证功能正确性：当消息发送页存在 `input_box` 控件时，向该输入框输入任意非空字符串，并断言 `send_button` 必须存在。

```python
    @precondition(
        lambda self: self.d(description="input_box").exists
    )
    def test_input_box(self):
        from hypothesis.strategies import text, ascii_letters
        random_str = text(alphabet=ascii_letters).example()
        self.d(description="input_box").set_text(random_str)
        assert self.d(description="send_button").exist

        # 我们甚至可以做更多断言，如：
        # 输入字符串应在消息发送页面上出现
        assert self.d(text=random_str).exist
```
> 我们使用 [hypothesis](https://github.com/HypothesisWorks/hypothesis) 生成随机文本。

你可使用与特性 2 类似的命令行运行此示例。

## 文档（更多资料）

[更多文档](docs/manual_en.md)，包括：
- Kea2 案例教程（基于微信示例）、
- Kea2 脚本的定义方法，支持的脚本装饰器（如 `@precondition`、`@prob`、`@max_tries`）、
- Kea2 启动方式及命令行选项、
- 查看/理解 Kea2 的运行结果（如界面截图、测试覆盖率、脚本执行成功情况）、
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

### 维护者 / 贡献者

Kea2 由 [ecnusse](https://github.com/ecnusse) 团队积极开发和维护：

- [Xixian Liang](https://xixianliang.github.io/resume/) ([@XixianLiang][])
- Bo Ma ([@majuzi123][])
- Chen Peng ([@Drifterpc][])
- [Ting Su](https://tingsu.github.io/) ([@tingsu][])

[@XixianLiang]: https://github.com/XixianLiang
[@majuzi123]: https://github.com/majuzi123
[@Drifterpc]: https://github.com/Drifterpc
[@tingsu]: https://github.com/tingsu

[Zhendong Su](https://people.inf.ethz.ch/suz/), [Yiheng Xiong](https://xyiheng.github.io/), [Xiangchen Shen](https://xiangchenshen.github.io/), [Mengqian Xu](https://mengqianx.github.io/), [Haiying Sun](https://faculty.ecnu.edu.cn/_s43/shy/main.psp), [Jingling Sun](https://jinglingsun.github.io/), [Jue Wang](https://cv.juewang.info/) 也积极参与此项目并有大量贡献！

Kea2 同时获得来自字节跳动（[Zhao Zhang](https://github.com/zhangzhao4444)、Fastbot 团队的 Su Yuhui）、OPay（Tiesong Liu）、微信（Lu Haochuan、Deng Yuetang）、华为、小米等多家产业界专家的宝贵见解、建议、反馈和经验分享。致敬！

[^1]: 许多 UI 自动化测试工具提供“自定义事件序列”能力（如 [Fastbot](https://github.com/bytedance/Fastbot_Android/blob/main/handbook-cn.md#%E8%87%AA%E5%AE%9A%E4%B9%89%E4%BA%8B%E4%BB%B6%E5%BA%8F%E5%88%97) 和 [AppCrawler](https://github.com/seveniruby/AppCrawler)），但实际使用中存在诸多问题，比如自定义能力有限、使用不灵活等。此前许多 Fastbot 用户抱怨“自定义事件序列”使用体验存在的问题，如[#209](https://github.com/bytedance/Fastbot_Android/issues/209)、[#225](https://github.com/bytedance/Fastbot_Android/issues/225)、[#286](https://github.com/bytedance/Fastbot_Android/issues/286)等。

[^2]: 在 UI 自动化测试过程中支持自动断言是一项非常重要的能力，但几乎没有测试工具提供该能力。我们注意到 [AppCrawler](https://ceshiren.com/t/topic/15801/5) 的开发者曾计划提供断言机制并得到用户强烈响应，许多用户从 2021 年起就催促更新，但该功能一直未能实现。