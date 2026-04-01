"""元素定位模块的测试。

Mock策略：OCR引擎和GLM客户端是外部/重型依赖，使用 mock。
cv2 模板匹配和颜色检测使用真实实现，用 PIL 构造真实测试图像。
"""
import pytest
import json
import numpy as np
from unittest.mock import MagicMock, patch
from PIL import Image

from src.vision.element_locator import ElementLocator


def _make_bbox(x, y, w, h):
    """构造一个真实的 OCR bbox（四角坐标列表）。"""
    return [[x, y], [x + w, y], [x + w, y + h], [x, y + h]]


def _create_image_with_red_rectangle(width=300, height=200):
    """创建包含红色矩形的真实 RGB 图像。"""
    img = Image.new("RGB", (width, height), color="white")
    arr = np.array(img)
    # 在图像中心绘制一个 80x60 的红色矩形
    arr[70:130, 110:190] = [255, 0, 0]
    return Image.fromarray(arr)


class TestElementLocatorInit:
    """ElementLocator 初始化相关测试。"""

    def test_init_with_defaults(self):
        """默认初始化时所有参数应为 None。"""
        locator = ElementLocator()
        assert locator.ocr_engine is None
        assert locator.glm_client is None
        assert locator.window_info is None

    def test_init_with_custom_params(self):
        """自定义参数应被正确保存。"""
        mock_ocr = MagicMock()
        mock_glm = MagicMock()
        mock_window = MagicMock()

        locator = ElementLocator(
            ocr_engine=mock_ocr,
            glm_client=mock_glm,
            window_info=mock_window,
        )

        assert locator.ocr_engine is mock_ocr
        assert locator.glm_client is mock_glm
        assert locator.window_info is mock_window


class TestLocateByText:
    """ElementLocator.locate_by_text 方法测试。"""

    def test_locate_by_text_with_ocr_match(self):
        """OCR 匹配成功时应返回 (x, y, w, h) 元组。"""
        mock_ocr = MagicMock()
        bbox = _make_bbox(50, 30, 100, 40)
        mock_ocr.search_text.return_value = [
            {"text": "Login", "bbox": bbox, "confidence": 0.9, "center": (100, 50)}
        ]

        locator = ElementLocator(ocr_engine=mock_ocr)
        image = Image.new("RGB", (200, 100), color="white")

        result = locator.locate_by_text(image, "Login")

        assert result is not None
        x, y, w, h = result
        assert x == 50
        assert y == 30
        assert w == 100
        assert h == 40

    def test_locate_by_text_ocr_no_match_glm_fallback(self):
        """OCR 无匹配时应回退到 GLM 定位。"""
        mock_ocr = MagicMock()
        mock_ocr.search_text.return_value = []

        mock_glm = MagicMock()
        mock_glm.chat_with_image.return_value = '{"x": 150, "y": 75}'

        locator = ElementLocator(ocr_engine=mock_ocr, glm_client=mock_glm)
        image = Image.new("RGB", (300, 150), color="white")

        result = locator.locate_by_text(image, "Settings")

        assert result is not None
        # GLM 返回 (150, 75)，locate_by_text 构造 (cx-25, cy-25, 50, 50)
        assert result == (125, 50, 50, 50)

    def test_locate_by_text_no_engines_returns_none(self):
        """既没有 OCR 引擎也没有 GLM 客户端时应返回 None。"""
        locator = ElementLocator()
        image = Image.new("RGB", (200, 100), color="white")

        result = locator.locate_by_text(image, "AnyText")

        assert result is None


