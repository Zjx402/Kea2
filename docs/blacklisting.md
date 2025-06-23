## Blacklisting specific UI widgets/regions (黑白名单/控件/界面特定区域)

[中文文档](blacklisting_cn.md)

We support blacklisting specific UI widgets/regions so that Fastbot can avoid interacting with these widgets during fuzzing. 

We support two levels for blacklisting:

- Widget Blocking: Only set the specified attributes (clickable, long-clickable, scrollable, checkable, enabled, focusable) of the widget you pass in to false. Use this method when you want to disable some single widget.

- Tree Blocking: Treat the passed-in widget as the root node of a subtree, and set the above attributes to false for the root node and all its descendant nodes in the subtree. Use this method when you want to disable all widgets within a certain area by simply passing the root node of that area to disable the entire subtree of widgets under it.

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


### Supported Methods for UI Element Identification

When configuring the blacklist, you can precisely locate specific UI elements in the current window by combining various attributes. These attributes can be flexibly used together to achieve accurate blocking.

For example, to locate a UI element with text "Alarm" and class name `android.widget.Button`:

```python
d(text="Alarm", className="android.widget.Button")
```

#### Supported Attributes

Commonly used attributes are listed below. For detailed usage, please refer to the official Android UiSelector documentation:

- **Text-related attributes**  
  `text`, `textContains`, `textStartsWith`

- **Class-related attributes**  
  `className`

- **Description-related attributes**  
  `description`, `descriptionContains`, `descriptionStartsWith`

- **State-related attributes**  
  `checkable`, `checked`, `clickable`, `longClickable`, `scrollable`, `enabled`, `focusable`, `focused`, `selected`

- **Package name related attributes**  
  `packageName`

- **Resource ID related attributes**  
  `resourceId`

- **Index related attributes**  
  `index`

#### Locating Children and Siblings

Besides directly locating target elements, you can locate child or sibling elements for more complex queries.

- **Locate child or grandchild elements**  
  For example, locate an item named "Wi-Fi" inside a list view:

  ```python
  d(className="android.widget.ListView").child(text="Wi-Fi")
  ```

- **Locate sibling elements**  
  For example, find an `android.widget.ImageView` sibling next to an element with text "Settings":

  ```python
  d(text="Settings").sibling(className="android.widget.ImageView")
  ```

---

### Unsupported Methods

> ⚠️ Please avoid using the following methods as they are **not supported** for blacklist configuration:

- Positional relations based queries:  

  ```python
  d(A).left(B)    # Select B to the left of A
  d(A).right(B)   # Select B to the right of A
  d(A).up(B)      # Select B above A
  d(A).down(B)    # Select B below A
  ```

- Child querying methods such as `child_by_text`, `child_by_description`, and `child_by_instance`. For example:

  ```python
  d(className="android.widget.ListView", resourceId="android:id/list") \
    .child_by_text("Bluetooth", className="android.widget.LinearLayout")
  
  d(className="android.widget.ListView", resourceId="android:id/list") \
    .child_by_text(
      "Bluetooth",
      allow_scroll_search=True,  # default False
      className="android.widget.LinearLayout"
    )
  ```
- Using instance parameter to locate elements. For example, avoid:

 ```python
    d(className="android.widget.Button", instance=2)
  ```

- Regular expression matching parameters:  
  `textMatches`, `classNameMatches`, `descriptionMatches`, `packageNameMatches`, `resourceIdMatches`


Please avoid using these unsupported methods to ensure your blacklist configurations are applied correctly.

