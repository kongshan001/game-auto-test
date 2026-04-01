# API 参考文档

本文档涵盖 `src/` 下全部 12 个模块的公共 API，按模块分组，包含签名、参数表、返回值和异常信息。

---

## 1. main — 程序入口

> 模块路径: `src/main.py`

### GameAutoTester

游戏自动化测试器，编排 ReAct 主循环（初始化 -> 截屏 -> 决策 -> 执行 -> 状态记录）。

#### `__init__(self, config: Config)`

初始化测试器，创建并组装所有子模块实例。

| 参数 | 类型 | 说明 |
|------|------|------|
| `config` | `Config` | 框架配置实例 |

#### `initialize(self) -> None`

初始化测试环境：启动游戏、等待窗口、激活窗口、创建 DecisionAgent、开始测试计时。

**异常:**

| 异常类型 | 触发条件 |
|----------|----------|
| `RuntimeError` | 无法获取游戏窗口 |

#### `execute_action(self, action: dict) -> bool`

根据动作字典分发并执行具体操作（click / type / keypress / wait / assert / done）。

| 参数 | 类型 | 说明 |
|------|------|------|
| `action` | `dict` | 动作指令，需包含 `"action"` 键及对应参数 |

| 返回值 | 说明 |
|--------|------|
| `bool` | 执行是否成功 |

#### `run(self) -> None`

运行完整测试流程。执行 ReAct 推理主循环，直到收到 `"done"` 动作或达到 `max_steps` 上限。

**异常:**

| 异常类型 | 触发条件 |
|----------|----------|
| `KeyboardInterrupt` | 用户手动中断 |
| `Exception` | 测试执行出错 |

#### `cleanup(self) -> None`

清理资源：保存测试记录、显示测试摘要、关闭游戏进程、关闭 GLM 客户端。

---

### setup_logging

```python
setup_logging(log_level: str = "INFO") -> None
```

配置日志系统，同时输出到控制台和 `logs/test.log` 文件。

| 参数 | 类型 | 说明 |
|------|------|------|
| `log_level` | `str` | 日志级别，默认 `"INFO"` |

---

## 2. agents.decision_agent — 决策引擎

> 模块路径: `src/agents/decision_agent.py`

### DecisionAgent

AI 决策引擎，支持 ReAct（推理+行动）模式。将截图和历史上下文发送给 GLM-4V，解析返回的结构化 JSON 动作指令。

#### `__init__(self, glm_client, test_case: str, state_memory, temperature: float = 0.2, use_react: bool = True, max_retry_same_action: int = 3)`

| 参数 | 类型 | 说明 |
|------|------|------|
| `glm_client` | `GLMClient` | GLM API 客户端实例 |
| `test_case` | `str` | 测试用例描述 |
| `state_memory` | `StateMemory` | 状态记忆实例 |
| `temperature` | `float` | 生成温度，默认 0.2 |
| `use_react` | `bool` | 是否启用 ReAct 模式，默认 `True` |
| `max_retry_same_action` | `int` | 同一动作最大重试次数，默认 3 |

#### `decide(self, image: Image.Image, scene_description: Optional[str] = None, ocr_engine=None) -> Dict[str, Any]`

根据当前画面决定下一步动作。构建 ReAct Prompt，调用 GLM-4V 推理，解析 JSON 响应。

| 参数 | 类型 | 说明 |
|------|------|------|
| `image` | `PIL.Image.Image` | 当前截图 |
| `scene_description` | `Optional[str]` | 可选的场景描述文本 |
| `ocr_engine` | `Optional[OCREngine]` | OCR 引擎（用于提取画面文本） |

| 返回值 | 说明 |
|--------|------|
| `Dict[str, Any]` | 包含 `"reasoning"`（推理过程）、`"action"`（动作字典）、可选 `"warning"` |

#### `validate_action(self, action: Dict[str, Any]) -> bool`

验证动作格式是否合法。检查动作类型是否在白名单中，以及必要参数是否存在。

| 参数 | 类型 | 说明 |
|------|------|------|
| `action` | `Dict[str, Any]` | 待验证的动作字典 |

| 返回值 | 说明 |
|--------|------|
| `bool` | 动作是否合法 |

**合法动作类型:** `click`（需 target）、`type`（需 target + text）、`keypress`（需 key）、`wait`、`assert`（需 condition）、`done`。

---

## 3. agents.state_memory — 状态记忆

> 模块路径: `src/agents/state_memory.py`

