# src/ — 源码层总览

src 目录包含框架全部业务代码，按职责分为 5 个子模块，外加一个入口文件。

## 目录结构

| 路径 | 职责 |
|------|------|
| `main.py` | 程序入口。`GameAutoTester` 类编排 ReAct 主循环：初始化 -> 截屏 -> 决策 -> 执行 -> 状态记录 |
| `agents/` | 决策层。AI 推理引擎、状态记忆、测试用例解析 |
| `vision/` | 感知层。屏幕捕获、OCR 文字识别、多策略元素定位 |
| `action/` | 执行层。鼠标/键盘输入模拟、Windows 窗口管理 |
| `game/` | 游戏适配层。游戏进程启动、关闭、重启 |
| `utils/` | 基础设施。配置管理（Config dataclass）、GLM API 客户端（带重试） |

## 调用链

```
main.py::GameAutoTester
  -> utils.Config         加载 .env 配置
  -> utils.GLMClient      初始化 API 客户端
  -> game.GameLauncher    启动游戏进程
  -> action.WindowManager 查找并激活游戏窗口
  -> vision.ScreenCapture 绑定窗口区域
  -> agents.DecisionAgent 主循环中调用 GLM 推理
  -> action.ActionExecutor 执行 AI 决策的动作
  -> agents.StateMemory   记录每步结果
```

## 关键约定

- 所有模块通过 `GameAutoTester.__init__` 统一实例化并注入依赖
- 窗口信息 `WindowInfo` 在 `initialize()` 阶段获取后分发到各模块
- 日志使用 Python 标准 `logging`，输出到控制台 + `logs/test.log`
- 测试记录自动保存为 `logs/test_record.json`
