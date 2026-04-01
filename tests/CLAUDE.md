# tests/ — 测试套件

基于 pytest 的单元测试，覆盖框架核心模块。使用 unittest.mock 隔离外部依赖（GLM API、mss、EasyOCR）。

## 文件说明

| 文件 | 测试类 | 覆盖模块 | 测试重点 |
|------|--------|----------|----------|
| `test_config.py` | `TestConfig` | `utils.Config` | 默认值、自定义值、环境变量加载、必填项校验、OCR/延迟配置 |
| `test_glm_client.py` | `TestGLMClient` | `utils.GLMClient` | API key 校验、图像编码、请求成功/超时/异常、上下文管理器 |
| `test_decision_agent.py` | `TestDecisionAgent` | `agents.DecisionAgent` | 初始化、动作计数、重试判断、历史上下文构建、JSON 解析、动作格式验证 |
| `test_state_memory.py` | `TestActionRecord` / `TestStateMemory` | `agents.StateMemory` | ActionRecord 序列化、测试生命周期、历史记录限制、摘要统计、JSON 持久化 |
| `test_test_case_parser.py` | `TestTestCaseParser` | `agents.TestCaseParser` | 目标提取、步骤提取、数据提取（用户名/密码）、断言提取、Prompt 生成 |
| `test_screen_capture.py` | `TestScreenCapture` | `vision.ScreenCapture` | 基础创建和截图功能（标记 skip，依赖 mss 模块） |

## 运行命令

```bash
# 运行全部测试
pytest tests/ -v

# 运行单个模块
pytest tests/test_config.py -v

# 运行并查看覆盖率
pytest tests/ --cov=src --cov-report=term-missing
```

## 测试策略

- **Mock 隔离**：GLM API、mss 截屏、EasyOCR 等外部依赖通过 `unittest.mock.Mock/MagicMock` 替代
- **环境变量 Mock**：Config 测试使用 `@patch.dict(os.environ, {...})` 注入测试环境变量
- **跳过标记**：依赖硬件/平台的测试使用 `@pytest.mark.skip`，如 ScreenCapture
- **临时文件**：StateMemory 文件保存测试使用 pytest 的 `tmp_path` fixture

## 关键约定

- 测试文件命名：`test_<模块名>.py`
- 测试类命名：`Test<ClassName>`
- 测试方法命名：`test_<行为描述>`，使用中文 docstring 说明测试目的
- 每个测试方法专注一个验证点