### ActionRecord

单条动作记录的数据类。

```python
@dataclass
class ActionRecord:
    step: int
    action: str
    target: str
    description: str
    timestamp: float = field(default_factory=time.time)
    success: bool = True
    error: Optional[str] = None
    screenshot_path: Optional[str] = None
```

| 字段 | 类型 | 说明 |
|------|------|------|
| `step` | `int` | 步骤序号 |
| `action` | `str` | 动作类型 |
| `target` | `str` | 动作目标 |
| `description` | `str` | 动作描述 |
| `timestamp` | `float` | 时间戳 |
| `success` | `bool` | 是否成功 |
| `error` | `Optional[str]` | 错误信息 |
| `screenshot_path` | `Optional[str]` | 截图路径 |

#### `to_dict(self) -> Dict[str, Any]`

转换为字典。

| 返回值 | 说明 |
|--------|------|
| `Dict[str, Any]` | 字典形式的动作记录 |

#### `to_prompt_text(self) -> str`

转换为适合注入 Prompt 的文本。

| 返回值 | 说明 |
|--------|------|
| `str` | 格式: `"步骤{step}: {action} {target} - {description}"` |

---

### StateMemory

测试状态记忆，管理动作历史和测试生命周期。

#### `__init__(self, max_history: int = 20)`

| 参数 | 类型 | 说明 |
|------|------|------|
| `max_history` | `int` | 最大保留历史条数，默认 20 |

#### `set_test_case(self, test_case: str) -> None`

设置测试用例，自动提取测试目标。

| 参数 | 类型 | 说明 |
|------|------|------|
| `test_case` | `str` | 测试用例文本 |

#### `add_action(self, action: str, target: str, description: str = "", success: bool = True, error: Optional[str] = None) -> None`

添加一条动作记录。超过 `max_history` 时自动裁剪旧记录。

| 参数 | 类型 | 说明 |
|------|------|------|
| `action` | `str` | 动作类型 |
| `target` | `str` | 动作目标 |
| `description` | `str` | 动作描述 |
| `success` | `bool` | 是否成功 |
| `error` | `Optional[str]` | 错误信息 |

#### `get_recent_actions(self, n: int = 5) -> List[ActionRecord]`

获取最近 N 条动作记录。

| 参数 | 类型 | 说明 |
|------|------|------|
| `n` | `int` | 数量，默认 5 |

| 返回值 | 说明 |
|--------|------|
| `List[ActionRecord]` | 最近 N 条动作记录 |

#### `get_history_prompt(self, n: int = 5) -> str`

获取历史动作的 Prompt 文本。

| 参数 | 类型 | 说明 |
|------|------|------|
| `n` | `int` | 最近 N 条 |

| 返回值 | 说明 |
|--------|------|
| `str` | 每行一条记录的文本 |

#### `start_test(self) -> None`

开始测试，记录起始时间。

#### `end_test(self, success: bool = True) -> None`

结束测试，记录结束时间。

| 参数 | 类型 | 说明 |
|------|------|------|
| `success` | `bool` | 测试是否成功 |

#### `get_duration(self) -> Optional[float]`

获取测试持续时间。

| 返回值 | 说明 |
|--------|------|
| `Optional[float]` | 持续秒数，未开始则返回 `None` |

#### `is_completed(self) -> bool`

检查测试是否已完成。

| 返回值 | 说明 |
|--------|------|
| `bool` | 是否已完成 |

#### `get_summary(self) -> Dict[str, Any]`

获取测试摘要。

| 返回值 | 说明 |
|--------|------|
| `Dict[str, Any]` | 包含 `test_case`、`test_goal`、`total_steps`、`success_steps`、`failed_steps`、`duration`、`completed` |

#### `to_json(self) -> str`

序列化为 JSON 字符串。

| 返回值 | 说明 |
|--------|------|
| `str` | JSON 格式的测试记录 |

#### `save_to_file(self, filepath: str) -> None`

保存测试记录到文件。

| 参数 | 类型 | 说明 |
|------|------|------|
| `filepath` | `str` | 输出文件路径 |

---

## 4. agents.test_case_parser — 用例解析器

> 模块路径: `src/agents/test_case_parser.py`

### TestCaseParser

自然语言测试用例解析器。从中文描述中提取测试目标、步骤、断言和测试数据。

#### `parse(test_case: str) -> Dict[str, Any]` (静态方法)

解析测试用例文本，返回结构化结果。

