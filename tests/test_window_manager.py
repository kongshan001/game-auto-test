"""窗口管理模块的测试。"""
import time
from unittest.mock import patch, MagicMock, call

import pytest

from src.action.window_manager import WindowInfo, WindowManager


# ---------------------------------------------------------------------------
# WindowInfo 数据类 —— 使用真实实例，零 mock（纯数据 + 纯计算）
# ---------------------------------------------------------------------------


class TestWindowInfo:
    """WindowInfo 数据类的属性计算测试。"""

    def test_center_property_calculation(self):
        """center 属性应正确计算窗口中心坐标。"""
        info = WindowInfo(
            hwnd=1, title="测试", left=100, top=200, width=800, height=600, process_id=100
        )
        assert info.center == (100 + 800 // 2, 200 + 600 // 2)
        assert info.center == (500, 500)

    def test_rect_property_calculation(self):
        """rect 属性应返回 (left, top, right, bottom) 元组。"""
        info = WindowInfo(
            hwnd=1, title="测试", left=50, top=60, width=300, height=400, process_id=200
        )
        assert info.rect == (50, 60, 50 + 300, 60 + 400)
        assert info.rect == (50, 60, 350, 460)

    def test_window_info_with_different_dimensions(self):
        """使用不同尺寸的 WindowInfo，center 和 rect 仍应正确。"""
        info = WindowInfo(
            hwnd=99, title="大窗口", left=0, top=0, width=1920, height=1080, process_id=300
        )
        assert info.center == (960, 540)
        assert info.rect == (0, 0, 1920, 1080)

        info2 = WindowInfo(
            hwnd=100, title="小窗口", left=1000, top=500, width=100, height=80, process_id=400
        )
        assert info2.center == (1050, 540)
        assert info2.rect == (1000, 500, 1100, 580)


# ---------------------------------------------------------------------------
# WindowManager —— 必须 mock win32gui / win32con / win32process / pygetwindow
# （平台特定依赖），但 WindowInfo 返回值使用真实实例
# ---------------------------------------------------------------------------


class TestWindowManager:
    """WindowManager 的全面测试。"""

    # ---- get_window_by_title ----

    @patch("src.action.window_manager.gw.getWindowsWithTitle")
    @patch("src.action.window_manager.win32gui.GetWindowText", return_value="游戏窗口")
    @patch("src.action.window_manager.win32gui.GetWindowRect", return_value=(10, 20, 810, 620))
    @patch("src.action.window_manager.win32process.GetWindowThreadProcessId", return_value=(999, 1234))
    def test_get_window_by_title_found(
        self, mock_get_tid, mock_rect, mock_text, mock_gw
    ):
        """通过标题查找窗口，窗口存在时应返回真实 WindowInfo 实例。"""
        mock_win = MagicMock()
        mock_win._hwnd = 5555
        mock_gw.return_value = [mock_win]

        wm = WindowManager()
        result = wm.get_window_by_title("游戏窗口")

        assert result is not None
        assert isinstance(result, WindowInfo)
        assert result.hwnd == 5555
        assert result.title == "游戏窗口"
        assert result.width == 800
        assert result.height == 600

    @patch("src.action.window_manager.gw.getWindowsWithTitle", return_value=[])
    def test_get_window_by_title_not_found(self, mock_gw):
        """通过标题查找窗口，窗口不存在时应返回 None。"""
        wm = WindowManager()
        result = wm.get_window_by_title("不存在的窗口")

        assert result is None

    # ---- get_window_by_pid ----

    @patch("src.action.window_manager.win32gui.IsWindowVisible", return_value=True)
    @patch("src.action.window_manager.win32process.GetWindowThreadProcessId")
    @patch("src.action.window_manager.win32gui.EnumWindows")
    @patch("src.action.window_manager.win32gui.GetWindowText", return_value="PID窗口")
    @patch("src.action.window_manager.win32gui.GetWindowRect", return_value=(0, 0, 640, 480))
    def test_get_window_by_pid_found(
        self, mock_rect, mock_text, mock_enum, mock_get_tid, mock_visible
    ):
        """通过 PID 查找窗口，匹配时应返回真实 WindowInfo 实例。"""
        target_pid = 5678

        def fake_enum_windows(callback, hwnds):
            """模拟枚举窗口回调，模拟两个窗口，其中一个 PID 匹配。"""
            mock_get_tid.side_effect = [
                (111, 9999),   # 第一个窗口，PID 不匹配
                (222, target_pid),  # 第二个窗口，PID 匹配
            ]
            # 模拟回调被调用两次
            callback(100, hwnds)
            # 第一个不匹配，不再追加
            callback(200, hwnds)

        mock_enum.side_effect = fake_enum_windows
        # _get_window_info 内部调用
        mock_get_tid_for_info = MagicMock(return_value=(333, target_pid))

        wm = WindowManager()
        with patch.object(wm, "_get_window_info") as mock_get_info:
            expected_info = WindowInfo(
                hwnd=200, title="PID窗口", left=0, top=0, width=640, height=480, process_id=target_pid
            )
            mock_get_info.return_value = expected_info

            result = wm.get_window_by_pid(target_pid)

        assert result is not None
        assert isinstance(result, WindowInfo)
        assert result.process_id == target_pid

    @patch("src.action.window_manager.win32gui.IsWindowVisible", return_value=True)
    @patch("src.action.window_manager.win32process.GetWindowThreadProcessId")
    @patch("src.action.window_manager.win32gui.EnumWindows")
    def test_get_window_by_pid_not_found(self, mock_enum, mock_get_tid, mock_visible):
        """通过 PID 查找窗口，无匹配时应返回 None。"""
        def fake_enum_windows(callback, hwnds):
            mock_get_tid.return_value = (111, 9999)  # PID 不匹配
            callback(100, hwnds)

        mock_enum.side_effect = fake_enum_windows

        wm = WindowManager()
        result = wm.get_window_by_pid(12345)

        assert result is None

    # ---- activate_window ----

    @patch("src.action.window_manager.win32gui.SetForegroundWindow")
    @patch("src.action.window_manager.win32gui.ShowWindow")
    def test_activate_window_success(self, mock_show, mock_fg):
        """激活窗口成功时应返回 True。"""
        wm = WindowManager()
        result = wm.activate_window(1234)

        mock_show.assert_called_once()  # ShowWindow(hwnd, SW_RESTORE)
        mock_fg.assert_called_once_with(1234)
        assert result is True

    @patch("src.action.window_manager.win32gui.SetForegroundWindow", side_effect=Exception("fail"))
    @patch("src.action.window_manager.win32gui.ShowWindow")
    def test_activate_window_failure(self, mock_show, mock_fg):
        """激活窗口失败时应返回 False，不应抛出异常。"""
        wm = WindowManager()
        result = wm.activate_window(1234)

        assert result is False

    # ---- is_window_valid ----

    @patch("src.action.window_manager.win32gui.IsWindowVisible", return_value=True)
    @patch("src.action.window_manager.win32gui.IsWindow", return_value=True)
    def test_is_window_valid_true(self, mock_is_win, mock_visible):
        """窗口有效且可见时，is_window_valid 应返回 True。"""
        wm = WindowManager()
        assert wm.is_window_valid(1234) is True

    @patch("src.action.window_manager.win32gui.IsWindow", return_value=False)
    def test_is_window_valid_false(self, mock_is_win):
        """窗口无效时，is_window_valid 应返回 False。"""
        wm = WindowManager()
        assert wm.is_window_valid(0) is False

    # ---- wait_for_window ----

    @patch("src.action.window_manager.time.sleep")
    @patch("src.action.window_manager.time.time")
    def test_wait_for_window_success(self, mock_time, mock_sleep):
        """等待窗口出现成功时，应返回真实 WindowInfo 实例。"""
        # 模拟时间推进：start=0, 第一次检查时 time.time() 返回 0.1（未超时）
        mock_time.side_effect = [0.0, 0.1]

        mock_process = MagicMock()
        mock_process.poll.return_value = None  # 进程仍在运行
        mock_process.pid = 9999

        expected_info = WindowInfo(
            hwnd=7777, title="游戏", left=0, top=0, width=1024, height=768, process_id=9999
        )

        wm = WindowManager()
        with patch.object(wm, "get_window_by_pid", return_value=expected_info) as mock_get_pid:
            result = wm.wait_for_window(mock_process, timeout=30)

        assert result is not None
        assert isinstance(result, WindowInfo)
        assert result.hwnd == 7777
        mock_sleep.assert_not_called()  # 第一次就找到了，不需要 sleep

    @patch("src.action.window_manager.time.sleep")
    @patch("src.action.window_manager.time.time")
    def test_wait_for_window_timeout(self, mock_time, mock_sleep):
        """等待窗口超时时，应返回 None。"""
        # 模拟时间推进：start=0, 然后每次检查时 time.time() 都大于 timeout
        mock_time.side_effect = [0.0, 31.0]  # 已超过 30 秒超时

        mock_process = MagicMock()
        mock_process.poll.return_value = None
        mock_process.pid = 9999

        wm = WindowManager()
        with patch.object(wm, "get_window_by_pid", return_value=None):
            result = wm.wait_for_window(mock_process, timeout=30)

        assert result is None

    # ---- _get_window_info ----

    @patch("src.action.window_manager.win32process.GetWindowThreadProcessId", return_value=(555, 4321))
    @patch("src.action.window_manager.win32gui.GetWindowRect", return_value=(20, 30, 820, 630))
    @patch("src.action.window_manager.win32gui.GetWindowText", return_value="目标窗口")
    def test_get_window_info_builds_correct_window_info(
        self, mock_text, mock_rect, mock_get_tid
    ):
        """_get_window_info 应从 win32 调用结果构建真实的 WindowInfo 实例。"""
        wm = WindowManager()
        result = wm._get_window_info(3456)

        assert isinstance(result, WindowInfo)
        assert result.hwnd == 3456
        assert result.title == "目标窗口"
        assert result.left == 20
        assert result.top == 30
        assert result.width == 800   # 820 - 20
        assert result.height == 600  # 630 - 30
        assert result.process_id == 4321
