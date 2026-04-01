# 组件图

## 分层组件架构

按职责将系统划分为 5 个层次的 Mermaid 组件图，展示模块间的调用关系和数据流向。

```mermaid
flowchart TB
    subgraph EntryLayer["入口层"]
        direction LR
        GAT["GameAutoTester<br/><i>main.py</i><br/><b>主控编排器</b><br/>ReAct 主循环 · 动作分发 · 资源管理"]
    end

    subgraph DecisionLayer["决策层"]
        direction LR
        DA["DecisionAgent<br/><i>agents/decision_agent.py</i><br/><b>AI 决策引擎</b><br/>ReAct 推理 · Prompt 构建 · 响应解析"]
        SM["StateMemory<br/><i>agents/state_memory.py</i><br/><b>状态记忆</b><br/>动作历史 · 测试生命周期"]
        TCP["TestCaseParser<br/><i>agents/test_case_parser.py</i><br/><b>用例解析器</b><br/>NLP 步骤提取 · 验证条件提取"]
    end

    subgraph VisionLayer["感知层"]
        direction LR
        SC["ScreenCapture<br/><i>vision/screen_capture.py</i><br/><b>画面捕获</b><br/>mss 截图 · 区域裁剪 · 文件保存"]
        OCR["OCREngine<br/><i>vision/ocr_engine.py</i><br/><b>文字识别</b><br/>EasyOCR · 文本搜索 · 坐标定位"]
        EL["ElementLocator<br/><i>vision/element_locator.py</i><br/><b>元素定位</b><br/>OCR · GLM 视觉 · 模板匹配 · 颜色匹配"]
    end

    subgraph ExecutionLayer["执行层"]
        direction LR
        AE["ActionExecutor<br/><i>action/input_executor.py</i><br/><b>动作执行</b><br/>点击 · 输入 · 按键 · 拖拽 · 滚动"]
        WM["WindowManager<br/><i>action/window_manager.py</i><br/><b>窗口管理</b><br/>win32gui 窗口查找 · 激活 · 等待"]
        WI["WindowInfo<br/><i>action/window_manager.py</i><br/><b>窗口信息</b><br/>hwnd · 位置 · 尺寸"]
    end

    subgraph AdapterLayer["适配层"]
        direction LR
        GL["GameLauncher<br/><i>game/game_launcher.py</i><br/><b>游戏启动</b><br/>进程管理 · 启动/关闭/重启"]
        CFG["Config<br/><i>utils/config.py</i><br/><b>配置管理</b><br/>dotenv · 环境变量 · 验证"]
        GC["GLMClient<br/><i>utils/glm_client.py</i><br/><b>API 客户端</b><br/>HTTP · base64 · 重试策略"]
        ERR["GLMAPIError<br/><i>utils/glm_client.py</i><br/><b>API 异常</b>"]
    end

    %% 入口层 -> 决策层
    GAT ==>|"创建并调用"| DA
    GAT ==>|"创建并持有"| SM
    GAT -.->|"用例解析"| TCP

    %% 入口层 -> 感知层
    GAT ==>|"截图"| SC

    %% 入口层 -> 执行层
    GAT ==>|"执行动作"| AE
    GAT ==>|"窗口管理"| WM

    %% 入口层 -> 适配层
    GAT ==>|"启动游戏"| GL
    GAT -->|"加载配置"| CFG

    %% 决策层内部
    DA -->|"读取历史"| SM
    DA -.->|"OCR 辅助"| OCR
    DA ==>|"调用 API"| GC

    %% 感知层内部
    EL -->|"文本定位"| OCR
    EL -.->|"视觉定位"| GC
    EL -.->|"窗口坐标"| WI

    %% 执行层内部
    AE -.->|"文本目标定位"| EL
    AE -.->|"坐标转换"| WI
    WM -->|"创建"| WI

    %% 适配层 -> 执行层
    GL -.->|"进程 PID"| WM

    %% 感知层 -> 执行层
    SC -.->|"截图区域"| WI

    %% 适配层异常
    GC -.->|"抛出"| ERR

    %% 样式
    style EntryLayer fill:#E8F4FD,stroke:#4A90D9,color:#333
    style DecisionLayer fill:#FFF8E1,stroke:#F5A623,color:#333
    style VisionLayer fill:#E8F5E9,stroke:#4CAF50,color:#333
    style ExecutionLayer fill:#FFEBEE,stroke:#E74C3C,color:#333
    style AdapterLayer fill:#F3E5F5,stroke:#9C27B0,color:#333

    style GAT fill:#4A90D9,color:#fff
    style DA fill:#F5A623,color:#fff
    style SC fill:#4CAF50,color:#fff
    style EL fill:#66BB6A,color:#fff
    style AE fill:#E74C3C,color:#fff
    style GC fill:#9C27B0,color:#fff
```