| 参数 | 类型 | 说明 |
|------|------|------|
| `test_case` | `str` | 自然语言测试用例 |

| 返回值 | 说明 |
|--------|------|
| `Dict[str, Any]` | 包含 `goal`、`steps`、`assertions`、`data`、`raw` 的字典 |

#### `to_prompt(test_case_parsed: Dict[str, Any]) -> str` (静态方法)

将解析后的测试用例转换为 Prompt 文本。

| 参数 | 类型 | 说明 |
|------|------|------|
| `test_case_parsed` | `Dict[str, Any]` | `parse()` 的返回结果 |

| 返回值 | 说明 |
|--------|------|
| `str` | 格式化的 Prompt 文本 |

---

## 5. vision.screen_capture — 屏幕捕获

> 模块路径: `src/vision/screen_capture.py`

### ScreenCapture

基于 mss 的屏幕捕获器，支持全屏、窗口区域和自定义区域截图。

#### `__init__(self, window_info=None, save_path: str = "./logs/screenshots")`

| 参数 | 类型 | 说明 |
|------|------|------|
| `window_info` | `Optional[WindowInfo]` | 目标窗口信息 |
| `save_path` | `str` | 截图保存目录，默认 `"./logs/screenshots"` |

#### `set_window(self, window_info) -> None`

设置目标窗口信息。

| 参数 | 类型 | 说明 |
|------|------|------|
| `window_info` | `WindowInfo` | 窗口信息实例 |

#### `capture(self, region: Optional[Tuple[int, int, int, int]] = None) -> Image.Image`

捕获屏幕截图。

| 参数 | 类型 | 说明 |
|------|------|------|
| `region` | `Optional[Tuple[int, int, int, int]]` | 截取区域 `(x, y, width, height)`，相对于窗口；`None` 则捕获整个窗口或全屏 |

| 返回值 | 说明 |
|--------|------|
| `PIL.Image.Image` | RGB 格式截图 |

#### `capture_to_numpy(self, region: Optional[Tuple[int, int, int, int]] = None) -> np.ndarray`

捕获屏幕并返回 numpy 数组。

| 参数 | 类型 | 说明 |
|------|------|------|
| `region` | `Optional[Tuple[int, int, int, int]]` | 截取区域 |

| 返回值 | 说明 |
|--------|------|
| `np.ndarray` | HWC 格式的 RGB 数组 |

#### `save_screenshot(self, filename: Optional[str] = None, region: Optional[Tuple[int, int, int, int]] = None) -> str`

保存截图到文件。

| 参数 | 类型 | 说明 |
|------|------|------|
| `filename` | `Optional[str]` | 文件名，`None` 则自动生成时间戳文件名 |
| `region` | `Optional[Tuple[int, int, int, int]]` | 截取区域 |

| 返回值 | 说明 |
|--------|------|
| `str` | 保存的文件路径 |

#### `capture_and_save(self, step: int, action: str = "", region: Optional[Tuple[int, int, int, int]] = None) -> str`

捕获并保存截图，文件名包含步骤编号和动作信息。

| 参数 | 类型 | 说明 |
|------|------|------|
| `step` | `int` | 步骤编号 |
| `action` | `str` | 动作描述 |
| `region` | `Optional[Tuple[int, int, int, int]]` | 截取区域 |

| 返回值 | 说明 |
|--------|------|
| `str` | 保存的文件路径 |

---

## 6. vision.ocr_engine — OCR 文字识别

> 模块路径: `src/vision/ocr_engine.py`

### OCREngine

基于 EasyOCR 的文字识别引擎，支持中英文识别。Reader 实例采用懒加载策略。

#### `__init__(self, languages: List[str] = None, use_gpu: bool = False)`

| 参数 | 类型 | 说明 |
|------|------|------|
| `languages` | `Optional[List[str]]` | 语言列表，默认 `["ch_sim", "en"]` |
| `use_gpu` | `bool` | 是否使用 GPU 加速，默认 `False` |

#### `reader` (属性)

懒加载的 EasyOCR Reader 实例。首次访问时初始化，后续调用复用。

| 返回值 | 说明 |
|--------|------|
| `easyocr.Reader` | OCR 读取器 |

**异常:**

| 异常类型 | 触发条件 |
|----------|----------|
| `ImportError` | easyocr 未安装 |

#### `recognize(self, image: Image.Image, detail: int = 1) -> List[Tuple[str, List[List[int]]]]`

识别图像中的文字。

