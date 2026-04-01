# 时序图

## 1. ReAct 主循环

`GameAutoTester.run()` 的完整生命周期：初始化 -> 循环（观察-推理-行动）-> 清理。

```mermaid
sequenceDiagram
    participant Main as GameAutoTester
    participant Launcher as GameLauncher
    participant WinMgr as WindowManager
    participant Capture as ScreenCapture
    participant Agent as DecisionAgent
    participant Executor as ActionExecutor
    participant Memory as StateMemory

    Note over Main: 初始化阶段

    Main->>Launcher: launch()
    Launcher-->>Main: Popen process

    Main->>WinMgr: wait_for_window(process, title)
    WinMgr-->>Main: WindowInfo

    Main->>Capture: set_window(window_info)
    Main->>Main: 配置 element_locator / action_executor

    Main->>Agent: new(glm_client, test_case, state_memory)
    Main->>Memory: start_test()

    Note over Main: ReAct 主循环

    loop step = 1 .. max_steps
        Main->>Capture: capture()
        Capture-->>Main: PIL.Image (screenshot)

        alt save_screenshots
            Main->>Capture: capture_and_save(step, "before")
        end

        Main->>Agent: decide(image, ocr_engine)
        Note over Agent: 构建 Prompt（历史上下文 + 画面描述）
        Agent->>Memory: get_recent_actions(10)
        Memory-->>Agent: ActionRecord[]
        Agent->>Agent: _analyze_repetition()
        Agent-->>Main: {reasoning, action, warning?}

        Main->>Agent: validate_action(action)
        Agent-->>Main: bool

        alt action invalid
            Main->>Main: 替换为 wait(1s)
        end

        Main->>Main: execute_action(action)

        alt action == "click"
            Main->>Capture: capture()
            Main->>Executor: click(target, image, locator)
        else action == "type"
            Main->>Capture: capture()
            Main->>Executor: type_text(text, target, image, locator)
        else action == "keypress"
            Main->>Executor: press_key(key)
        else action == "wait"
            Main->>Executor: wait(seconds)
        else action == "assert"
            Main->>Capture: capture()
            Main->>Agent: ocr_engine.search_text(image, condition)
        else action == "done"
            Main->>Memory: end_test(success)
            Main->>Main: running = false, break
        end

        Main->>Memory: add_action(action, target, ..., success)

        alt save_screenshots
            Main->>Capture: capture_and_save(step, action_name)
        end

        alt consecutive_failures >= 5
            Main->>Executor: wait(3)
        end

        Main->>Main: sleep(1)
    end

    Note over Main: 清理阶段

    Main->>Memory: save_to_file("logs/test_record.json")
    Main->>Memory: get_summary()
    Main->>Launcher: close(force=true)
    Main->>Agent: glm_client.close()
```

---

## 2. DecisionAgent.decide() 决策流程

`DecisionAgent.decide()` 内部的 ReAct 推理全过程。

```mermaid
sequenceDiagram
    participant Caller as GameAutoTester
    participant Agent as DecisionAgent
    participant Memory as StateMemory
    participant OCR as OCREngine
    participant GLM as GLMClient

    Caller->>Agent: decide(image, scene_description, ocr_engine)

    Note over Agent: 构建上下文

    Agent->>Memory: get_recent_actions(10)
    Memory-->>Agent: ActionRecord[]

    alt scene_description is None
        Agent->>OCR: get_all_text_with_positions(image)
        OCR-->>Agent: [{text, bbox, center, confidence}, ...]
        Agent->>Agent: _build_screen_description()
    end

    Agent->>Agent: _build_history_context()

    Note over Agent: 分析重复动作

    Agent->>Memory: get_recent_actions(3)
    Memory-->>Agent: recent 3 actions

    alt last action exists
        Agent->>Agent: _analyze_repetition({action, target})
        alt count >= max_retry_same_action
            Agent-->>Agent: warning: "已连续执行N次，建议更换策略"
        end
    end

    Note over Agent: 构造 Prompt

    alt use_react == true
        Agent->>Agent: _build_react_prompt(history, screen)
    else
        Agent->>Agent: _build_decision_prompt(history)
    end

    Note over Agent: 调用 GLM

    Agent->>GLM: chat_with_image(prompt, image, system_prompt)
    GLM-->>Agent: response (str)

    Note over Agent: 解析响应

    Agent->>Agent: _parse_response_with_reasoning(response)
    Agent->>Agent: _extract_json(response)

    alt JSON 解析成功
        Agent->>Agent: 提取 reasoning + action
    else JSON 解析失败
        Agent->>Agent: _parse_action_only(response)
    end

    Note over Agent: 重试检查

    Agent->>Agent: _should_retry(action)

    alt count >= max_retry_same_action
        Agent->>Agent: 强制替换为 wait(3s)
        Agent-->>Agent: result["warning"] = "已达到最大重试次数"
    end

    Agent->>Agent: _increment_action(action_type, target)

    Agent-->>Caller: {reasoning, action, warning?}

    Note over Agent: 异常路径

    alt Exception
        Agent-->>Caller: {reasoning: "决策出错: ...", action: {wait, 2s}}
    end
```

