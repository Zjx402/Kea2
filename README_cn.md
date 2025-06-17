[![PyPI](https://img.shields.io/pypi/v/kea2-python.svg)](https://pypi.python.org/pypi/kea2-python)
[![PyPI Downloads](https://static.pepy.tech/badge/kea2-python)](https://pepy.tech/projects/kea2-python)
![Python](https://img.shields.io/badge/python-3.8%2B-blue)

<div>
    <img src="https://github.com/user-attachments/assets/1a64635b-a8f2-40f1-8f16-55e47b1d74e7" style="border-radius: 14px; width: 20%; height: 20%;"/> 
</div>

## 关于

Kea2 是一个易于使用的 Python 库，支持、自定义并改善移动应用的自动化 UI 测试。Kea2 的创新之处在于能够融合人类编写的脚本与自动化 UI 测试工具，从而实现许多有趣且强大的功能。

Kea2 目前基于 [Fastbot](https://github.com/bytedance/Fastbot_Android) 和 [uiautomator2](https://github.com/openatx/uiautomator2) 构建，主要面向 [Android](https://en.wikipedia.org/wiki/Android_(operating_system)) 应用。

## 主要功能
- **功能1**（查找稳定性问题）：具备完整的 [Fastbot](https://github.com/bytedance/Fastbot_Android) 压力测试能力，能找出*稳定性问题*（即*崩溃类缺陷*）；

- **功能2**（自定义测试场景\事件序列\黑白名单\黑白控件[^1]）：运行 Fastbot 时自定义测试场景（如测试特定应用功能、执行特定事件序列、进入指定 UI 页面、达到特定应用状态、黑名单特定活动/UI控件/UI区域），完全灵活且强大，依托 *python* 语言和 [uiautomator2](https://github.com/openatx/uiautomator2)；

- **功能3**（支持断言机制[^2]）：运行 Fastbot 时支持自动断言，基于从 [Kea](https://github.com/ecnusse/Kea) 继承的 [property-based testing](https://en.wikipedia.org/wiki/Software_testing#Property_testing) 思想，寻找*逻辑缺陷*（即*非崩溃类缺陷*）。


**Kea2 三大功能能力对比**
|  | **功能1** | **功能2** | **功能3** |
| --- | --- | --- | ---- |
| **发现崩溃** | :+1: | :+1: | :+1: |
| **在深层状态发现崩溃** |  | :+1: | :+1: |
| **发现非崩溃功能性（逻辑）缺陷** |  |  | :+1: |


<div align="center">
    <div style="max-width:80%; max-height:80%">
    <img src="docs/intro.png" style="border-radius: 14px; width: 80%; height: 80%;"/> 
    </div>
</div>

## 设计与发展路线

Kea2 作为 Python 库发布，当前支持：
- 以 [unittest](https://docs.python.org/3/library/unittest.html) 作为测试框架；
- 以 [uiautomator2](https://github.com/openatx/uiautomator2) 作为 UI 测试驱动；
- 以 [Fastbot](https://github.com/bytedance/Fastbot_Android) 作为后端自动化 UI 测试工具。

未来，Kea2 将扩展支持：
- [pytest](https://docs.pytest.org/en/stable/)
- [Appium](https://github.com/appium/appium)、[Hypium](https://developer.huawei.com/consumer/cn/doc/harmonyos-guides/hypium-python-guidelines)（针对 HarmonyOS/Open Harmony）
- 其他自动化 UI 测试工具（不限于 Fastbot）

## 安装

运行环境：
- 支持 Windows、MacOS 和 Linux
- python 3.8+，Android 4.4+（需安装 Android SDK）
- **关闭 VPN**（功能2和3要求）

通过 pip 安装 Kea2：
```bash
python3 -m pip install kea2-python
```

查看 Kea2 的选项：
```bash
kea2 -h
```

## 快速测试

Kea2 连接并运行于 Android 设备。推荐先进行快速测试，确保 Kea2 与设备兼容。

1. 连接真实 Android 设备或 Android 模拟器（一个设备即可），确保通过命令 `adb devices` 能看到连接设备。

2. 运行 `quicktest.py` 测试示例应用 `omninotes`（示例 apk：omninotes.apk，包含于 Kea2 仓库中）。脚本会自动安装并对该示例应用做短时间测试。

在你喜欢的工作目录初始化 Kea2：
```python
kea2 init
```

> 如果是首次运行 Kea2，该步骤必做。

运行快速测试：
```python
python3 quicktest.py
```

如果看到应用 `omninotes` 成功启动并测试，则说明 Kea2 正常工作！
否则，请帮忙向我们提交带有错误信息的[缺陷报告](https://github.com/ecnusse/Kea2/issues)。感谢！

## 功能1（运行基础版 Fastbot：查找稳定性错误）

利用 Fastbot 完整能力进行压力测试，发现*稳定性问题*（即*崩溃缺陷*）；

```bash
kea2 run -s "emulator-5554" -p it.feio.android.omninotes.alpha --agent native --running-minutes 10 --throttle 200
```

理解以上选项含义请查阅[文档](docs/manual_en.md#launching-kea2)

> 使用方法类似 Fastbot 原始的[shell 命令](https://github.com/bytedance/Fastbot_Android?tab=readme-ov-file#run-fastbot-with-shell-command)。

更多选项：
```bash
kea2 run -h
```

## 功能2（运行增强版 Fastbot：自定义测试场景\事件序列\黑白控件）

运行任何自动化 UI 测试工具（如 Fastbot）测试应用时，你可能发现某些 UI 页面或功能难以覆盖，原因是 Fastbot 对你的应用缺乏足够了解。脚本测试在这方面有优势。功能2支持写小脚本，引导 Fastbot 探索特定页面，还能用脚本在测试中屏蔽特定控件。

在 Kea2 中，脚本由两个元素组成：
- **前置条件（Precondition）**：何时执行脚本。
- **交互场景**：脚本测试方法中指定的交互逻辑，实现到达目标。

### 简单示例

假设 `Privacy` 是自动化测试中难以到达的页面。Kea2 可轻松引导 Fastbot 访问该页面。

```python
    @prob(0.5)
    # precondition: 当处于页面 `Home`
    @precondition(lambda self: 
        self.d(text="Home").exists
    )
    def test_goToPrivacy(self):
        """
        引导 Fastbot 到页面 `Privacy` ，方法是打开 `Drawer`，
        点击选项 `Setting`，再点击 `Privacy`。
        """
        self.d(description="Drawer").click()
        self.d(text="Settings").click()
        self.d(text="Privacy").click()
```

- 通过装饰器 `@precondition` 指定前置条件 —— 当处于 `Home` 页面。
此时 `Home` 是 `Privacy` 页面入口且 Fastbot 易到达，从而通过检查控件 `Home` 是否存在激活该脚本。
- 脚本中测试方法 `test_goToPrivacy` 指定交互逻辑（打开 `Drawer`，点击 `Setting`，再点击 `Privacy`）引导 Fastbot 到 `Privacy` 页面。
- 通过装饰器 `@prob` 指定在处于 `Home` 页时有 50% 概率执行该引导，允许 Fastbot 仍有机会探索其他页面。

完整示例见脚本 `quicktest.py`，用命令 `kea2 run` 结合 Fastbot 执行：

```bash
# 启动 Kea2 并加载单脚本 quicktest.py。
kea2 run -s "emulator-5554" -p it.feio.android.omninotes.alpha --agent u2 --running-minutes 10 --throttle 200 --driver-name d unittest discover -p quicktest.py
```

## 功能3（运行增强版 Fastbot：加入自动断言）

Kea2 支持运行 Fastbot 时自动断言，用于发现*逻辑缺陷*（即*非崩溃缺陷*）。你可以在脚本中添加断言，断言失败时即发现可能的功能缺陷。

功能3中，脚本由三部分构成：
- **前置条件**：何时执行脚本。
- **交互场景**：脚本测试方法中指定的交互逻辑。
- **断言**：预期的应用表现。

### 示例

在社交应用中，发送消息是常用功能。发送页面中，输入框非空时应始终显示“发送”按钮。

<div align="center" >
    <div >
        <img src="docs/socialAppBug.png" style="border-radius: 14px; width:30%; height:40%;"/>
    </div>
    <p>期望的行为（上图）与有缺陷的行为（下图）。
<p/>
</div>

针对该始终保持的性质，可以写如下脚本验证功能正确性：消息发送页上如果存在 `input_box`，向输入框输入任意非空字符串，并断言 `send_button` 始终存在。


```python
    @precondition(
        lambda self: self.d(description="input_box").exists
    )
    def test_input_box(self):
        from hypothesis.strategies import text, ascii_letters
        random_str = text(alphabet=ascii_letters).example()
        self.d(description="input_box").set_text(random_str)
        assert self.d(description="send_button").exist

        # 还可以做更多断言，例如：
        #       输入的字符串应显示在消息发送页上
        assert self.d(text=random_str).exist
```
> 这里使用了 [hypothesis](https://github.com/HypothesisWorks/hypothesis) 来生成随机文本。

该示例可参照功能2的命令行运行。

## 文档（更多文档）

[更多文档](docs/manual_en.md)，包括：
- Kea2 的案例教程（基于微信介绍）
- Kea2 脚本的定义方法，支持的脚本装饰器（如 `@precondition`、`@prob`、`@max_tries`）
- Kea2 的启动方式、命令行选项
- 查看/理解 Kea2 运行结果（如界面截图、测试覆盖率、脚本执行情况）
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

Kea2 由 [ecnusse](https://github.com/ecnusse) 团队积极开发和维护：

- [Xixian Liang](https://xixianliang.github.io/resume/) ([@XixianLiang][])
- Bo Ma ([@majuzi123][])
- Chen Peng ([@Drifterpc][])
- [Ting Su](https://tingsu.github.io/) ([@tingsu][])

[@XixianLiang]: https://github.com/XixianLiang
[@majuzi123]: https://github.com/majuzi123
[@Drifterpc]: https://github.com/Drifterpc
[@tingsu]: https://github.com/tingsu

[Zhendong Su](https://people.inf.ethz.ch/suz/)、[Yiheng Xiong](https://xyiheng.github.io/)、[Xiangchen Shen](https://xiangchenshen.github.io/)、[Mengqian Xu](https://mengqianx.github.io/)、[Haiying Sun](https://faculty.ecnu.edu.cn/_s43/shy/main.psp)、[Jingling Sun](https://jinglingsun.github.io/)、[Jue Wang](https://cv.juewang.info/) 也积极参与并贡献巨大！

此外，Kea2 得到字节跳动（[Zhao Zhang](https://github.com/zhangzhao4444)、Fastbot 团队 Yuhui Su）、OPay（Tiesong Liu）、微信（Haochuan Lu、Yuetang Deng）、华为、小米等多位业界专家宝贵见解、建议、反馈及经验分享。致谢！

[^1]: 许多 UI 自动化测试工具支持“自定义事件序列”（如 [Fastbot](https://github.com/bytedance/Fastbot_Android/blob/main/handbook-cn.md#%E8%87%AA%E5%AE%9A%E4%B9%89%E4%BA%8B%E4%BB%B6%E5%BA%8F%E5%88%97) 和 [AppCrawler](https://github.com/seveniruby/AppCrawler)），但其实用中常见限制，比如自定义能力有限，灵活性差等。众多 Fastbot 用户曾投诉其“自定义事件序列”相关问题，如[#209](https://github.com/bytedance/Fastbot_Android/issues/209), [#225](https://github.com/bytedance/Fastbot_Android/issues/225), [#286](https://github.com/bytedance/Fastbot_Android/issues/286) 等。

[^2]: UI 自动化测试过程中支持自动断言是一项重要能力，但几乎无测试工具提供。我们注意到 [AppCrawler](https://ceshiren.com/t/topic/15801/5) 开发者曾希望添加断言机制，得到用户热烈响应，多数用户自 2021 年开始催促，但至今未实现。