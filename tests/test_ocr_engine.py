"""OCR引擎模块的测试。

Mock策略：easyocr.Reader 是重型外部依赖，必须 mock。
PIL Image 和 numpy 使用真实实现，用 Image.new() 构造测试图像。
"""
import pytest
from unittest.mock import patch, MagicMock, PropertyMock
from PIL import Image
import numpy as np

from src.vision.ocr_engine import OCREngine


def _make_bbox(x, y, w, h):
    """构造一个真实的 OCR bbox（四角坐标列表）。"""
    return [[x, y], [x + w, y], [x + w, y + h], [x, y + h]]


class TestOCREngineInit:
    """OCREngine 初始化相关测试。"""

    def test_init_default_languages(self):
        """默认语言列表应为 ["ch_sim", "en"]。"""
        engine = OCREngine()
        assert engine.languages == ["ch_sim", "en"]

    def test_init_custom_languages(self):
        """自定义语言列表应被正确保存。"""
        engine = OCREngine(languages=["en", "ja"])
        assert engine.languages == ["en", "ja"]

    def test_init_use_gpu_default_false(self):
        """use_gpu 默认值应为 False。"""
        engine = OCREngine()
        assert engine.use_gpu is False

    def test_reader_lazy_loading(self):
        """reader 属性在首次访问前应为 None（懒加载）。"""
        engine = OCREngine()
        # _reader 内部属性在首次访问 reader 属性之前应为 None
        assert engine._reader is None

    def test_reader_property_triggers_lazy_load(self):
        """首次访问 reader 属性应触发 easyocr.Reader 的创建。"""
        mock_reader_instance = MagicMock()
        mock_easyocr = MagicMock()
        mock_easyocr.Reader.return_value = mock_reader_instance

        engine = OCREngine(languages=["en"], use_gpu=False)
        with patch.dict("sys.modules", {"easyocr": mock_easyocr}):
            reader = engine.reader

        mock_easyocr.Reader.assert_called_once_with(["en"], gpu=False, verbose=False)
        assert reader is mock_reader_instance

    def test_reader_property_raises_import_error_when_easyocr_missing(self):
        """当 easyocr 未安装时，访问 reader 应抛出 ImportError。"""
        engine = OCREngine()
        with patch.dict("sys.modules", {"easyocr": None}):
            with pytest.raises(ImportError, match="easyocr"):
                _ = engine.reader


class TestOCREngineRecognize:
    """OCREngine.recognize 方法测试。"""

    def _setup_engine_with_mock_reader(self):
        """创建带有 mock reader 的引擎实例。"""
        engine = OCREngine()
        mock_reader = MagicMock()
        engine._reader = mock_reader
        return engine, mock_reader

    def test_recognize_detail_1_returns_full_results(self):
        """detail=1 时应返回 (text, bbox, confidence) 元组列表。"""
        engine, mock_reader = self._setup_engine_with_mock_reader()
        image = Image.new("RGB", (200, 100), color="white")

        bbox = _make_bbox(10, 20, 80, 30)
        mock_reader.readtext.return_value = [("Hello", bbox, 0.95)]

        results = engine.recognize(image, detail=1)

        assert len(results) == 1
        assert results[0] == ("Hello", bbox, 0.95)

    def test_recognize_detail_0_returns_text_only(self):
        """detail=0 时应只返回文本字符串列表。"""
        engine, mock_reader = self._setup_engine_with_mock_reader()
        image = Image.new("RGB", (200, 100), color="white")

        mock_reader.readtext.return_value = [
            ("Hello", _make_bbox(10, 20, 80, 30), 0.95),
            ("World", _make_bbox(100, 20, 80, 30), 0.88),
        ]

        results = engine.recognize(image, detail=0)

        assert results == ["Hello", "World"]

    def test_recognize_converts_grayscale_to_rgb(self):
        """灰度图像应被自动转换为 RGB 后再传给 reader。"""
        engine, mock_reader = self._setup_engine_with_mock_reader()
        # 真实的灰度图像（mode="L"）
        image = Image.new("L", (200, 100), color=128)
        mock_reader.readtext.return_value = []

        engine.recognize(image, detail=1)

        # 验证传给 readtext 的数组是 3 通道
        call_args = mock_reader.readtext.call_args
        img_array = call_args[0][0]
        assert len(img_array.shape) == 3
        assert img_array.shape[2] == 3

    def test_recognize_converts_rgba_to_rgb(self):
        """RGBA 图像应被自动转换为 RGB 后再传给 reader。"""
        engine, mock_reader = self._setup_engine_with_mock_reader()
        # 真实的 RGBA 图像
        image = Image.new("RGBA", (200, 100), color=(255, 0, 0, 128))
        mock_reader.readtext.return_value = []

        engine.recognize(image, detail=1)

        call_args = mock_reader.readtext.call_args
        img_array = call_args[0][0]
        assert len(img_array.shape) == 3
        assert img_array.shape[2] == 3