| 参数 | 类型 | 说明 |
|------|------|------|
| `image` | `PIL.Image.Image` | 输入图像 |
| `detail` | `int` | `0` 仅返回文本列表；`1` 返回 `(text, bbox, confidence)` 元组列表 |

| 返回值 | 说明 |
|--------|------|
| `List` | `detail=0` 时为 `List[str]`；`detail=1` 时为 `List[Tuple[str, bbox, float]]` |

#### `search_text(self, image: Image.Image, search_term: str, confidence_threshold: float = 0.5) -> List[Dict]`

在图像中搜索指定文本。

| 参数 | 类型 | 说明 |
|------|------|------|
| `image` | `PIL.Image.Image` | 输入图像 |
| `search_term` | `str` | 搜索文本 |
| `confidence_threshold` | `float` | 置信度阈值，默认 0.5 |

| 返回值 | 说明 |
|--------|------|
| `List[Dict]` | 每项包含 `text`、`bbox`、`confidence`、`center` `(x, y)` |

#### `find_text_position(self, image: Image.Image, search_term: str, confidence_threshold: float = 0.5) -> Optional[Tuple[int, int]]`

查找文本在图像中的中心坐标（置信度最高的匹配）。

| 参数 | 类型 | 说明 |
|------|------|------|
| `image` | `PIL.Image.Image` | 输入图像 |
| `search_term` | `str` | 搜索文本 |
| `confidence_threshold` | `float` | 置信度阈值 |

| 返回值 | 说明 |
|--------|------|
| `Optional[Tuple[int, int]]` | `(x, y)` 坐标，未找到返回 `None` |

#### `get_all_text_with_positions(self, image: Image.Image, confidence_threshold: float = 0.3) -> List[Dict]`

获取图像中所有文本及其位置。

| 参数 | 类型 | 说明 |
|------|------|------|
| `image` | `PIL.Image.Image` | 输入图像 |
| `confidence_threshold` | `float` | 置信度阈值，默认 0.3 |

| 返回值 | 说明 |
|--------|------|
| `List[Dict]` | 每项包含 `text`、`bbox`、`center`、`confidence` |

---

## 7. vision.element_locator — 元素定位

> 模块路径: `src/vision/element_locator.py`

### ElementLocator

多策略元素定位器，按优先级组合 OCR 文本定位、GLM 视觉定位、OpenCV 模板匹配和颜色定位。

#### `__init__(self, ocr_engine=None, glm_client=None, window_info=None)`

| 参数 | 类型 | 说明 |
|------|------|------|
| `ocr_engine` | `Optional[OCREngine]` | OCR 引擎实例 |
| `glm_client` | `Optional[GLMClient]` | GLM 客户端实例 |
| `window_info` | `Optional[WindowInfo]` | 窗口信息 |

#### `locate_by_text(self, image: Image.Image, description: str, confidence_threshold: float = 0.5) -> Optional[Tuple[int, int, int, int]]`

根据文本描述定位元素。优先使用 OCR，失败后回退到 GLM 视觉定位。

| 参数 | 类型 | 说明 |
|------|------|------|
| `image` | `PIL.Image.Image` | 当前截图 |
| `description` | `str` | 元素描述（如 "登录按钮"） |
| `confidence_threshold` | `float` | OCR 置信度阈值 |

| 返回值 | 说明 |
|--------|------|
| `Optional[Tuple[int, int, int, int]]` | `(x, y, width, height)` 或 `None` |

#### `locate_by_template(self, image: Image.Image, template_path: str, threshold: float = 0.8) -> Optional[Tuple[int, int, int, int]]`

使用 OpenCV 模板匹配定位元素。

| 参数 | 类型 | 说明 |
|------|------|------|
| `image` | `PIL.Image.Image` | 当前截图 |
| `template_path` | `str` | 模板图像文件路径 |
| `threshold` | `float` | 匹配阈值，默认 0.8 |

| 返回值 | 说明 |
|--------|------|
| `Optional[Tuple[int, int, int, int]]` | `(x, y, width, height)` 或 `None` |

#### `locate_by_color(self, image: Image.Image, color_range: Tuple[Tuple[int, int, int], Tuple[int, int, int]], min_area: int = 100) -> List[Tuple[int, int, int, int]]`

根据 HSV 颜色范围定位元素。

