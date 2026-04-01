"""屏幕捕获模块的测试。"""
import os
import time
from pathlib import Path
from unittest.mock import patch, MagicMock

import numpy as np
import pytest
from PIL import Image

from src.vision.screen_capture import ScreenCapture


def _make_mock_mss(capture_size=(800, 600), capture_rgb=None):
    """
    构造一个 mock mss 实例。

    mss.grab 返回的对象需要 .size 和 .rgb 属性，
    这里用真实 PIL Image 生成像素数据以保证 Image.frombytes 可正常工作。
    只有 mss 这个硬件依赖被 mock，PIL 操作全部使用真实实现。
    """
    img = Image.new("RGB", capture_size, color=(128, 64, 32))
    if capture_rgb is None:
        capture_rgb = img.tobytes()

    mock_grab_result = MagicMock()
    mock_grab_result.size = capture_size
    mock_grab_result.rgb = capture_rgb

    mock_sct = MagicMock()
    mock_sct.grab.return_value = mock_grab_result
    mock_sct.monitors = [{}]
    mock_sct.close = MagicMock()
    return mock_sct


class TestScreenCapture:
    """ScreenCapture 的全面测试。"""

    # ---- __init__ ----

    @patch("src.vision.screen_capture.mss.mss")
    def test_init_creates_save_directory(self, mock_mss_cls, tmp_path):
        """初始化时应自动创建保存目录。"""
        save_dir = str(tmp_path / "nested" / "screenshots")
        mock_mss_cls.return_value = _make_mock_mss()

        ScreenCapture(save_path=save_dir)

        assert os.path.isdir(save_dir)

    @patch("src.vision.screen_capture.mss.mss")
    def test_init_default_state(self, mock_mss_cls, tmp_path):
        """初始化后 window_info 应为 None，save_path 应正确设置。"""
        mock_mss_cls.return_value = _make_mock_mss()

        sc = ScreenCapture(save_path=str(tmp_path))

        assert sc.window_info is None
        assert sc.save_path == tmp_path

    # ---- set_window ----

    @patch("src.vision.screen_capture.mss.mss")
    def test_set_window_updates_window_info(self, mock_mss_cls, tmp_path, mock_window_info):
        """set_window 应更新内部 window_info 属性。"""
        mock_mss_cls.return_value = _make_mock_mss()
        sc = ScreenCapture(save_path=str(tmp_path))

        assert sc.window_info is None
        sc.set_window(mock_window_info)

        assert sc.window_info is mock_window_info
        assert sc.window_info.hwnd == 12345

    # ---- capture ----

    @patch("src.vision.screen_capture.mss.mss")
    def test_capture_without_window_info_uses_first_monitor(self, mock_mss_cls, tmp_path):
        """未设置 window_info 时，capture 应使用 mss.monitors[0] 作为监控区域。"""
        fake_monitor = {"left": 0, "top": 0, "width": 1920, "height": 1080}
        mock_sct = _make_mock_mss()
        mock_sct.monitors = [fake_monitor]
        mock_mss_cls.return_value = mock_sct

        sc = ScreenCapture(save_path=str(tmp_path))
        result = sc.capture()

        # 验证 grab 被调用，且传入的是 monitors[0]
        mock_sct.grab.assert_called_once_with(fake_monitor)
        # 返回值应为真实的 PIL Image
        assert isinstance(result, Image.Image)

    @patch("src.vision.screen_capture.mss.mss")
    def test_capture_with_window_info_calculates_monitor_region(self, mock_mss_cls, tmp_path, mock_window_info):
        """设置 window_info 后，capture 应根据窗口位置计算监控区域。"""
        mock_sct = _make_mock_mss()
        mock_mss_cls.return_value = mock_sct

        sc = ScreenCapture(window_info=mock_window_info, save_path=str(tmp_path))
        result = sc.capture()

        expected_monitor = {
            "left": mock_window_info.left,
            "top": mock_window_info.top,
            "width": mock_window_info.width,
            "height": mock_window_info.height,
        }
        mock_sct.grab.assert_called_once_with(expected_monitor)
        assert isinstance(result, Image.Image)

    @patch("src.vision.screen_capture.mss.mss")
    def test_capture_with_region_offset_adds_window_position(self, mock_mss_cls, tmp_path, mock_window_info):
        """传入 region 参数时，坐标应加上窗口左上角偏移量。"""
        mock_sct = _make_mock_mss()
        mock_mss_cls.return_value = mock_sct

        sc = ScreenCapture(window_info=mock_window_info, save_path=str(tmp_path))
        region = (50, 30, 200, 150)
        result = sc.capture(region=region)

        expected_monitor = {
            "left": mock_window_info.left + region[0],  # 100 + 50 = 150
            "top": mock_window_info.top + region[1],    # 100 + 30 = 130
            "width": region[2],                         # 200
            "height": region[3],                        # 150
        }
        mock_sct.grab.assert_called_once_with(expected_monitor)
        assert isinstance(result, Image.Image)

    # ---- capture_to_numpy ----

    @patch("src.vision.screen_capture.mss.mss")
    def test_capture_to_numpy_returns_ndarray(self, mock_mss_cls, tmp_path):
        """capture_to_numpy 应返回 numpy ndarray，且形状与捕获尺寸一致。"""
        capture_size = (640, 480)
        mock_sct = _make_mock_mss(capture_size=capture_size)
        mock_sct.monitors = [{"left": 0, "top": 0, "width": 640, "height": 480}]
        mock_mss_cls.return_value = mock_sct

        sc = ScreenCapture(save_path=str(tmp_path))
        result = sc.capture_to_numpy()

        assert isinstance(result, np.ndarray)
        # PIL Image 转 numpy 后形状为 (height, width, 3)
        assert result.shape == (480, 640, 3)

    # ---- save_screenshot ----

    @patch("src.vision.screen_capture.mss.mss")
    def test_save_screenshot_with_custom_filename(self, mock_mss_cls, tmp_path):
        """指定文件名保存截图时，文件应存在且路径正确。"""
        mock_mss_cls.return_value = _make_mock_mss()

        sc = ScreenCapture(save_path=str(tmp_path))
        filepath = sc.save_screenshot(filename="custom.png")

        assert os.path.isfile(filepath)
        assert filepath.endswith("custom.png")
        # 用真实 PIL 验证文件可正常打开
        with Image.open(filepath) as img:
            assert img.mode == "RGB"

    @patch("src.vision.screen_capture.mss.mss")
    def test_save_screenshot_auto_generated_filename(self, mock_mss_cls, tmp_path):
        """未指定文件名时，应自动生成包含 'screenshot_' 的文件名。"""
        mock_mss_cls.return_value = _make_mock_mss()

        sc = ScreenCapture(save_path=str(tmp_path))
        filepath = sc.save_screenshot()

        basename = os.path.basename(filepath)
        assert "screenshot_" in basename
        assert basename.endswith(".png")
        assert os.path.isfile(filepath)

    # ---- capture_and_save ----

    @patch("src.vision.screen_capture.mss.mss")
    def test_capture_and_save_generates_correct_filename_format(self, mock_mss_cls, tmp_path):
        """capture_and_save 应生成包含步骤号、动作和时间戳的文件名。"""
        mock_mss_cls.return_value = _make_mock_mss()

        sc = ScreenCapture(save_path=str(tmp_path))
        filepath = sc.capture_and_save(step=5, action="click_start")

        basename = os.path.basename(filepath)
        assert basename.startswith("step005_")
        assert "click_start" in basename
        assert basename.endswith(".png")
        # 时间戳格式: YYYYMMDD_HHMMSS —— 验证包含下划线分隔的数字段
        parts = basename.replace("step005_click_start_", "").replace(".png", "")
        assert "_" in parts  # 日期_时间 中有下划线
        assert os.path.isfile(filepath)

    # ---- __del__ ----

    @patch("src.vision.screen_capture.mss.mss")
    def test_del_closes_mss(self, mock_mss_cls, tmp_path):
        """对象销毁时应调用 mss.close() 释放资源。"""
        mock_sct = _make_mock_mss()
        mock_mss_cls.return_value = mock_sct

        sc = ScreenCapture(save_path=str(tmp_path))
        sc.__del__()

        mock_sct.close.assert_called_once()