---

## 3. ElementLocator 元素定位

`ElementLocator` 的多策略定位链：OCR 文本 -> GLM 视觉 -> 模板匹配 -> 颜色匹配。

```mermaid
sequenceDiagram
    participant Caller as ActionExecutor
    participant Locator as ElementLocator
    participant OCR as OCREngine
    participant GLM as GLMClient

    Note over Caller,Locator: 外部调用 get_element_center(image, "登录按钮")

    Caller->>Locator: get_element_center(image, description)
    Locator->>Locator: locate_by_text(image, description)

    Note over Locator: 策略1: OCR 文本定位

    alt ocr_engine is not None
        Locator->>OCR: search_text(image, description, threshold=0.5)
        OCR->>OCR: recognize(image, detail=1)
        OCR->>OCR: 逐条匹配 search_term
        OCR-->>Locator: [{text, bbox, confidence, center}, ...]

        alt matches found
            Locator->>Locator: 计算 bbox 边界
            Locator-->>Locator: return (x, y, w, h)
        end
    end

    Note over Locator: 策略2: GLM 视觉定位 (OCR 失败时)

    alt no OCR match and glm_client is not None
        Locator->>Locator: _locate_by_glm(image, description)

        Locator->>GLM: chat_with_image(prompt, image)
        Note over GLM: Prompt: 找到"{description}"的位置，输出JSON {x, y}
        GLM-->>Locator: response (JSON string)

        Locator->>Locator: 解析 JSON -> (x, y)
        Locator-->>Locator: return (x-25, y-25, 50, 50)
    end

    Note over Locator: 计算屏幕绝对坐标

    alt bbox found
        Locator->>Locator: cx = bbox.x + bbox.w/2, cy = bbox.y + bbox.h/2

        alt window_info is not None
            Locator->>Locator: cx += window_info.left, cy += window_info.top
        end

        Locator-->>Caller: (cx, cy) 屏幕绝对坐标
    else bbox not found
        Locator-->>Caller: None
    end

    Note over Caller,Locator: 其他定位策略 (独立调用)

    Caller->>Locator: locate_by_template(image, template_path)
    Note over Locator: OpenCV matchTemplate
    Locator-->>Caller: (x, y, w, h) | None

    Caller->>Locator: locate_by_color(image, color_range, min_area)
    Note over Locator: HSV 颜色空间 + 轮廓检测
    Locator-->>Caller: [(x, y, w, h), ...]
```

---

## 4. 游戏启动初始化

`GameAutoTester.initialize()` 的完整启动流程。