| 参数 | 类型 | 说明 |
|------|------|------|
| `image` | `PIL.Image.Image` | 当前截图 |
| `color_range` | `Tuple[Tuple[int, int, int], Tuple[int, int, int]]` | HSV 范围 `((h_min, s_min, v_min), (h_max, s_max, v_max))` |
| `min_area` | `int` | 最小区域面积（像素），默认 100 |

| 返回值 | 说明 |
|--------|------|
| `List[Tuple[int, int, int, int]]` | 匹配的边界框列表 |

#### `get_element_center(self, image: Image.Image, description: str) -> Optional[Tuple[int, int]]`

获取元素的屏幕绝对中心坐标。先调用 `locate_by_text` 定位，再转换为绝对坐标。

| 参数 | 类型 | 说明 |
|------|------|------|
| `image` | `PIL.Image.Image` | 当前截图 |
| `description` | `str` | 元素描述 |

| 返回值 | 说明 |
|--------|------|
| `Optional[Tuple[int, int]]` | `(x, y)` 屏幕绝对坐标，或 `None` |

---

## 8. action.input_executor — 动作执行器

> 模块路径: `src/action/input_executor.py`

### ActionExecutor

统一输入执行器，基于 pydirectinput 模拟硬件级鼠标和键盘操作。

#### `__init__(self, window_info=None, click_delay: float = 0.5, type_delay: float = 0.1, keypress_delay: float = 0.3)`

| 参数 | 类型 | 说明 |
|------|------|------|
| `window_info` | `Optional[WindowInfo]` | 窗口信息（用于坐标转换） |
| `click_delay` | `float` | 点击后等待秒数，默认 0.5 |
| `type_delay` | `float` | 逐字符输入间隔秒数，默认 0.1 |
| `keypress_delay` | `float` | 按键后等待秒数，默认 0.3 |

#### `click(self, target: Union[str, Tuple[int, int]], image: Optional[Image.Image] = None, locator: Optional[Any] = None, button: str = "left") -> bool`

点击目标。

| 参数 | 类型 | 说明 |
|------|------|------|
| `target` | `Union[str, Tuple[int, int]]` | 目标描述文本或 `(x, y)` 坐标 |
| `image` | `Optional[Image.Image]` | 当前截图（文本目标定位时需要） |
| `locator` | `Optional[ElementLocator]` | 元素定位器（文本目标定位时需要） |
| `button` | `str` | 鼠标按钮: `"left"` / `"right"` / `"middle"` |

| 返回值 | 说明 |
|--------|------|
| `bool` | 是否成功 |

**异常:**

| 异常类型 | 触发条件 |
|----------|----------|
| `RuntimeError` | pydirectinput 不可用 |
| `ValueError` | 文本目标未提供 locator |

#### `double_click(self, target: Union[str, Tuple[int, int]], image: Optional[Image.Image] = None, locator: Optional[Any] = None) -> bool`

双击目标。

| 参数 | 类型 | 说明 |
|------|------|------|
| `target` | `Union[str, Tuple[int, int]]` | 目标描述或坐标 |
| `image` | `Optional[Image.Image]` | 当前截图 |
| `locator` | `Optional[ElementLocator]` | 元素定位器 |

| 返回值 | 说明 |
|--------|------|
| `bool` | 是否成功 |

#### `right_click(self, target: Union[str, Tuple[int, int]], image: Optional[Image.Image] = None, locator: Optional[Any] = None) -> bool`

右键点击目标。内部调用 `click()` 并传入 `button="right"`。

| 参数 | 类型 | 说明 |
|------|------|------|
| `target` | `Union[str, Tuple[int, int]]` | 目标描述或坐标 |
| `image` | `Optional[Image.Image]` | 当前截图 |
| `locator` | `Optional[ElementLocator]` | 元素定位器 |

| 返回值 | 说明 |
|--------|------|
| `bool` | 是否成功 |

#### `type_text(self, text: str, target: Union[str, Tuple[int, int], None] = None, image: Optional[Image.Image] = None, locator: Optional[Any] = None, clear_first: bool = False) -> bool`

输入文本。可先点击目标输入框，逐字符输入以确保可靠性。

| 参数 | 类型 | 说明 |
|------|------|------|
| `text` | `str` | 要输入的文本 |
| `target` | `Union[str, Tuple[int, int], None]` | 输入目标（先点击再输入），`None` 则直接输入 |
| `image` | `Optional[Image.Image]` | 当前截图 |
| `locator` | `Optional[ElementLocator]` | 元素定位器 |
| `clear_first` | `bool` | 是否先清除已有内容（Ctrl+A + Backspace） |

