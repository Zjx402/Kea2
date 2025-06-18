## Blacklisting specific UI widgets/regions (黑白名单/控件/界面特定区域)

[中文文档](docs/blacklisting_cn.md)

We support blacklisting specific UI widgets/regions so that Fastbot can avoid interacting with these widgets during fuzzing. 

We support two granularity levels for blacklisting:

- Widget Blocking: Block individual UI widgets.

- Tree Blocking : Block a UI widget trees by specifying its root node.
It can block the root node and all its descendants. 

We support (1) `Global Block List` (always taking effective), and (2) `Conditional Block List` (only taking effective when some conditions are met).

The list of blocked elements are specified in Kea2's config file `configs/widget.block.py` (generated when running `kea2 init`). 
The elements needed to be blocked can be flexibly specified by u2 selector (e.g., `text`, `description`) or `xpath`, etc. 

#### Widget Blocking
##### Global Block List
We can define the function `global_block_widgets` to specify which UI widgets should be blocked globally. The blocking always takes effect. 

```python
# file: configs/widget.block.py

def global_block_widgets(d: "Device"):
    """
    global block list.
    return the widgets which should be blocked globally
    """
    return [d(text="widgets to block"), 
            d.xpath(".//node[@text='widget to block']"),
            d(description="widgets to block")]
```
##### Conditional Block List
We can define any reserved function whose name starts with "block_" (but not requiring "block_tree_" prefix) and decorate such function by `@precondition` to allow conditional block list.
In this case, the blocking only takes effect when the precondition is satisfied.
```python
# file: configs/widget.block.py

# conditional block list
@precondition(lambda d: d(text="In the home page").exists)
def block_sth(d: "Device"):
    # Important: the function name should start with "block_"
    return [d(text="widgets to block"), 
            d.xpath(".//node[@text='widget to block']"),
            d(description="widgets to block")]
```

#### Tree Blocking
##### Global Block List
We can define the function `global_block_tree` to specify which UI widget trees should be blocked globally. The blocking always takes effect. 

```python
# file: configs/widget.block.py

def global_block_tree(d: "Device"):
    """
    Specify UI widget trees to be blocked globally during testing.
    Returns a list of root nodes whose entire subtrees will be blocked from exploration.
    This function is only available in 'u2 agent' mode.
    """
     return [d(text="trees to block"), d.xpath(".//node[@text='tree to block']")]
```
##### Conditional Block List
We can define any reserved function whose name starts with "block_tree_" and decorate such function by `@precondition` to allow conditional block list.
In this case, the blocking only takes effect when the precondition is satisfied.
```python
# file: configs/widget.block.py

# Example of conditional tree blocking with precondition

@precondition(lambda d: d(text="In the home page").exists)
def block_tree_sth(d: "Device"):
    # Note: Function name must start with "block_tree_"
    return [d(text="trees to block"), 
            d.xpath(".//node[@text='tree to block']"),
            d(description="trees to block")]
```