class TestOCREngineSearchText:
    """OCREngine.search_text 方法测试。"""

    def _setup_engine_with_results(self, readtext_results):
        """创建引擎并预设 reader 返回值。"""
        engine = OCREngine()
        mock_reader = MagicMock()
        mock_reader.readtext.return_value = readtext_results
        engine._reader = mock_reader
        return engine

    def test_search_text_finds_matching_text_case_insensitive(self):
        """搜索文本应忽略大小写匹配。"""
        engine = self._setup_engine_with_results([
            ("Login Button", _make_bbox(10, 10, 100, 40), 0.9),
            ("Cancel", _make_bbox(120, 10, 80, 40), 0.85),
        ])
        image = Image.new("RGB", (200, 100), color="white")

        matches = engine.search_text(image, "login button")

        assert len(matches) == 1
        assert matches[0]["text"] == "Login Button"

    def test_search_text_returns_empty_when_no_match(self):
        """搜索不到文本时应返回空列表。"""
        engine = self._setup_engine_with_results([
            ("Hello", _make_bbox(10, 10, 80, 30), 0.9),
        ])
        image = Image.new("RGB", (200, 100), color="white")

        matches = engine.search_text(image, "不存在")

        assert matches == []

    def test_search_text_filters_by_confidence_threshold(self):
        """低于置信度阈值的结果应被过滤掉。"""
        engine = self._setup_engine_with_results([
            ("HighConf", _make_bbox(10, 10, 80, 30), 0.8),
            ("LowConf", _make_bbox(100, 10, 80, 30), 0.3),
        ])
        image = Image.new("RGB", (200, 100), color="white")

        matches = engine.search_text(image, "HighConf", confidence_threshold=0.5)

        assert len(matches) == 1
        assert matches[0]["text"] == "HighConf"


class TestOCREngineFindTextPosition:
    """OCREngine.find_text_position 方法测试。"""

    def _setup_engine_with_results(self, readtext_results):
        """创建引擎并预设 reader 返回值。"""
        engine = OCREngine()
        mock_reader = MagicMock()
        mock_reader.readtext.return_value = readtext_results
        engine._reader = mock_reader
        return engine

    def test_find_text_position_returns_center_of_best_match(self):
        """应返回置信度最高的匹配项的中心坐标。"""
        engine = self._setup_engine_with_results([
            ("Play", _make_bbox(10, 10, 80, 30), 0.7),
            ("Play", _make_bbox(100, 50, 80, 30), 0.95),
        ])
        image = Image.new("RGB", (200, 100), color="white")

        pos = engine.find_text_position(image, "Play")

        assert pos is not None
        # 第二个 bbox 的中心: xs=[100,180,180,100] -> avg=140, ys=[50,50,80,80] -> avg=65
        assert pos == (140, 65)

    def test_find_text_position_returns_none_when_no_match(self):
        """找不到文本时应返回 None。"""
        engine = self._setup_engine_with_results([
            ("Other", _make_bbox(10, 10, 80, 30), 0.9),
        ])
        image = Image.new("RGB", (200, 100), color="white")

        pos = engine.find_text_position(image, "不存在")

        assert pos is None


class TestOCREngineGetAllTextWithPositions:
    """OCREngine.get_all_text_with_positions 方法测试。"""

    def _setup_engine_with_results(self, readtext_results):
        """创建引擎并预设 reader 返回值。"""
        engine = OCREngine()
        mock_reader = MagicMock()
        mock_reader.readtext.return_value = readtext_results
        engine._reader = mock_reader
        return engine

    def test_get_all_text_filters_by_confidence(self):
        """低于置信度阈值的文本应被过滤掉。"""
        engine = self._setup_engine_with_results([
            ("High", _make_bbox(10, 10, 80, 30), 0.9),
            ("Low", _make_bbox(100, 10, 80, 30), 0.2),
        ])
        image = Image.new("RGB", (200, 100), color="white")

        items = engine.get_all_text_with_positions(image, confidence_threshold=0.3)

        assert len(items) == 1
        assert items[0]["text"] == "High"

    def test_get_all_text_returns_all_fields(self):
        """每个返回项应包含 text、bbox、center、confidence 四个字段。"""
        bbox = _make_bbox(10, 20, 80, 30)
        engine = self._setup_engine_with_results([
            ("Test", bbox, 0.85),
        ])
        image = Image.new("RGB", (200, 100), color="white")

        items = engine.get_all_text_with_positions(image, confidence_threshold=0.3)

        assert len(items) == 1
        item = items[0]
        assert "text" in item
        assert "bbox" in item
        assert "center" in item
        assert "confidence" in item
        assert item["text"] == "Test"
        assert item["bbox"] == bbox
        assert item["confidence"] == 0.85
        # center: xs=[10,90,90,10] -> avg=50, ys=[20,20,50,50] -> avg=35
        assert item["center"] == (50, 35)