class TestLocateByTemplate:
    """ElementLocator.locate_by_template 方法测试。"""

    def test_locate_by_template_with_valid_template(self, tmp_path):
        """使用真实模板图像匹配时应返回正确位置。"""
        # 创建源图像：灰色背景上放置独特的棋盘格图案
        source_arr = np.full((200, 300, 3), 128, dtype=np.uint8)
        for row in range(40, 100):
            for col in range(60, 160):
                if (row // 10 + col // 10) % 2 == 0:
                    source_arr[row, col] = [255, 255, 255]
                else:
                    source_arr[row, col] = [0, 0, 0]
        source_img = Image.fromarray(source_arr)

        # 从源图像中裁剪出模板（与棋盘格区域完全匹配）
        template_img = source_img.crop((60, 40, 160, 100))
        template_path = str(tmp_path / "template.png")
        template_img.save(template_path)

        locator = ElementLocator()
        result = locator.locate_by_template(source_img, template_path, threshold=0.8)

        assert result is not None
        x, y, w, h = result
        assert x == 60
        assert y == 40
        assert w == 100
        assert h == 60

    def test_locate_by_template_file_not_found_returns_none(self):
        """模板文件不存在时应返回 None。"""
        locator = ElementLocator()
        image = Image.new("RGB", (200, 100), color="white")

        result = locator.locate_by_template(image, "/nonexistent/path/template.png")

        assert result is None

    def test_locate_by_template_below_threshold_returns_none(self, tmp_path):
        """匹配分数低于阈值时应返回 None。"""
        # 源图像：均匀灰色（与模板无相关性）
        source_img = Image.new("RGB", (300, 200), color=(128, 128, 128))

        # 模板：棋盘格图案（与均匀源图像完全不同）
        template_arr = np.full((60, 100, 3), 128, dtype=np.uint8)
        for row in range(60):
            for col in range(100):
                if (row // 10 + col // 10) % 2 == 0:
                    template_arr[row, col] = [255, 255, 255]
                else:
                    template_arr[row, col] = [0, 0, 0]
        template_img = Image.fromarray(template_arr)
        template_path = str(tmp_path / "template.png")
        template_img.save(template_path)

        locator = ElementLocator()
        # TM_CCOEFF_NORMED 对均匀源图像 vs 棋盘格模板返回 0.0
        result = locator.locate_by_template(source_img, template_path, threshold=0.5)

        assert result is None


class TestLocateByColor:
    """ElementLocator.locate_by_color 方法测试。"""

    def test_locate_by_color_with_matching_color(self):
        """图像中存在目标颜色区域时应返回边界框。"""
        image = _create_image_with_red_rectangle()
        locator = ElementLocator()

        # HSV 红色范围（OpenCV 中 H 范围 0-179）
        color_range = ((0, 100, 100), (10, 255, 255))

        results = locator.locate_by_color(image, color_range, min_area=100)

        assert len(results) >= 1
        # 验证至少有一个结果的面积足够大
        for x, y, w, h in results:
            assert w * h >= 100

    def test_locate_by_color_no_matching_color(self):
        """图像中不存在目标颜色区域时应返回空列表。"""
        image = Image.new("RGB", (300, 200), color="blue")
        locator = ElementLocator()

        # HSV 黄色范围，在蓝色图像中不存在
        color_range = ((20, 100, 100), (35, 255, 255))

        results = locator.locate_by_color(image, color_range, min_area=100)

        assert results == []

    def test_locate_by_color_filters_by_min_area(self):
        """面积小于 min_area 的轮廓应被过滤掉。"""
        image = _create_image_with_red_rectangle()
        locator = ElementLocator()

        color_range = ((0, 100, 100), (10, 255, 255))

        # 用很大的 min_area 过滤
        results_small = locator.locate_by_color(image, color_range, min_area=1)
        results_large = locator.locate_by_color(image, color_range, min_area=100000)

        assert len(results_small) >= 1
        assert len(results_large) == 0


class TestGetElementCenter:
    """ElementLocator.get_element_center 方法测试。"""

    def test_get_element_center_with_window_info(self):
        """有 window_info 时应返回加上窗口偏移的绝对坐标。"""
        mock_ocr = MagicMock()
        bbox = _make_bbox(40, 20, 120, 60)
        mock_ocr.search_text.return_value = [
            {"text": "Start", "bbox": bbox, "confidence": 0.9, "center": (100, 50)}
        ]

        mock_window = MagicMock()
        mock_window.left = 100
        mock_window.top = 50

        locator = ElementLocator(ocr_engine=mock_ocr, window_info=mock_window)
        image = Image.new("RGB", (300, 200), color="white")

        center = locator.get_element_center(image, "Start")

        assert center is not None
        # bbox (40,20,120,60) -> center = (40+120//2, 20+60//2) = (100, 50)
        # 加上窗口偏移: (100+100, 50+50) = (200, 100)
        assert center == (200, 100)

    def test_get_element_center_without_window_info(self):
        """没有 window_info 时不应添加偏移。"""
        mock_ocr = MagicMock()
        bbox = _make_bbox(40, 20, 120, 60)
        mock_ocr.search_text.return_value = [
            {"text": "Start", "bbox": bbox, "confidence": 0.9, "center": (100, 50)}
        ]

        locator = ElementLocator(ocr_engine=mock_ocr)
        image = Image.new("RGB", (300, 200), color="white")

        center = locator.get_element_center(image, "Start")

        assert center is not None
        # bbox (40,20,120,60) -> center = (40+60, 20+30) = (100, 50)
        assert center == (100, 50)

    def test_get_element_center_element_not_found_returns_none(self):
        """元素未找到时应返回 None。"""
        mock_ocr = MagicMock()
        mock_ocr.search_text.return_value = []

        locator = ElementLocator(ocr_engine=mock_ocr)
        image = Image.new("RGB", (200, 100), color="white")

        center = locator.get_element_center(image, "不存在")

        assert center is None


class TestLocateByGLM:
    """ElementLocator._locate_by_glm 私有方法测试。"""

    def test_locate_by_glm_success(self):
        """GLM 返回有效 JSON 时应返回坐标元组。"""
        mock_glm = MagicMock()
        mock_glm.chat_with_image.return_value = '{"x": 200, "y": 150}'

        locator = ElementLocator(glm_client=mock_glm)
        image = Image.new("RGB", (300, 200), color="white")

        result = locator._locate_by_glm(image, "开始按钮")

        assert result is not None
        assert result == (200, 150)

    def test_locate_by_glm_json_parse_failure_returns_none(self):
        """GLM 返回无法解析的内容时应返回 None。"""
        mock_glm = MagicMock()
        mock_glm.chat_with_image.return_value = "这不是有效的JSON"

        locator = ElementLocator(glm_client=mock_glm)
        image = Image.new("RGB", (300, 200), color="white")

        result = locator._locate_by_glm(image, "按钮")

        assert result is None

    def test_locate_by_glm_no_client_returns_none(self):
        """没有 GLM 客户端时应返回 None。"""
        locator = ElementLocator()
        image = Image.new("RGB", (300, 200), color="white")

        result = locator._locate_by_glm(image, "按钮")

        assert result is None
