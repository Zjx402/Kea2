# Expert System

> All configuration files are located in the `configs` directory.

---

## Custom Input Method (Auto Input + Input Bar Masking)

**ADBKeyBoard** automatically inputs content into the input field and blocks the UI input method.

**Use Case:**
When encountering random input in the search bar and needing to input specified characters.

**Environment Setup:**
Download ADBKeyBoard and set it as the default input method on the phone.

> [ADBKeyBoard download link](https://github.com/senzhk/ADBKeyBoard/blob/master/ADBKeyboard.apk)  
> After activation, when encountering an input field, ADBKeyBoard will not pop up the UI input method but will show **ADB Keyboard {ON}** on the toolbar.


### Random Input String

- Configuration in `configs/max.config`:  
  `max.randomPickFromStringList = false`  

  - On PC, create a file named `max.config` (file name cannot be changed), and input:  
    ```
    max.randomPickFromStringList = false
    ```
  - Push the file to the phone with the command:  
    ```
    adb push configs/max.config /sdcard
    ```

### Random input by reading strings from file

- Configuration in `configs/max.config`:  
  `max.randomPickFromStringList = true`

  - On PC, create a file named `max.strings` (file name cannot be changed), input the strings you want to enter, each string ends with a newline.

  - Push file to the phone with:  
    ```
    adb push configs/max.strings /sdcard
    ```



### Fuzzing Text Input to Text Controls

- Place a file named `max.fuzzing.strings` inside the `configs` directory of the project (existence activates fuzzing), reference strings can be found here:  
  [https://github.com/danielmiessler/SecLists/blob/master/Fuzzing/big-list-of-naughty-strings.txt](https://github.com/danielmiessler/SecLists/blob/master/Fuzzing/big-list-of-naughty-strings.txt)

- Input desired strings in the file, each string on a new line.

- Push the file to the phone with:  
  ```
  adb push configs/max.fuzzing.strings /sdcard
  ```
  
- Fuzzing probabilities
  1. 50% chance to input a string randomly selected from `fuzzing.strings`.  
  2. 35% chance to input text/description from historical pages of the tested app (if no `max.fuzzing.strings` file exists, chance increases to 85%).  
  3. 15% chance to input nothing.

---

## Custom Event Sequence

Manually configure the Activity path (for UI automation test cases).

**Use Case:**
To cover scenarios not fully reached by automation, by manually defining sequences that Fastbot cannot traverse (e.g., pre-login steps).

- On PC, create a file named `max.xpath.actions` (file name fixed).

- Event Sequence Configuration (case)

| Field      | Description                                               |
|------------|-----------------------------------------------------------|
| prob       | Probability of occurrence. `"prob": 1` means 100%.        |
| activity   | Belonging scene (refer to section "Get Current Activity") |
| times      | Number of repetitions (default 1)                         |
| actions    | List of action steps                                      |
| throttle   | Interval between actions in milliseconds                  |

- Supported `action` types (uppercase only)

| Action            | Description                             | Notes                                   |
|-------------------|-------------------------------------|-----------------------------------------|
| CLICK             | Click                               | If `text` is provided, enter text.      |
| LONG_CLICK        | Long press                         |                                         |
| BACK              | Go back                            |                                         |
| SCROLL_TOP_DOWN   | Scroll from top to bottom           |                                         |
| SCROLL_BOTTOM_UP  | Scroll from bottom to top           |                                         |
| SCROLL_LEFT_RIGHT | Scroll from left to right           |                                         |
| SCROLL_RIGHT_LEFT | Scroll from right to left           |                                         |

> **Note:** If switching pages occurs:
> - The `activity` will change, and `actions` should be split accordingly (no need to split if within the same activity).  
> - Format as shown in the figure below: write the next `activity` starting from `prob`.

- After finishing file creation, validate on [json.cn](https://json.cn) then push to device:  
```
adb push configs/max.xpath.actions /sdcard
```

- Useful Tips

  - Getting package name (requires properly configured ADB commands):

    ```bash
    aapt dump badging [apk_path]
    # On Mac, drag the APK file onto the terminal.
    ```

  - Get current control's activity using Maxim:

    ```bash
    adb shell CLASSPATH=/sdcard/monkey.jar:/sdcard/framework.jar exec app_process /system/bin tv.panda.test.monkey.api.CurrentActivity
    ```
    
  - Locate current page controls

    Use Android SDK's GUI inspection tool **UiAutomatorViewer** (SDK must be configured):  
    ```
    ${ANDROID_HOME}/tools/bin/uiautomatorviewer
    ```

    > For Mac users, `uiautomatorviewer` may encounter errors. See solution:  
    > https://github.com/android/android-test/issues/911#issuecomment-849389068

  - View current tree structure with Maxim:

    ```bash
    adb shell CLASSPATH=/sdcard/monkey.jar:/sdcard/framework.jar exec app_process /system/bin tv.panda.test.monkey.api.Dumptree
    ```

    - Use Fastbot `--top-activity` command to identify current device activity info:

      ```bash
      adb shell CLASSPATH=/sdcard/monkeyq.jar:/sdcard/framework.jar:/sdcard/fastbot-thirdpart.jar exec app_process /system/bin com.android.commands.monkey.Monkey --top-activity
      ```

      Sample output:
      ```
      [Fastbot][2023-08-03 20:37:20.108] Top activity name is:com.ss.android.article.news.activity.MainActivity
      [Fastbot][2023-08-03 20:37:20.108] Top package name is:com.ss.android.article.news
      [Fastbot][2023-08-03 20:37:20.108] Top short activity name is:.activity.MainActivity
      ```

> Use this information when writing custom test sequences (`max.xpath.actions`). However, the test sequences defined here can all be replaced by property-based methods. We strongly recommend using our Kea2 property-based testing approach.



---


## Schema Event Support

App needs to support third-party execution via Intents for Schema jumps.

- Create a file called `max.schema` on PC.

- Push to `/sdcard`:

```
adb push configs/max.schema /sdcard
```

- Add to `max.config`:

```
max.execSchema = true
max.execSchemaEveryStartup = true  # Execute schema on every app startup
```

Schema events run by default after app startup.

---

## Automatic Permission Granting

By default, Fastbot grants all required app permissions before app launch.

To test dynamic permission popups manually, configure `configs/max.config` with:

```
max.grantAllPermission = false
```

Then add related popup packages in shell command (one or more):

```
-p com.android.packageinstaller
-p com.android.permissioncontroller
-p com.lbe.security.miui            # for MIUI Android 10
-p com.samsung.android.permissioncontroller # for Samsung Android 10
```

This helps to dismiss permission dialogs during runtime.

---

## Fuzzing Dataset (New)

Provides various image and video materials for use during traversal.

Execute shell commands:

```bash
adb push data/fuzzing/ /sdcard
adb shell am broadcast -a android.intent.action.MEDIA_SCANNER_SCAN_FILE -d file:///sdcard/fuzzing
```

---

## Add Fuzz and Mutation Events (New)

After model inference triggers an action, with a probability defined by fuzzingRate, generate 5-10 fuzz sequences composed of the following events in random order.

- Create or update `configs/max.config` on PC with:

```properties
max.fuzzingRate = 0.01D  # total probability for fuzz events (0.01 = 1%)

# Included fuzzing events probabilities (default):
max.doRotateFuzzing = 0.15
max.doAppSwitchFuzzing = 0.15
max.doTrackballFuzzing = 0.15
max.doNavKeyFuzzing = 0.15
max.doKeyCodeFuzzing = 0.15
max.doSystemKeyFuzzing = 0.15
max.doDragFuzzing = 0.5
max.doPinchZoomFuzzing = 0.15
max.doClickFuzzing = 0.7

max.startMutation = 0.3D  # Chance mutation is enabled immediately after Fastbot starts (30% default)

# Mutation event probabilities (part of total event probability):
max.doMutationAirplaneFuzzing = 0.001
max.doMutationMutationAlwaysFinishActivitysFuzzing = 0.1
max.doMutationWifiFuzzing = 0.001
```

> Note: Airplane mode and wifi switch mutations will be reset after Fastbot execution.

- Push `max.config` to device:

```
adb push configs/max.config /sdcard
```