```mermaid
sequenceDiagram
    participant Main as GameAutoTester
    participant Launcher as GameLauncher
    participant WinMgr as WindowManager
    participant Capture as ScreenCapture
    participant Locator as ElementLocator
    participant Executor as ActionExecutor
    participant Agent as DecisionAgent
    participant Memory as StateMemory

    Main->>Main: initialize()

    Note over Main,Launcher: 1. 启动游戏进程

    Main->>Launcher: launch()
    Note over Launcher: subprocess.Popen(exe_path)
    Launcher->>Launcher: 验证 exe_path 存在
    Launcher->>Launcher: sleep(startup_delay)
    Launcher-->>Main: Popen process

    Note over Main,WinMgr: 2. 等待游戏窗口

    Main->>WinMgr: wait_for_window(process, timeout=30, title)

    loop until timeout
        WinMgr->>WinMgr: get_window_by_pid(process.pid)
        Note over WinMgr: win32gui.EnumWindows + GetWindowThreadProcessId

        alt window found by PID
            WinMgr-->>Main: WindowInfo
        else title specified
            WinMgr->>WinMgr: get_window_by_title(title)
            Note over WinMgr: pygetwindow.getWindowsWithTitle
            alt window found by title
                WinMgr-->>Main: WindowInfo
            end
        end

        WinMgr->>WinMgr: sleep(0.5)
    end

    Note over Main: 3. 配置窗口上下文

    Main->>Capture: set_window(window_info)
    Main->>Locator: window_info = window_info
    Main->>Executor: window_info = window_info

    Note over Main,WinMgr: 4. 激活窗口

    Main->>WinMgr: activate_window(hwnd)
    Note over WinMgr: ShowWindow(SW_RESTORE) + SetForegroundWindow

    Note over Main,Agent: 5. 创建决策 Agent

    Main->>Agent: new(glm_client, test_case, state_memory, use_react=True)

    Note over Main,Memory: 6. 开始测试

    Main->>Memory: start_test()
    Note over Memory: start_time = time.time()

    Main->>Main: running = True
    Main-->>Main: 初始化完成，准备进入 ReAct 循环
```

---

## 5. 动作执行与错误恢复

`GameAutoTester.execute_action()` 的动作分发和连续失败恢复机制。

```mermaid
sequenceDiagram
    participant Main as GameAutoTester
    participant Executor as ActionExecutor
    participant Locator as ElementLocator
    participant Capture as ScreenCapture
    participant OCR as OCREngine
    participant Memory as StateMemory

    Main->>Main: execute_action(action)
    Note over Main: action = {action: "...", target: "...", ...}

    alt action.action == "click"
        Main->>Capture: capture()
        Capture-->>Main: screenshot
        Main->>Executor: click(target, screenshot, locator)

        alt target is str (文本描述)
            Executor->>Locator: get_element_center(screenshot, target)
            Locator-->>Executor: (x, y) | None

            alt coords is None
                Executor-->>Main: false (未找到目标)
            end
        else target is Tuple (坐标)
            Note over Executor: 直接使用 (x, y)
        end

        Executor->>Executor: pydirectinput.moveTo(x, y)
        Executor->>Executor: pydirectinput.click()
        Executor-->>Main: true

    else action.action == "type"
        Main->>Capture: capture()
        Main->>Executor: type_text(text, target, screenshot, locator)

        alt target is not None
            Executor->>Executor: click(target) 先点击目标
        end

        alt clear_first
            Executor->>Executor: hotkey("ctrl", "a") + press("backspace")
        end

        loop 逐字符
            Executor->>Executor: pydirectinput.write(char)
            Executor->>Executor: sleep(type_delay)
        end
        Executor-->>Main: true

    else action.action == "keypress"
        Main->>Executor: press_key(key)
        Executor->>Executor: pydirectinput.press(key)
        Executor-->>Main: true

    else action.action == "wait"
        Main->>Executor: wait(seconds)
        Executor->>Executor: sleep(seconds)
        Executor-->>Main: true

    else action.action == "assert"
        Main->>Capture: capture()
        Main->>OCR: search_text(screenshot, condition)
        OCR-->>Main: matches []
        Main->>Main: success = len(matches) > 0

    else action.action == "done"
        Main->>Memory: end_test(success)
        Main-->>Main: return success
    end

    Note over Main,Memory: 记录动作结果

    Main->>Memory: add_action(action_type, target, reasoning, success, error?)

    Note over Main: 错误恢复

    alt not success
        Main->>Main: consecutive_failures += 1

        alt consecutive_failures >= 5
            Note over Main: 卡住恢复策略
            Main->>Main: consecutive_failures = 0
            Main->>Executor: wait(3)
        end
    else success
        Main->>Main: consecutive_failures = 0
    end

    Note over Main: 异常兜底

    alt Exception during execution
        Main->>Main: logger.error(e)
        Main->>Memory: add_action(type, "", error=str(e), success=False)
        Main-->>Main: return False
    end
```
