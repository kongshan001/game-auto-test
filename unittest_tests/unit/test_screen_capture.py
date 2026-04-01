"""
Unit tests for screen_capture module.

Tests ScreenCapture class with all external dependencies mocked:
mss, numpy, PIL.Image, os, time, pathlib
"""
import sys
import unittest
from unittest.mock import MagicMock, Mock, patch, PropertyMock

# ---------------------------------------------------------------------------
# sys.path adjustment so the src package is importable
# ---------------------------------------------------------------------------
sys.path.insert(0, "d:/claude_code_proj/py_unit_test_skills/game-auto-test/src")

from vision.screen_capture import ScreenCapture  # noqa: E402


# ---------------------------------------------------------------------------
# Lightweight stub that mimics WindowInfo (dataclass)
# ---------------------------------------------------------------------------
class _FakeWindowInfo:
    """Mimics the WindowInfo dataclass used by ScreenCapture."""

    def __init__(
        self,
        left: int = 100,
        top: int = 200,
        width: int = 800,
        height: int = 600,
        **_kwargs,
    ):
        self.hwnd = 1
        self.title = "TestWindow"
        self.left = left
        self.top = top
        self.width = width
        self.height = height
        self.process_id = 1234


# ===========================================================================
# Test suite
# ===========================================================================
class TestScreenCapture(unittest.TestCase):
    """Tests for ScreenCapture."""

    # ------------------------------------------------------------------
    # __init__
    # ------------------------------------------------------------------
    @patch("vision.screen_capture.mss")
    @patch("vision.screen_capture.Path")
    def test_init_default_save_path(self, mock_path_cls, mock_mss):
        """__init__ with default save_path creates a Path and calls mkdir."""
        mock_path_inst = MagicMock()
        mock_path_cls.return_value = mock_path_inst

        sc = ScreenCapture()

        mock_path_cls.assert_called_once_with("./logs/screenshots")
        mock_path_inst.mkdir.assert_called_once_with(parents=True, exist_ok=True)
        mock_mss.mss.assert_called_once()
        self.assertIsNone(sc.window_info)

    @patch("vision.screen_capture.mss")
    @patch("vision.screen_capture.Path")
    def test_init_custom_save_path(self, mock_path_cls, mock_mss):
        """__init__ with custom save_path forwards it to Path."""
        mock_path_inst = MagicMock()
        mock_path_cls.return_value = mock_path_inst

        sc = ScreenCapture(save_path="/tmp/custom_shots")

        mock_path_cls.assert_called_once_with("/tmp/custom_shots")
        mock_path_inst.mkdir.assert_called_once()

    @patch("vision.screen_capture.mss")
    @patch("vision.screen_capture.Path")
    def test_init_with_window_info(self, mock_path_cls, mock_mss):
        """__init__ stores window_info when provided."""
        win = _FakeWindowInfo()
        sc = ScreenCapture(window_info=win)
        self.assertIs(sc.window_info, win)

    # ------------------------------------------------------------------
    # set_window
    # ------------------------------------------------------------------
    @patch("vision.screen_capture.mss")
    @patch("vision.screen_capture.Path")
    def test_set_window_valid(self, mock_path_cls, mock_mss):
        """set_window stores a valid WindowInfo."""
        sc = ScreenCapture()
        win = _FakeWindowInfo(left=10, top=20, width=640, height=480)
        sc.set_window(win)
        self.assertIs(sc.window_info, win)

    @patch("vision.screen_capture.mss")
    @patch("vision.screen_capture.Path")
    def test_set_window_none(self, mock_path_cls, mock_mss):
        """set_window(None) clears window_info (falls back to fullscreen)."""
        win = _FakeWindowInfo()
        sc = ScreenCapture(window_info=win)
        self.assertIsNotNone(sc.window_info)

        sc.set_window(None)
        self.assertIsNone(sc.window_info)

    # ------------------------------------------------------------------
    # capture
    # ------------------------------------------------------------------
    @patch("vision.screen_capture.Image")
    @patch("vision.screen_capture.mss")
    @patch("vision.screen_capture.Path")
    def test_capture_no_window_fullscreen(self, mock_path_cls, mock_mss, mock_image):
        """capture with no window_info uses monitors[0] (fullscreen)."""
        mock_sct = MagicMock()
        mock_sct.monitors = [{"left": 0, "top": 0, "width": 1920, "height": 1080}]
        mock_grab_result = MagicMock()
        mock_grab_result.size = (1920, 1080)
        mock_grab_result.rgb = b"\x00" * (1920 * 1080 * 3)
        mock_sct.grab.return_value = mock_grab_result
        mock_mss.mss.return_value = mock_sct

        mock_img = MagicMock()
        mock_img.convert.return_value = mock_img
        mock_image.frombytes.return_value = mock_img

        sc = ScreenCapture()
        result = sc.capture()

        mock_sct.grab.assert_called_once_with(mock_sct.monitors[0])
        mock_image.frombytes.assert_called_once()
        mock_img.convert.assert_called_once_with("RGB")
        self.assertIs(result, mock_img)

    @patch("vision.screen_capture.Image")
    @patch("vision.screen_capture.mss")
    @patch("vision.screen_capture.Path")
    def test_capture_with_window_no_region(self, mock_path_cls, mock_mss, mock_image):
        """capture with window but no region captures entire window."""
        mock_sct = MagicMock()
        mock_grab_result = MagicMock()
        mock_grab_result.size = (800, 600)
        mock_grab_result.rgb = b"\x00" * (800 * 600 * 3)
        mock_sct.grab.return_value = mock_grab_result
        mock_mss.mss.return_value = mock_sct

        mock_img = MagicMock()
        mock_img.convert.return_value = mock_img
        mock_image.frombytes.return_value = mock_img

        win = _FakeWindowInfo(left=100, top=200, width=800, height=600)
        sc = ScreenCapture(window_info=win)
        result = sc.capture()

        expected_monitor = {
            "left": 100,
            "top": 200,
            "width": 800,
            "height": 600,
        }
        mock_sct.grab.assert_called_once_with(expected_monitor)
        self.assertIs(result, mock_img)

    @patch("vision.screen_capture.Image")
    @patch("vision.screen_capture.mss")
    @patch("vision.screen_capture.Path")
    def test_capture_with_window_and_region(self, mock_path_cls, mock_mss, mock_image):
        """capture with window + region offsets region relative to window."""
        mock_sct = MagicMock()
        mock_grab_result = MagicMock()
        mock_grab_result.size = (200, 150)
        mock_grab_result.rgb = b"\x00" * (200 * 150 * 3)
        mock_sct.grab.return_value = mock_grab_result
        mock_mss.mss.return_value = mock_sct

        mock_img = MagicMock()
        mock_img.convert.return_value = mock_img
        mock_image.frombytes.return_value = mock_img

        win = _FakeWindowInfo(left=100, top=200, width=800, height=600)
        sc = ScreenCapture(window_info=win)
        region = (10, 20, 200, 150)
        result = sc.capture(region)

        expected_monitor = {
            "left": 110,   # 100 + 10
            "top": 220,    # 200 + 20
            "width": 200,
            "height": 150,
        }
        mock_sct.grab.assert_called_once_with(expected_monitor)
        self.assertIs(result, mock_img)

    @patch("vision.screen_capture.Image")
    @patch("vision.screen_capture.mss")
    @patch("vision.screen_capture.Path")
    def test_capture_without_window_is_fullscreen(self, mock_path_cls, mock_mss, mock_image):
        """capture with window_info=None always captures monitors[0]."""
        mock_sct = MagicMock()
        mock_sct.monitors = [{"left": 0, "top": 0, "width": 1920, "height": 1080}]
        mock_grab_result = MagicMock()
        mock_grab_result.size = (1920, 1080)
        mock_grab_result.rgb = b"\x00" * (1920 * 1080 * 3)
        mock_sct.grab.return_value = mock_grab_result
        mock_mss.mss.return_value = mock_sct

        mock_img = MagicMock()
        mock_img.convert.return_value = mock_img
        mock_image.frombytes.return_value = mock_img

        sc = ScreenCapture()
        # Ensure no window set
        self.assertIsNone(sc.window_info)
        result = sc.capture()

        mock_sct.grab.assert_called_once_with(mock_sct.monitors[0])
        self.assertIs(result, mock_img)

    # ------------------------------------------------------------------
    # capture_to_numpy
    # ------------------------------------------------------------------
    @patch("vision.screen_capture.np")
    @patch("vision.screen_capture.Image")
    @patch("vision.screen_capture.mss")
    @patch("vision.screen_capture.Path")
    def test_capture_to_numpy_returns_ndarray(self, mock_path_cls, mock_mss, mock_image, mock_np):
        """capture_to_numpy calls np.array on the captured image."""
        mock_sct = MagicMock()
        mock_sct.monitors = [{"left": 0, "top": 0, "width": 100, "height": 100}]
        mock_grab_result = MagicMock()
        mock_grab_result.size = (100, 100)
        mock_grab_result.rgb = b"\x00" * (100 * 100 * 3)
        mock_sct.grab.return_value = mock_grab_result
        mock_mss.mss.return_value = mock_sct

        mock_img = MagicMock()
        mock_img.convert.return_value = mock_img
        mock_image.frombytes.return_value = mock_img

        fake_array = MagicMock(name="ndarray")
        mock_np.array.return_value = fake_array

        sc = ScreenCapture()
        result = sc.capture_to_numpy()

        mock_np.array.assert_called_once_with(mock_img)
        self.assertIs(result, fake_array)

    @patch("vision.screen_capture.np")
    @patch("vision.screen_capture.Image")
    @patch("vision.screen_capture.mss")
    @patch("vision.screen_capture.Path")
    def test_capture_to_numpy_with_region(self, mock_path_cls, mock_mss, mock_image, mock_np):
        """capture_to_numpy forwards region to capture."""
        mock_sct = MagicMock()
        mock_grab_result = MagicMock()
        mock_grab_result.size = (50, 50)
        mock_grab_result.rgb = b"\x00" * (50 * 50 * 3)
        mock_sct.grab.return_value = mock_grab_result
        mock_mss.mss.return_value = mock_sct

        mock_img = MagicMock()
        mock_img.convert.return_value = mock_img
        mock_image.frombytes.return_value = mock_img
        mock_np.array.return_value = MagicMock(name="ndarray")

        win = _FakeWindowInfo()
        sc = ScreenCapture(window_info=win)
        region = (0, 0, 50, 50)
        result = sc.capture_to_numpy(region)

        expected_monitor = {
            "left": win.left,
            "top": win.top,
            "width": 50,
            "height": 50,
        }
        mock_sct.grab.assert_called_once_with(expected_monitor)
        mock_np.array.assert_called_once_with(mock_img)
        self.assertIsNotNone(result)

    # ------------------------------------------------------------------
    # save_screenshot
    # ------------------------------------------------------------------
    @patch("vision.screen_capture.Image")
    @patch("vision.screen_capture.mss")
    @patch("vision.screen_capture.Path")
    @patch("vision.screen_capture.time")
    def test_save_screenshot_auto_filename(self, mock_time, mock_path_cls, mock_mss, mock_image):
        """save_screenshot with no filename generates one with timestamp."""
        mock_time.strftime.return_value = "20260401_120000"

        mock_sct = MagicMock()
        mock_sct.monitors = [{"left": 0, "top": 0, "width": 100, "height": 100}]
        mock_grab_result = MagicMock()
        mock_grab_result.size = (100, 100)
        mock_grab_result.rgb = b"\x00" * (100 * 100 * 3)
        mock_sct.grab.return_value = mock_grab_result
        mock_mss.mss.return_value = mock_sct

        mock_img = MagicMock()
        mock_img.convert.return_value = mock_img
        mock_image.frombytes.return_value = mock_img

        mock_path_inst = MagicMock()
        # save_path / "screenshot_20260401_120000.png" returns a new mock
        joined = MagicMock()
        joined.__str__ = lambda self_: "d:/logs/screenshots/screenshot_20260401_120000.png"
        mock_path_inst.__truediv__ = Mock(return_value=joined)
        mock_path_cls.return_value = mock_path_inst

        sc = ScreenCapture()
        result = sc.save_screenshot()

        mock_time.strftime.assert_called_once_with("%Y%m%d_%H%M%S")
        mock_img.save.assert_called_once_with(joined)
        self.assertIn("screenshot_20260401_120000.png", result)

    @patch("vision.screen_capture.Image")
    @patch("vision.screen_capture.mss")
    @patch("vision.screen_capture.Path")
    def test_save_screenshot_custom_filename(self, mock_path_cls, mock_mss, mock_image):
        """save_screenshot with custom filename uses it directly."""
        mock_sct = MagicMock()
        mock_sct.monitors = [{"left": 0, "top": 0, "width": 100, "height": 100}]
        mock_grab_result = MagicMock()
        mock_grab_result.size = (100, 100)
        mock_grab_result.rgb = b"\x00" * (100 * 100 * 3)
        mock_sct.grab.return_value = mock_grab_result
        mock_mss.mss.return_value = mock_sct

        mock_img = MagicMock()
        mock_img.convert.return_value = mock_img
        mock_image.frombytes.return_value = mock_img

        mock_path_inst = MagicMock()
        joined = MagicMock()
        joined.__str__ = lambda self_: "d:/logs/screenshots/custom.png"
        mock_path_inst.__truediv__ = Mock(return_value=joined)
        mock_path_cls.return_value = mock_path_inst

        sc = ScreenCapture()
        result = sc.save_screenshot(filename="custom.png")

        mock_img.save.assert_called_once_with(joined)
        self.assertIn("custom.png", result)

    @patch("vision.screen_capture.Image")
    @patch("vision.screen_capture.mss")
    @patch("vision.screen_capture.Path")
    def test_save_screenshot_creates_directory(self, mock_path_cls, mock_mss, mock_image):
        """save_screenshot ensures the save directory exists via __init__ mkdir."""
        mock_sct = MagicMock()
        mock_sct.monitors = [{"left": 0, "top": 0, "width": 100, "height": 100}]
        mock_grab_result = MagicMock()
        mock_grab_result.size = (100, 100)
        mock_grab_result.rgb = b"\x00" * (100 * 100 * 3)
        mock_sct.grab.return_value = mock_grab_result
        mock_mss.mss.return_value = mock_sct

        mock_img = MagicMock()
        mock_img.convert.return_value = mock_img
        mock_image.frombytes.return_value = mock_img

        mock_path_inst = MagicMock()
        joined = MagicMock()
        joined.__str__ = lambda self_: "new_dir/test.png"
        mock_path_inst.__truediv__ = Mock(return_value=joined)
        mock_path_cls.return_value = mock_path_inst

        sc = ScreenCapture()
        mock_path_inst.mkdir.assert_called_once_with(parents=True, exist_ok=True)

        result = sc.save_screenshot(filename="test.png")
        self.assertIn("test.png", result)

    # ------------------------------------------------------------------
    # capture_and_save
    # ------------------------------------------------------------------
    @patch("vision.screen_capture.Image")
    @patch("vision.screen_capture.mss")
    @patch("vision.screen_capture.Path")
    @patch("vision.screen_capture.time")
    def test_capture_and_save_with_step(self, mock_time, mock_path_cls, mock_mss, mock_image):
        """capture_and_save builds filename from step number."""
        mock_time.strftime.return_value = "20260401_130000"

        mock_sct = MagicMock()
        mock_sct.monitors = [{"left": 0, "top": 0, "width": 100, "height": 100}]
        mock_grab_result = MagicMock()
        mock_grab_result.size = (100, 100)
        mock_grab_result.rgb = b"\x00" * (100 * 100 * 3)
        mock_sct.grab.return_value = mock_grab_result
        mock_mss.mss.return_value = mock_sct

        mock_img = MagicMock()
        mock_img.convert.return_value = mock_img
        mock_image.frombytes.return_value = mock_img

        mock_path_inst = MagicMock()
        joined = MagicMock()
        joined.__str__ = lambda self_: "d:/logs/screenshots/step005__20260401_130000.png"
        mock_path_inst.__truediv__ = Mock(return_value=joined)
        mock_path_cls.return_value = mock_path_inst

        sc = ScreenCapture()
        result = sc.capture_and_save(step=5)

        # Filename should contain step number zero-padded
        self.assertIn("step005", result)
        self.assertIn("20260401_130000", result)
        mock_img.save.assert_called_once_with(joined)

    @patch("vision.screen_capture.Image")
    @patch("vision.screen_capture.mss")
    @patch("vision.screen_capture.Path")
    @patch("vision.screen_capture.time")
    def test_capture_and_save_with_action(self, mock_time, mock_path_cls, mock_mss, mock_image):
        """capture_and_save includes action string in filename."""
        mock_time.strftime.return_value = "20260401_140000"

        mock_sct = MagicMock()
        mock_sct.monitors = [{"left": 0, "top": 0, "width": 100, "height": 100}]
        mock_grab_result = MagicMock()
        mock_grab_result.size = (100, 100)
        mock_grab_result.rgb = b"\x00" * (100 * 100 * 3)
        mock_sct.grab.return_value = mock_grab_result
        mock_mss.mss.return_value = mock_sct

        mock_img = MagicMock()
        mock_img.convert.return_value = mock_img
        mock_image.frombytes.return_value = mock_img

        mock_path_inst = MagicMock()
        joined = MagicMock()
        joined.__str__ = lambda self_: "d:/logs/screenshots/step001_click_20260401_140000.png"
        mock_path_inst.__truediv__ = Mock(return_value=joined)
        mock_path_cls.return_value = mock_path_inst

        sc = ScreenCapture()
        result = sc.capture_and_save(step=1, action="click")

        self.assertIn("step001", result)
        self.assertIn("click", result)
        self.assertIn("20260401_140000", result)

    @patch("vision.screen_capture.Image")
    @patch("vision.screen_capture.mss")
    @patch("vision.screen_capture.Path")
    @patch("vision.screen_capture.time")
    def test_capture_and_save_empty_action(self, mock_time, mock_path_cls, mock_mss, mock_image):
        """capture_and_save with empty action string produces correct filename."""
        mock_time.strftime.return_value = "20260401_150000"

        mock_sct = MagicMock()
        mock_sct.monitors = [{"left": 0, "top": 0, "width": 100, "height": 100}]
        mock_grab_result = MagicMock()
        mock_grab_result.size = (100, 100)
        mock_grab_result.rgb = b"\x00" * (100 * 100 * 3)
        mock_sct.grab.return_value = mock_grab_result
        mock_mss.mss.return_value = mock_sct

        mock_img = MagicMock()
        mock_img.convert.return_value = mock_img
        mock_image.frombytes.return_value = mock_img

        mock_path_inst = MagicMock()
        joined = MagicMock()
        joined.__str__ = lambda self_: "d:/logs/screenshots/step002__20260401_150000.png"
        mock_path_inst.__truediv__ = Mock(return_value=joined)
        mock_path_cls.return_value = mock_path_inst

        sc = ScreenCapture()
        result = sc.capture_and_save(step=2, action="")

        # Empty action still yields a valid filename pattern
        self.assertIn("step002", result)

    @patch("vision.screen_capture.Image")
    @patch("vision.screen_capture.mss")
    @patch("vision.screen_capture.Path")
    @patch("vision.screen_capture.time")
    def test_capture_and_save_with_region(self, mock_time, mock_path_cls, mock_mss, mock_image):
        """capture_and_save forwards region to capture."""
        mock_time.strftime.return_value = "20260401_160000"

        mock_sct = MagicMock()
        mock_grab_result = MagicMock()
        mock_grab_result.size = (50, 50)
        mock_grab_result.rgb = b"\x00" * (50 * 50 * 3)
        mock_sct.grab.return_value = mock_grab_result
        mock_mss.mss.return_value = mock_sct

        mock_img = MagicMock()
        mock_img.convert.return_value = mock_img
        mock_image.frombytes.return_value = mock_img

        mock_path_inst = MagicMock()
        joined = MagicMock()
        joined.__str__ = lambda self_: "d:/logs/screenshots/step001_move_20260401_160000.png"
        mock_path_inst.__truediv__ = Mock(return_value=joined)
        mock_path_cls.return_value = mock_path_inst

        win = _FakeWindowInfo(left=10, top=20, width=800, height=600)
        sc = ScreenCapture(window_info=win)
        region = (5, 5, 50, 50)
        result = sc.capture_and_save(step=1, action="move", region=region)

        expected_monitor = {
            "left": 15,   # 10 + 5
            "top": 25,    # 20 + 5
            "width": 50,
            "height": 50,
        }
        mock_sct.grab.assert_called_with(expected_monitor)
        self.assertIn("move", result)

    # ------------------------------------------------------------------
    # __del__
    # ------------------------------------------------------------------
    @patch("vision.screen_capture.mss")
    @patch("vision.screen_capture.Path")
    def test_del_closes_sct(self, mock_path_cls, mock_mss):
        """__del__ calls _sct.close() to clean up resources."""
        mock_sct = MagicMock()
        mock_mss.mss.return_value = mock_sct

        sc = ScreenCapture()
        sc.__del__()

        mock_sct.close.assert_called_once()

    @patch("vision.screen_capture.mss")
    @patch("vision.screen_capture.Path")
    def test_del_handles_exception(self, mock_path_cls, mock_mss):
        """__del__ silently ignores exceptions from _sct.close()."""
        mock_sct = MagicMock()
        mock_sct.close.side_effect = RuntimeError("already closed")
        mock_mss.mss.return_value = mock_sct

        sc = ScreenCapture()
        # Should not raise
        sc.__del__()


if __name__ == "__main__":
    unittest.main()
