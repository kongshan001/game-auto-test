# src/action/ — 执行层

执行层负责模拟用户输入和管理游戏窗口，是框架的"手"。

## 文件说明

| 文件 | 类 | 职责 |
|------|---|------|
| `input_executor.py` | `ActionExecutor` | 统一输入执行器。基于 pydirectinput 模拟鼠标和键盘操作，支持点击、双击、右键、文本输入、按键、组合键、滚动、拖拽。内置窗口坐标转换 |
| `window_manager.py` | `WindowManager` / `WindowInfo` | Windows 窗口管理器。通过 win32gui/pygetwindow 按标题、进程名、PID 查找窗口，支持窗口激活和等待窗口出现 |

## ActionExecutor 支持的动作

| 方法 | 说明 | 关键参数 |
|------|------|----------|
| `click()` | 单击（支持字符串目标或坐标） | target, button |
| `double_click()` | 双击 | target |
| `right_click()` | 右键点击 | target |
| `type_text()` | 逐字符输入文本 | text, target, clear_first |
| `press_key()` | 按单个键 | key |
| `press_keys()` | 组合键（如 Ctrl+C） | keys[] |
| `scroll()` | 鼠标滚轮 | clicks |
| `drag()` | 拖拽操作 | start, end, duration |
| `wait()` | 等待指定秒数 | seconds |

## WindowInfo 数据结构

```python
@dataclass
class WindowInfo:
    hwnd: int          # 窗口句柄
    title: str         # 窗口标题
    left, top: int     # 窗口左上角坐标
    width, height: int # 窗口尺寸
    process_id: int    # 进程 ID
```

## 依赖关系

- `input_executor.py` -> pydirectinput（必须）、win32api（可选备用）、`element_locator.ElementLocator`（用于文本目标定位）
- `window_manager.py` -> win32gui、win32con、win32process、pygetwindow

## 关键约定

- 坐标转换：`_to_absolute()` 将窗口相对坐标转屏幕绝对坐标，`_to_relative()` 反向转换
- pydirectinput 启用 FAILSAFE 安全机制（鼠标移至左上角中止程序）
- 点击目标支持字符串描述（需配合 ElementLocator）或 (x, y) 坐标元组
- 输入延迟可配置：click_delay=0.5s, type_delay=0.1s, keypress_delay=0.3s