| 返回值 | 说明 |
|--------|------|
| `bool` | 是否成功 |

#### `press_key(self, key: str) -> bool`

按下单个按键。

| 参数 | 类型 | 说明 |
|------|------|------|
| `key` | `str` | 按键名称（如 `"enter"`、`"esc"`、`"a"`） |

| 返回值 | 说明 |
|--------|------|
| `bool` | 是否成功 |

#### `press_keys(self, keys: list) -> bool`

组合按键。

| 参数 | 类型 | 说明 |
|------|------|------|
| `keys` | `list` | 按键列表（如 `["ctrl", "c"]`） |

| 返回值 | 说明 |
|--------|------|
| `bool` | 是否成功 |

#### `wait(self, seconds: float) -> bool`

等待指定秒数。

| 参数 | 类型 | 说明 |
|------|------|------|
| `seconds` | `float` | 等待时长 |

| 返回值 | 说明 |
|--------|------|
| `bool` | 始终返回 `True` |

#### `scroll(self, clicks: int, x: Optional[int] = None, y: Optional[int] = None) -> bool`

滚动鼠标滚轮。

| 参数 | 类型 | 说明 |
|------|------|------|
| `clicks` | `int` | 滚动量（正数向上，负数向下） |
| `x` | `Optional[int]` | 鼠标 X 坐标（可选） |
| `y` | `Optional[int]` | 鼠标 Y 坐标（可选） |

| 返回值 | 说明 |
|--------|------|
| `bool` | 是否成功 |

#### `drag(self, start: Tuple[int, int], end: Tuple[int, int], duration: float = 0.5) -> bool`

拖拽操作。分段移动以实现平滑拖拽。

| 参数 | 类型 | 说明 |
|------|------|------|
| `start` | `Tuple[int, int]` | 起点坐标 |
| `end` | `Tuple[int, int]` | 终点坐标 |
| `duration` | `float` | 拖拽持续时间（秒），默认 0.5 |

| 返回值 | 说明 |
|--------|------|
| `bool` | 是否成功 |

---

## 9. action.window_manager — 窗口管理

> 模块路径: `src/action/window_manager.py`

### WindowInfo

窗口信息数据类。

```python
@dataclass
class WindowInfo:
    hwnd: int
    title: str
    left: int
    top: int
    width: int
    height: int
    process_id: int
```

| 字段 | 类型 | 说明 |
|------|------|------|
| `hwnd` | `int` | 窗口句柄 |
| `title` | `str` | 窗口标题 |
| `left` | `int` | 窗口左上角 X |
| `top` | `int` | 窗口左上角 Y |
| `width` | `int` | 窗口宽度 |
| `height` | `int` | 窗口高度 |
| `process_id` | `int` | 所属进程 ID |

**属性:**

| 属性 | 类型 | 说明 |
|------|------|------|
| `center` | `Tuple[int, int]` | 窗口中心坐标 `(left + width//2, top + height//2)` |
| `rect` | `Tuple[int, int, int, int]` | 窗口矩形 `(left, top, right, bottom)` |

---

### WindowManager

Windows 窗口管理器，基于 win32gui 和 pygetwindow。

#### `__init__(self)`

初始化窗口管理器。

#### `get_window_by_title(self, title: str) -> Optional[WindowInfo]`

根据窗口标题查找窗口。

| 参数 | 类型 | 说明 |
|------|------|------|
| `title` | `str` | 窗口标题（模糊匹配） |

| 返回值 | 说明 |
|--------|------|
| `Optional[WindowInfo]` | 窗口信息，未找到返回 `None` |

#### `get_window_by_process_name(self, process_name: str) -> Optional[WindowInfo]`

根据进程名查找窗口。

| 参数 | 类型 | 说明 |
|------|------|------|
| `process_name` | `str` | 进程名 |

| 返回值 | 说明 |
|--------|------|
| `Optional[WindowInfo]` | 窗口信息，未找到返回 `None` |

#### `get_window_by_pid(self, pid: int) -> Optional[WindowInfo]`

根据进程 ID 查找窗口。

| 参数 | 类型 | 说明 |
|------|------|------|
| `pid` | `int` | 进程 ID |

| 返回值 | 说明 |
|--------|------|
| `Optional[WindowInfo]` | 窗口信息，未找到返回 `None` |

#### `activate_window(self, hwnd: int) -> bool`

激活窗口（置顶并设为前台窗口）。

