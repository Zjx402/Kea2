## Blacklisting specific UI widgets/regions (黑白名单/控件/界面特定区域)

[中文文档](docs/blacklisting_cn.md)

我们支持对特定 UI 控件/区域进行黑名单处理，以便 Fastbot 在模糊测试过程中避免与这些控件交互。

我们支持两种粒度级别的黑名单：

- 控件屏蔽：屏蔽单个 UI 控件。

- 树屏蔽：通过指定根节点屏蔽一个 UI 控件树。
它可以屏蔽根节点及其所有子节点。

我们支持（1）`全局黑名单`（始终生效）和（2）`条件黑名单`（仅在满足某些条件时生效）。

被屏蔽元素列表在 Kea2 的配置文件 `configs/widget.block.py` 中指定（运行 `kea2 init` 时生成）。
需要屏蔽的元素可以灵活地通过 u2 选择器（例如 `text`、`description`）或 `xpath` 等指定。

#### 控件屏蔽
##### 全局黑名单
我们可以定义函数 `global_block_widgets`，指定哪些 UI 控件应被全局屏蔽。该屏蔽始终生效。

```python
# file: configs/widget.block.py

def global_block_widgets(d: "Device"):
    """
    全局黑名单。
    返回应被全局屏蔽的控件列表。
    """
    return [d(text="widgets to block"), 
            d.xpath(".//node[@text='widget to block']"),
            d(description="widgets to block")]
```
##### 条件黑名单
我们可以定义任意以 “block_” 开头（但不要求以 “block_tree_” 开头）的保留函数名，并使用 `@precondition` 装饰该函数，以支持条件黑名单。
在这种情况下，屏蔽仅在前置条件满足时生效。

```python
# file: configs/widget.block.py

# 条件黑名单
@precondition(lambda d: d(text="In the home page").exists)
def block_sth(d: "Device"):
    # 重要：函数名应以 "block_" 开头
    return [d(text="widgets to block"), 
            d.xpath(".//node[@text='widget to block']"),
            d(description="widgets to block")]
```

#### 树屏蔽
##### 全局黑名单
我们可以定义函数 `global_block_tree`，指定哪些 UI 控件树应被全局屏蔽。该屏蔽始终生效。

```python
# file: configs/widget.block.py

def global_block_tree(d: "Device"):
    """
    指定测试过程中全局屏蔽的 UI 控件树。
    返回根节点列表，整个子树将被屏蔽不被探索。
    该函数仅在 'u2 agent' 模式下可用。
    """
    return [d(text="trees to block"), d.xpath(".//node[@text='tree to block']")]
```
##### 条件黑名单
我们可以定义任意以 “block_tree_” 开头的保留函数名，并使用 `@precondition` 装饰该函数，以支持条件黑名单。
在这种情况下，屏蔽仅在前置条件满足时生效。

```python
# file: configs/widget.block.py

# 带前置条件的条件树屏蔽示例

@precondition(lambda d: d(text="In the home page").exists)
def block_tree_sth(d: "Device"):
    # 注意：函数名必须以 "block_tree_" 开头
    return [d(text="trees to block"), 
            d.xpath(".//node[@text='tree to block']"),
            d(description="trees to block")]
```