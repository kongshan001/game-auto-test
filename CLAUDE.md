# game-auto-test — Windows 游戏自动化测试框架

基于 GLM 多模态大模型（GLM-4V）的 AI 驱动游戏自动化测试框架。通过截屏 -> AI 推理 -> 执行动作的 ReAct 循环，自动完成游戏功能测试。

## 技术栈

Python 3.10+ | GLM-4V 多模态大模型 | EasyOCR | OpenCV | mss | pydirectinput | pytest

## 目录结构

```
game-auto-test/
  src/
    main.py              # 入口：GameAutoTester 类，编排 ReAct 主循环
    agents/               # 决策层：AI 推理、状态记忆、用例解析
    vision/               # 感知层：截屏、OCR、元素定位
    action/               # 执行层：鼠标/键盘输入、窗口管理
    game/                 # 游戏适配：启动、关闭、重启
    utils/                # 基础设施：配置管理、GLM API 客户端
  tests/                  # pytest 测试套件
  logs/                   # 运行日志与截图（运行时生成）
```

## 常用命令

```bash
# 安装依赖
pip install -r requirements.txt

# 运行测试框架（需先配置 .env）
python src/main.py --config .env

# 运行单元测试
pytest tests/ -v

# 运行单个测试文件
pytest tests/test_config.py -v
```

## 架构概览

分层架构：**入口(main) -> 决策(agents) -> 感知(vision) -> 执行(action) + 适配(utils/game)**

核心 ReAct 循环：
1. `ScreenCapture` 捕获游戏画面
2. `DecisionAgent` 调用 GLM-4V 进行推理，输出下一步动作
3. `ActionExecutor` 执行 click/type/keypress/wait/assert/done 动作
4. `StateMemory` 记录动作历史与测试状态
5. 回到步骤 1，直到测试完成或达到最大步数

配置通过 `.env` 文件加载，由 `Config` dataclass 统一管理。

## 详细文档

- 架构设计 @docs/architecture.md
- UML 类图 @docs/uml/class-diagram.md
- UML 时序图 @docs/uml/sequence-diagrams.md
- 组件图 @docs/uml/component-diagram.md
- 业务逻辑脑图 @docs/mindmap/business-logic.md
- 模块结构脑图 @docs/mindmap/module-structure.md
- API 参考 @docs/api/reference.md

## 关键约定

- 动作类型固定为 6 种：click、type、keypress、wait、assert、done
- GLM 返回 JSON 格式：`{"reasoning": "...", "action": {...}}`
- 同一动作连续失败超过 `max_retry_same_action`（默认 3）次时自动切换策略
- 连续 5 次失败触发强制等待恢复机制
- 窗口坐标统一使用绝对屏幕坐标，通过 `window_info` 做相对/绝对转换