| 参数 | 类型 | 说明 |
|------|------|------|
| `hwnd` | `int` | 窗口句柄 |

| 返回值 | 说明 |
|--------|------|
| `bool` | 是否成功 |

#### `wait_for_window(self, process: subprocess.Popen, timeout: int = 30, title: Optional[str] = None) -> Optional[WindowInfo]`

等待窗口出现。轮询查找，直到超时。

| 参数 | 类型 | 说明 |
|------|------|------|
| `process` | `subprocess.Popen` | 游戏进程 |
| `timeout` | `int` | 超时秒数，默认 30 |
| `title` | `Optional[str]` | 窗口标题（额外匹配条件） |

| 返回值 | 说明 |
|--------|------|
| `Optional[WindowInfo]` | 窗口信息，超时返回 `None` |

#### `is_window_valid(self, hwnd: int) -> bool`

检查窗口是否有效且可见。

| 参数 | 类型 | 说明 |
|------|------|------|
| `hwnd` | `int` | 窗口句柄 |

| 返回值 | 说明 |
|--------|------|
| `bool` | 窗口是否有效 |

---

## 10. game.game_launcher — 游戏启动器

> 模块路径: `src/game/game_launcher.py`

### GameLauncher

游戏进程管理器，负责启动、关闭和重启游戏。

#### `__init__(self, exe_path: str, window_title: Optional[str] = None, startup_delay: int = 5)`

| 参数 | 类型 | 说明 |
|------|------|------|
| `exe_path` | `str` | 游戏可执行文件路径 |
| `window_title` | `Optional[str]` | 窗口标题（用于查找窗口） |
| `startup_delay` | `int` | 启动后等待秒数，默认 5 |

#### `launch(self, args: list = None, cwd: Optional[str] = None) -> subprocess.Popen`

启动游戏进程。

| 参数 | 类型 | 说明 |
|------|------|------|
| `args` | `Optional[list]` | 启动参数列表 |
| `cwd` | `Optional[str]` | 工作目录 |

| 返回值 | 说明 |
|--------|------|
| `subprocess.Popen` | 游戏进程对象 |

**异常:**

| 异常类型 | 触发条件 |
|----------|----------|
| `FileNotFoundError` | 可执行文件不存在 |

#### `is_running(self) -> bool`

检查游戏进程是否仍在运行。

| 返回值 | 说明 |
|--------|------|
| `bool` | 进程是否存活 |

#### `close(self, force: bool = False) -> bool`

关闭游戏进程。

| 参数 | 类型 | 说明 |
|------|------|------|
| `force` | `bool` | `True` 强制 kill，`False` 先 terminate 再等待 5 秒超时后 kill |

| 返回值 | 说明 |
|--------|------|
| `bool` | 是否成功关闭 |

#### `restart(self) -> subprocess.Popen`

重启游戏。先强制关闭，等待 2 秒后重新启动。

| 返回值 | 说明 |
|--------|------|
| `subprocess.Popen` | 新的游戏进程对象 |

#### `get_pid(self) -> Optional[int]`

获取进程 ID。

| 返回值 | 说明 |
|--------|------|
| `Optional[int]` | 进程 ID，未启动时返回 `None` |

#### `get_process_info(self) -> dict`

获取进程信息。

| 返回值 | 说明 |
|--------|------|
| `dict` | 包含 `pid`、`running`、`returncode`；未启动返回空字典 |

---

## 11. utils.config — 配置管理

> 模块路径: `src/utils/config.py`

### Config

测试框架配置数据类，支持从 `.env` 文件加载。

```python
@dataclass
class Config:
    glm_api_key: str = ""
    glm_model: str = "glm-4v"
    game_exe_path: str = ""
    game_window_title: Optional[str] = None
    game_startup_delay: int = 5
    test_case: str = ""
    max_steps: int = 100
    step_timeout: int = 30
    log_level: str = "INFO"
    screenshot_save_path: str = "./logs/screenshots"
    save_screenshots: bool = True
    ocr_enabled: bool = True
    ocr_languages: list = field(default_factory=lambda: ["ch_sim", "en"])
    click_delay: float = 0.5
    type_delay: float = 0.1
    keypress_delay: float = 0.3
```

**配置分组:**