## 图例说明

| 线型 | 含义 |
|------|------|
| `==>` 实线粗箭头 | 直接调用（创建、持有、主流程调用） |
| `-->` 实线细箭头 | 依赖注入（构造函数注入） |
| `-.->` 虚线箭头 | 运行时依赖（方法参数注入、可选依赖、间接使用） |

## 层间调用规则

| 调用方 | 被调用方 | 调用方式 |
|--------|----------|----------|
| 入口层 -> 决策层 | `GameAutoTester` -> `DecisionAgent` | 创建并调用 `decide()` |
| 入口层 -> 感知层 | `GameAutoTester` -> `ScreenCapture` | 创建并调用 `capture()` |
| 入口层 -> 执行层 | `GameAutoTester` -> `ActionExecutor` | 创建并调用动作方法 |
| 入口层 -> 适配层 | `GameAutoTester` -> `GameLauncher` / `Config` / `GLMClient` | 创建并管理生命周期 |
| 决策层 -> 适配层 | `DecisionAgent` -> `GLMClient` | 依赖注入，调用 `chat_with_image()` |
| 决策层 -> 感知层 | `DecisionAgent` -> `OCREngine` | 运行时注入，用于画面描述 |
| 感知层 -> 适配层 | `ElementLocator` -> `GLMClient` | 依赖注入，用于视觉定位 |
| 感知层 -> 感知层 | `ElementLocator` -> `OCREngine` | 依赖注入，用于文本定位 |
| 执行层 -> 感知层 | `ActionExecutor` -> `ElementLocator` | 方法参数注入，用于目标定位 |

## 外部依赖封装

```mermaid
flowchart LR
    subgraph Framework["框架内部"]
        GC["GLMClient"]
        OCR["OCREngine"]
        SC["ScreenCapture"]
        AE["ActionExecutor"]
        WM["WindowManager"]
        GL["GameLauncher"]
    end

    subgraph External["外部依赖"]
        API["GLM-4V API<br/>多模态大模型"]
        EOCR["EasyOCR<br/>文字识别引擎"]
        MSS["mss<br/>屏幕截图库"]
        PDI["pydirectinput<br/>硬件级输入模拟"]
        W32["win32gui / win32con<br/>Windows 窗口 API"]
        SUB["subprocess<br/>进程管理"]
        CV2["OpenCV (cv2)<br/>图像处理"]
        PIL["Pillow (PIL)<br/>图像操作"]
        REQ["requests + urllib3<br/>HTTP 客户端"]
        DOT["python-dotenv<br/>环境变量加载"]
    end

    GC --> REQ
    GC --> API
    OCR --> EOCR
    SC --> MSS
    AE --> PDI
    WM --> W32
    GL --> SUB

    SC --> PIL
    OCR --> PIL
    EL2["ElementLocator"] --> CV2

    style Framework fill:#E3F2FD,stroke:#1976D2,color:#333
    style External fill:#F5F5F5,stroke:#9E9E9E,color:#333
```
