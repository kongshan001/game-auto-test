# src/vision/ — 感知层

感知层负责屏幕画面获取和元素识别，是框架的"眼睛"。

## 文件说明

| 文件 | 类 | 职责 |
|------|---|------|
| `screen_capture.py` | `ScreenCapture` | 基于 mss 的屏幕捕获器。支持全屏/窗口区域/自定义区域截图，返回 PIL Image。可绑定 `WindowInfo` 实现窗口区域捕获，支持按步骤编号保存截图 |
| `ocr_engine.py` | `OCREngine` | 基于 EasyOCR 的文字识别引擎。懒加载 Reader 实例，提供文字识别、文本搜索（返回位置+置信度）、全量文本提取等能力。支持中英文 |
| `element_locator.py` | `ElementLocator` | 多策略元素定位器。按优先级组合三种定位方式：OCR 文本定位 -> GLM 视觉定位 -> OpenCV 模板匹配/颜色定位。输出屏幕绝对坐标 |

## 定位策略优先级

1. **OCR 文本定位** (`locate_by_text`): 通过 EasyOCR 搜索描述文本，返回文本边界框
2. **GLM 视觉定位** (`_locate_by_glm`): OCR 失败时，发送截图给 GLM-4V 让模型预测元素坐标
3. **OpenCV 模板匹配** (`locate_by_template`): 灰度图 `matchTemplate`，阈值默认 0.8
4. **颜色定位** (`locate_by_color`): HSV 颜色空间掩码 + 轮廓检测

## 依赖关系

- `screen_capture.py` -> mss、PIL、numpy
- `ocr_engine.py` -> easyocr（懒加载）、numpy、PIL
- `element_locator.py` -> `ocr_engine.OCREngine`（可选）、`glm_client.GLMClient`（可选）、cv2

## 关键约定

- 坐标系：元素定位返回窗口内相对坐标，`get_element_center()` 转换为屏幕绝对坐标
- OCR 引擎通过 `Config.ocr_enabled` 控制是否启用，未启用时 assert 动作无法执行
- 截图保存路径由 `Config.screenshot_save_path` 配置，默认 `./logs/screenshots`
