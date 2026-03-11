# Windows游戏自动化测试框架

基于GLM多模态大模型的AI驱动Windows游戏自动化测试框架。

## 特性

- 🤖 AI驱动 - 使用GLM多模态模型进行视觉理解和决策
- 🎮 游戏自动化 - 自动启动游戏并执行测试用例
- 👁️ 视觉感知 - OCR识别、模板匹配、场景描述
- 🔄 智能决策 - 自然语言测试用例自动解析
- 📝 完整日志 - 记录执行过程便于调试

## 快速开始

### 1. 安装依赖

```bash
pip install -r requirements.txt
```

### 2. 配置

创建 `.env` 文件：

```env
GLM_API_KEY=your_api_key_here
GAME_EXE_PATH=C:\Games\MyGame\game.exe
TEST_CASE=测试登录：输入用户名'admin'，密码'123'，点击登录，验证进入主界面
LOG_LEVEL=INFO
SCREENSHOT_SAVE_PATH=./logs/screenshots
MAX_STEPS=100
```

### 3. 运行

```bash
python src/main.py --config .env
```

## 架构

```
src/
├── main.py              # 入口点
├── agents/              # AI Agent模块
│   ├── test_case_parser.py   # 测试用例解析器
│   ├── decision_agent.py     # 决策规划模块
│   └── state_memory.py        # 状态记忆
├── vision/              # 视觉感知模块
│   ├── screen_capture.py      # 屏幕捕获
│   ├── ocr识别.py            # OCR识别
│   └── element_locator.py     # 元素定位
├── action/              # 动作执行模块
│   ├── input_executor.py      # 输入模拟
│   └── window_manager.py     # 窗口管理
├── game/               # 游戏启动器
│   └── game_launcher.py       # 游戏进程管理
└── utils/              # 工具函数
    ├── glm_client.py          # GLM API客户端
    └── config.py              # 配置管理
```

## 支持的动作

- `click` - 点击目标（文本描述或坐标）
- `type` - 输入文本
- `keypress` - 按键操作
- `wait` - 等待
- `assert` - 验证条件
- `done` - 测试完成

## 许可证

MIT
