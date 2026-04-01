# src/agents/ — 决策层

决策层负责 AI 推理、测试状态管理和测试用例解析，是框架的"大脑"。

## 文件说明

| 文件 | 类/组件 | 职责 |
|------|---------|------|
| `decision_agent.py` | `DecisionAgent` | 核心 AI 决策引擎。支持 ReAct 推理模式，将截图+历史上下文发送给 GLM-4V，解析返回的 JSON 动作指令。内置重复动作检测与最大重试保护 |
| `state_memory.py` | `StateMemory` / `ActionRecord` | 测试状态记忆。记录每步动作（类型、目标、成功/失败），提供历史 Prompt 生成、测试摘要、JSON 序列化。默认保留最近 20 条记录 |
| `test_case_parser.py` | `TestCaseParser` | 自然语言测试用例解析器。从中文描述中提取测试目标、步骤、断言条件和测试数据（用户名/密码等） |

## 关键设计

### DecisionAgent ReAct 循环
1. 从 `StateMemory` 获取历史动作上下文
2. 可选通过 `OCREngine` 提取画面文本辅助描述
3. 构建 ReAct/简化 Prompt 发送给 GLM-4V
4. 解析 JSON 响应：`{"reasoning": "...", "action": {...}}`
5. 重复动作计数，超过阈值强制切换为 wait

### 动作验证
`validate_action()` 检查动作格式：click 需要 target、type 需要 target+text、keypress 需要 key、assert 需要 condition。

## 依赖关系

- `decision_agent.py` -> `glm_client.GLMClient`（调用 API）、`state_memory.StateMemory`（读写状态）
- `state_memory.py` -> 无外部依赖，纯数据结构
- `test_case_parser.py` -> 无外部依赖，纯正则解析

## 关键约定

- 合法动作类型：click、type、keypress、wait、assert、done
- 响应解析采用多重策略：JSON 块提取 -> 嵌套 JSON -> 文本关键词匹配
- `max_retry_same_action` 默认 3，同一动作超过次数自动降级为 wait