| 分组 | 字段 | 默认值 |
|------|------|--------|
| GLM API | `glm_api_key`, `glm_model` | `""`, `"glm-4v"` |
| 游戏 | `game_exe_path`, `game_window_title`, `game_startup_delay` | `""`, `None`, `5` |
| 测试 | `test_case`, `max_steps`, `step_timeout` | `""`, `100`, `30` |
| 日志 | `log_level`, `screenshot_save_path`, `save_screenshots` | `"INFO"`, `"./logs/screenshots"`, `True` |
| 视觉 | `ocr_enabled`, `ocr_languages` | `True`, `["ch_sim", "en"]` |
| 动作 | `click_delay`, `type_delay`, `keypress_delay` | `0.5`, `0.1`, `0.3` |

#### `from_env(cls, env_path: str = ".env") -> Config` (类方法)

从 `.env` 文件加载配置。

| 参数 | 类型 | 说明 |
|------|------|------|
| `env_path` | `str` | 环境变量文件路径，默认 `".env"` |

| 返回值 | 说明 |
|--------|------|
| `Config` | 配置实例 |

#### `validate(self) -> bool`

验证必填配置项是否已设置。

| 返回值 | 说明 |
|--------|------|
| `bool` | 验证通过返回 `True` |

**异常:**

| 异常类型 | 触发条件 |
|----------|----------|
| `ValueError` | `glm_api_key`、`game_exe_path`、`test_case` 任一为空 |

---

## 12. utils.glm_client — GLM API 客户端

> 模块路径: `src/utils/glm_client.py`

### GLMAPIError

```python
class GLMAPIError(Exception)
```

GLM API 请求错误。在请求超时或 HTTP 错误时抛出。

---

### GLMClient

GLM 多模态模型 API 客户端，基于 requests 实现带重试策略的 HTTP 调用。

#### `__init__(self, api_key: str, model: str = "glm-4v", base_url: str = "https://open.bigmodel.cn/api/paas/v4", max_retries: int = 3, backoff_factor: float = 0.5, timeout: int = 30)`

| 参数 | 类型 | 说明 |
|------|------|------|
| `api_key` | `str` | API 密钥 |
| `model` | `str` | 模型名称，默认 `"glm-4v"` |
| `base_url` | `str` | API 基地址 |
| `max_retries` | `int` | 最大重试次数，默认 3 |
| `backoff_factor` | `float` | 退避因子，默认 0.5 |
| `timeout` | `int` | 请求超时秒数，默认 30 |

**异常:**

| 异常类型 | 触发条件 |
|----------|----------|
| `ValueError` | `api_key` 为空 |

#### `chat(self, messages: List[Dict[str, Any]], temperature: float = 0.2, max_tokens: int = 500) -> str`

发送聊天请求。

| 参数 | 类型 | 说明 |
|------|------|------|
| `messages` | `List[Dict[str, Any]]` | 消息列表（OpenAI 格式） |
| `temperature` | `float` | 生成温度，默认 0.2 |
| `max_tokens` | `int` | 最大生成 token 数，默认 500 |

| 返回值 | 说明 |
|--------|------|
| `str` | 模型回复文本 |

**异常:**

| 异常类型 | 触发条件 |
|----------|----------|
| `GLMAPIError` | 请求超时或 HTTP 错误 |

#### `chat_with_image(self, prompt: str, image: Image.Image, history: Optional[List[Dict[str, Any]]] = None, system_prompt: Optional[str] = None) -> str`

发送多模态请求（图片+文本）。

| 参数 | 类型 | 说明 |
|------|------|------|
| `prompt` | `str` | 用户提示文本 |
| `image` | `PIL.Image.Image` | 图片（自动编码为 base64） |
| `history` | `Optional[List[Dict[str, Any]]]` | 历史消息列表 |
| `system_prompt` | `Optional[str]` | 系统提示词 |

| 返回值 | 说明 |
|--------|------|
| `str` | 模型回复文本 |

**异常:**

| 异常类型 | 触发条件 |
|----------|----------|
| `GLMAPIError` | 请求超时或 HTTP 错误 |

#### `describe_scene(self, image: Image.Image, context: str = "") -> str`

描述游戏画面内容（布局、可交互元素、文本信息、界面状态）。

| 参数 | 类型 | 说明 |
|------|------|------|
| `image` | `PIL.Image.Image` | 游戏截图 |
| `context` | `str` | 额外上下文信息 |

| 返回值 | 说明 |
|--------|------|
| `str` | 画面描述文本 |

#### `close(self) -> None`

关闭 HTTP 会话，释放资源。

---

**上下文管理器支持:**

```python
with GLMClient(api_key="...") as client:
    response = client.chat_with_image("描述画面", image)
```
