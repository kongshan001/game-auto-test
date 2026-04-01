# src/utils/ — 基础设施层

基础设施层提供配置管理和 GLM API 通信能力，被所有上层模块依赖。

## 文件说明

| 文件 | 类 | 职责 |
|------|---|------|
| `config.py` | `Config` | 测试框架配置。使用 dataclass 定义全部配置项，支持从 `.env` 文件加载（`from_env()`），提供必填项校验（`validate()`） |
| `glm_client.py` | `GLMClient` / `GLMAPIError` | GLM 多模态模型 API 客户端。基于 requests + urllib3 Retry 实现带重试的 HTTP 调用，支持纯文本和多模态（图片+文本）请求，内置 base64 图像编码 |

## Config 配置项一览

| 分组 | 配置项 | 默认值 |
|------|--------|--------|
| GLM API | `glm_api_key`, `glm_model` | "", "glm-4v" |
| 游戏 | `game_exe_path`, `game_window_title`, `game_startup_delay` | "", None, 5 |
| 测试 | `test_case`, `max_steps`, `step_timeout` | "", 100, 30 |
| 日志 | `log_level`, `screenshot_save_path`, `save_screenshots` | INFO, ./logs/screenshots, True |
| 视觉 | `ocr_enabled`, `ocr_languages` | True, ["ch_sim","en"] |
| 动作 | `click_delay`, `type_delay`, `keypress_delay` | 0.5, 0.1, 0.3 |

## GLMClient 核心方法

| 方法 | 说明 |
|------|------|
| `chat(messages, temperature, max_tokens)` | 发送聊天请求，返回文本响应 |
| `chat_with_image(prompt, image, history, system_prompt)` | 发送多模态请求（图片+文本） |
| `describe_scene(image, context)` | 描述游戏画面内容（布局、元素、文本、状态） |
| `close()` | 关闭 HTTP 会话 |

## 依赖关系

- `config.py` -> python-dotenv（.env 加载）
- `glm_client.py` -> requests、urllib3、PIL

## 关键约定

- Config 必填项：`glm_api_key`、`game_exe_path`、`test_case`，缺少任一项 `validate()` 抛出 ValueError
- GLM API 基地址：`https://open.bigmodel.cn/api/paas/v4`
- 重试策略：最多 3 次，指数退避 0.5s，对 429/5xx 状态码重试
- 请求超时默认 30 秒
- `GLMClient` 支持上下文管理器（`with` 语法）
