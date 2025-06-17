# Advance User Manuel

### Enhance Kea2 performance

Currently, we have an algorithm in `@precondition` decorator and `widgets.block.py` to enhence the performance of the tool. The algorithm only support basic selector (No parent-child relationship) in uiautomator2. If you have many properties with complex preconditions and observed performance issue, you're recommanded to specify it in xpath.

| | **Recommand** | **Not recommand** |
| -- | -- | -- |
| **Selector** | `d(text="1").exist` | `d(text="1").child(text="2").exist` |

If you need to specify `parent-child` relation ship in `@precondition`, specify it in xpath.

for example:

```python
# Do not use:
# @precondition(lambda self: 
#      self.d(className="android.widget.ListView").child(text="Bluetooth")
# ):
# ...

# Use
@precondition(lambda self: 
    self.d.xpath('//android.widget.ListView/*[@text="Bluetooth"]')
):
...
```

# Documentation for developers

We are looking for maintainers and contributors for Kea2. If you have interest in maintaining Kea2, don't hesitate to contact us.

## Installation

1. Clone `Kea2` into your workspace.

```bash
git clone git@github.com:ecnusse/Kea2.git
cd Kea2
```

2. Setup the python virtual environment with `uv`.

> [uv](https://github.com/astral-sh/uv) is a extremely fast python package and project manager. We use `uv` to create a python virtual environment for Kea2 to avoid any dependency issues or conflicts with your existing python environment.
`uv` is similar to `virtualenv` but much more powerful.
Of course, you can also setup Kea2 in your [global environment](https://github.com/ecnusse/Kea2/tree/dev?tab=readme-ov-file#appendix-install-kea2-in-a-global-environment).

```bash
pip install --upgrade pip
pip install uv
uv sync
```

> MacOS users may have trouble with global pip install. In such cases, they can use `brew`.
```bash
# For macOS users
brew install uv
uv sync
```

3. Activate virtual environment

- Linux and macOS
```bash
source .venv/bin/activate
```

- Windows cmd
```cmd
\.venv\Scripts\activate.bat
```

- Windows powershell
```powershell
\.venv\Scripts\activate.ps1
```