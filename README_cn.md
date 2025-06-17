[![PyPI](https://img.shields.io/pypi/v/kea2-python.svg)](https://pypi.python.org/pypi/kea2-python)
[![PyPI Downloads](https://static.pepy.tech/badge/kea2-python)](https://pepy.tech/projects/kea2-python)
![Python](https://img.shields.io/badge/python-3.8%2B-blue)

<div>
    <img src="https://github.com/user-attachments/assets/1a64635b-a8f2-40f1-8f16-55e47b1d74e7" style="border-radius: 14px; width: 20%; height: 20%;"/> 
</div>

## 关于

Kea2 是一个易于使用的 Python 库，用于支持、定制和改进移动应用的自动化 UI 测试。Kea2 的创新之处在于能够将人工编写的脚本与自动化 UI 测试工具融合，从而实现许多有趣且强大的功能。

Kea2 目前基于 [Fastbot](https://github.com/bytedance/Fastbot_Android) 和 [uiautomator2](https://github.com/openatx/uiautomator2) 构建，并针对 [Android](https://en.wikipedia.org/wiki/Android_(operating_system)) 应用。

## 重要特性
- **特性1**(查找稳定性问题): 具备[Fastbot](https://github.com/bytedance/Fastbot_Android)的全部压力测试能力，可发现*稳定性问题*（即*崩溃类缺陷*）；  

- **特性2**(自定义测试场景\事件序列\黑白名单\黑白控件[^1]): 支持通过*python*语言和[uiautomator2](https://github.com/openatx/uiautomator2)灵活定制Fastbot测试场景（例如：测试特定功能、执行特定事件序列、进入特定UI页面、到达特定应用状态、屏蔽特定activity/UI控件/UI区域）；  

- **特性3**(支持断言机制[^2]): 基于[Kea](https://github.com/ecnusse/Kea)继承的[基于性质的测试](https://en.wikipedia.org/wiki/Software_testing#Property_testing)理念，支持在Fastbot运行过程中自动断言，用于发现*逻辑缺陷*（即*非崩溃类缺陷*）


**Kea2三大特性能力对比**
|  | **特性1** | **特性2** | **特性3** |
| --- | --- | --- | ---- |
| **发现崩溃问题** | :+1: | :+1: | :+1: |
| **发现深层状态崩溃问题** |  | :+1: | :+1: |
| **发现非崩溃功能（逻辑）缺陷** |  |  | :+1: |


<div align="center">
    <div style="max-width:80%; max-height:80%">
    <img src="docs/intro.png" style="border-radius: 14px; width: 80%; height: 80%;"/> 
    </div>
</div>

## 安装

运行环境：
- 支持 Windows、MacOS 和 Linux
- python 3.8+，Android 4.4+（需安装 Android SDK）
- **关闭 VPN**（功能2和3需要）

通过 `pip` 安装 Kea2：
```bash
python3 -m pip install kea2-python
```

查看 Kea2 的选项：
```bash
kea2 -h
```

## 快速测试

Kea2 需连接并在 Android 设备上运行。建议执行快速测试以确保 Kea2 与您的设备兼容。

1. 连接真实 Android 设备或模拟器（仅需一台设备），并通过 `adb devices` 确认设备已连接。

2. 运行 `quicktest.py` 测试示例应用 `omninotes`（该应用以 `omninotes.apk` 形式发布在 Kea2 的代码库中）。脚本 `quicktest.py` 会自动安装并短时间测试该应用。

在您的工作目录下初始化 Kea2：
```python
kea2 init
```

> 首次运行 Kea2 时必须执行此步骤。

执行快速测试：
```python
python3 quicktest.py
```

若能看到应用 `omninotes` 成功运行并完成测试，则表明 Kea2 工作正常！
若出现问题，请将错误信息[提交问题报告](https://github.com/ecnusse/Kea2/issues)给我们，感谢！

## Feature 1(运行基础版Fastbot：查找稳定性错误)

使用Fastbot的全部功能对您的应用进行压力测试，以发现*稳定性问题*（即*崩溃错误*）；


```bash
kea2 run -s "emulator-5554" -p it.feio.android.omninotes.alpha --agent native --running-minutes 10 --throttle 200
```

理解上述选项含义请查看[文档](docs/manual_en.md#launching-kea2)

> The usage is similar to the the original Fastbot's [shell commands](https://github.com/bytedance/Fastbot_Android?tab=readme-ov-file#run-fastbot-with-shell-command). 

查看更多选项：
```bash
kea2 run -h
```

## Feature 2(运行增强版Fastbot：自定义测试场景\事件序列\黑白控件)

当运行Fastbot等自动化UI测试工具测试您的应用时，您可能会发现某些特定的UI页面或功能难以到达或覆盖。原因是Fastbot缺乏对您应用的了解。幸运的是，这正是脚本测试的优势所在。在Feature 2中，Kea2支持编写小型脚本来引导Fastbot探索我们想要的任何地方。您还可以使用此类小型脚本在UI测试期间阻止特定的控件。

在Kea2中，脚本由两个要素组成：
-  **前置条件（Precondition）：** 何时执行脚本。
- **交互场景（Interaction scenario）：** 到达目标所需的交互逻辑（在脚本的测试方法中指定）。

### 简单示例

假设在自动化UI测试中，`Privacy`是一个难以到达的UI页面。Kea2可以轻松引导Fastbot到达该页面。

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

- 通过装饰器`@precondition`，我们指定了前置条件——当处于`Home`页面时。  
  在此例中，`Home`页面是`Privacy`页面的入口页面，且Fastbot可以轻松到达`Home`页面。因此，当通过检查唯一控件`Home`是否存在确认当前处于`Home`页面时，该脚本将被激活。  
- 在脚本的测试方法`test_goToPrivacy`中，我们指定了交互逻辑（即打开`Drawer`、点击选项`Setting`并点击`Privacy`）来引导Fastbot到达`Privacy`页面。  
- 通过装饰器`@prob`，我们指定了处于`Home`页面时执行引导的概率（本例中为50%）。因此，Kea2仍允许Fastbot探索其他页面。

完整示例可查看脚本`quicktest.py`，并通过命令`kea2 run`结合Fastbot运行该脚本：

```bash
# 启动Kea2并加载单个脚本quicktest.py
kea2 run -s "emulator-5554" -p it.feio.android.omninotes.alpha --agent u2 --running-minutes 10 --throttle 200 --driver-name d unittest discover -p quicktest.py
```

## 功能3（运行增强版Fastbot：加入自动断言）

Kea2支持在运行Fastbot时通过自动断言来发现*逻辑错误*（即*非崩溃型错误*）。为此，您可以在脚本中添加断言。当自动化UI测试过程中断言失败时，即可发现潜在的功能性错误。

在功能3中，脚本由三个要素组成：

- **前置条件**：何时执行脚本。
- **交互场景**：交互逻辑（在脚本的测试方法中指定）。
- **断言**：预期的应用行为。

### 示例

在一款社交媒体应用中，消息发送是一个常见功能。在消息发送页面，当输入框不为空（即包含某些消息）时，`send`按钮应始终显示。

<div align="center" >
    <div >
        <img src="docs/socialAppBug.png" style="border-radius: 14px; width:30%; height:40%;"/>
    </div>
    <p>预期行为（上图）与存在缺陷的行为（下图）。
<p/>
</div>

针对上述始终成立的性质，我们可以编写以下脚本来验证功能正确性：当消息发送页面上存在`input_box`控件时，我们可以向输入框中键入任意非空字符串文本，并断言`send_button`应始终存在。

```python
    @precondition(
        lambda self: self.d(description="input_box").exists
    )
    def test_input_box(self):
        from hypothesis.strategies import text, ascii_letters
        random_str = text(alphabet=ascii_letters).example()
        self.d(description="input_box").set_text(random_str)
        assert self.d(description="send_button").exist

        # 我们还可以进行更多断言，例如：
        #       输入字符串应存在于消息发送页面
        assert self.d(text=random_str).exist
```
> 我们使用[hypothesis](https://github.com/HypothesisWorks/hypothesis)生成随机文本。

您可以通过与特性2中类似的命令行运行此示例。

## 文档（更多文档）

[更多文档](docs/manual_en.md)，包括：
- Kea2的案例教程（基于微信介绍）、
- Kea2脚本的定义方法，支持的脚本装饰器（如`@precondition`、`@prob`、`@max_tries`）、
- Kea2的启动方式、命令行选项
- 查看/理解Kea2的运行结果（如界面截图、测试覆盖率、脚本执行成功与否）。
- [如何黑白控件/区域](docs/blacklisting.md)

## Kea2使用的开源项目

- [Fastbot](https://github.com/bytedance/Fastbot_Android)
- [uiautomator2](https://github.com/openatx/uiautomator2)
- [hypothesis](https://github.com/HypothesisWorks/hypothesis)

## Kea2相关论文

> General and Practical Property-based Testing for Android Apps. ASE 2024. [pdf](https://dl.acm.org/doi/10.1145/3691620.3694986)

> An Empirical Study of Functional Bugs in Android Apps. ISSTA 2023. [pdf](https://dl.acm.org/doi/10.1145/3597926.3598138)

> Fastbot2: Reusable Automated Model-based GUI Testing for Android Enhanced by Reinforcement Learning. ASE 2022. [pdf](https://dl.acm.org/doi/10.1145/3551349.3559505)

> Guided, Stochastic Model-Based GUI Testing of Android Apps. ESEC/FSE 2017.  [pdf](https://dl.acm.org/doi/10.1145/3106237.3106298)

### 维护者/贡献者

Kea2 由 [ecnusse](https://github.com/ecnusse) 的成员积极开发和维护：

- [Xixian Liang](https://xixianliang.github.io/resume/) ([@XixianLiang][])
- Bo Ma ([@majuzi123][])
- Chen Peng ([@Drifterpc][])
- [Ting Su](https://tingsu.github.io/) ([@tingsu][])

[@XixianLiang]: https://github.com/XixianLiang
[@majuzi123]: https://github.com/majuzi123
[@Drifterpc]: https://github.com/Drifterpc
[@tingsu]: https://github.com/tingsu

[Zhendong Su](https://people.inf.ethz.ch/suz/)、[Yiheng Xiong](https://xyiheng.github.io/)、[Xiangchen Shen](https://xiangchenshen.github.io/)、[Mengqian Xu](https://mengqianx.github.io/)、[Haiying Sun](https://faculty.ecnu.edu.cn/_s43/shy/main.psp)、[Jingling Sun](https://jinglingsun.github.io/)、[Jue Wang](https://cv.juewang.info/) 也积极参与了本项目并作出了重要贡献！

Kea2 还获得了来自字节跳动（Fastbot 团队的 [Zhao Zhang](https://github.com/zhangzhao4444)、Yuhui Su）、OPay（Tiesong Liu）、微信（Haochuan Lu、Yuetang Deng）、华为、小米等工业界人士的宝贵见解、建议、反馈和经验分享。感谢他们！

[^1]: 不少 UI 自动化测试工具提供了“自定义事件序列”能力（如 [Fastbot](https://github.com/bytedance/Fastbot_Android/blob/main/handbook-cn.md#%E8%87%AA%E5%AE%9A%E4%B9%89%E4%BA%8B%E4%BB%B6%E5%BA%8F%E5%88%97) 和 [AppCrawler](https://github.com/seveniruby/AppCrawler)），但在实际使用中存在不少问题，如自定义能力有限、使用不灵活等。此前不少 Fastbot 用户抱怨过其“自定义事件序列”在使用中的问题，如 [#209](https://github.com/bytedance/Fastbot_Android/issues/209)、[#225](https://github.com/bytedance/Fastbot_Android/issues/225)、[#286](https://github.com/bytedance/Fastbot_Android/issues/286) 等。

[^2]: 在 UI 自动化测试过程中支持自动断言是一个很重要的能力，但几乎没有测试工具提供这样的能力。我们注意到 [AppCrawler](https://ceshiren.com/t/topic/15801/5) 的开发者曾经希望提供一种断言机制，得到了用户的热切响应，不少用户从 21 年就开始催更，但始终未能实现。