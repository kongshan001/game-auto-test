"""
Unit tests for window_manager module.
Mocks all external dependencies: win32gui, win32con, win32process, pygetwindow, subprocess, time.
"""
import sys
import unittest
from unittest.mock import patch, MagicMock, call

# Adjust sys.path so the src package is importable
sys.path.insert(0, "d:/claude_code_proj/py_unit_test_skills/game-auto-test/src")

# Patch heavy/win32 dependencies before importing the module under test.
# We create persistent mock modules and install them so that the import
# inside window_manager.py resolves to our mocks.
mock_win32gui = MagicMock()
mock_win32con = MagicMock()
mock_win32process = MagicMock()
mock_pygetwindow = MagicMock()

for mod_name, mock_mod in [
    ("win32gui", mock_win32gui),
    ("win32con", mock_win32con),
    ("win32process", mock_win32process),
    ("pygetwindow", mock_pygetwindow),
]:
    sys.modules[mod_name] = mock_mod

# Now safe to import
from action.window_manager import WindowInfo, WindowManager  # noqa: E402


class TestWindowInfo(unittest.TestCase):
    """Tests for the WindowInfo dataclass and its properties."""

    # ------------------------------------------------------------------
    # Creation
    # ------------------------------------------------------------------
    def test_creation_with_all_fields(self):
        info = WindowInfo(
            hwnd=1001,
            title="TestWindow",
            left=10,
            top=20,
            width=800,
            height=600,
            process_id=42,
        )
        self.assertEqual(info.hwnd, 1001)
        self.assertEqual(info.title, "TestWindow")
        self.assertEqual(info.left, 10)
        self.assertEqual(info.top, 20)
        self.assertEqual(info.width, 800)
        self.assertEqual(info.height, 600)
        self.assertEqual(info.process_id, 42)

    def test_creation_defaults_are_required(self):
        """WindowInfo is a dataclass with no defaults -- all fields required."""
        with self.assertRaises(TypeError):
            WindowInfo()  # type: ignore[call-arg]

    # ------------------------------------------------------------------
    # center property
    # ------------------------------------------------------------------
    def test_center_returns_midpoint(self):
        info = WindowInfo(
            hwnd=1, title="", left=0, top=0, width=1000, height=800, process_id=1
        )
        self.assertEqual(info.center, (500, 400))

    def test_center_with_nonzero_origin(self):
        info = WindowInfo(
            hwnd=1, title="", left=200, top=100, width=600, height=400, process_id=1
        )
        self.assertEqual(info.center, (200 + 300, 100 + 200))
        self.assertEqual(info.center, (500, 300))

    def test_center_with_odd_dimensions(self):
        info = WindowInfo(
            hwnd=1, title="", left=0, top=0, width=101, height=51, process_id=1
        )
        # Integer division: 101 // 2 == 50, 51 // 2 == 25
        self.assertEqual(info.center, (50, 25))

    # ------------------------------------------------------------------
    # rect property
    # ------------------------------------------------------------------
    def test_rect_returns_left_top_right_bottom(self):
        info = WindowInfo(
            hwnd=1, title="", left=10, top=20, width=800, height=600, process_id=1
        )
        self.assertEqual(info.rect, (10, 20, 810, 620))

    def test_rect_with_zero_origin(self):
        info = WindowInfo(
            hwnd=1, title="", left=0, top=0, width=1920, height=1080, process_id=1
        )
        self.assertEqual(info.rect, (0, 0, 1920, 1080))

    def test_rect_with_large_values(self):
        info = WindowInfo(
            hwnd=1, title="", left=5000, top=3000, width=1000, height=500, process_id=1
        )
        self.assertEqual(info.rect, (5000, 3000, 6000, 3500))


class TestWindowManagerInit(unittest.TestCase):
    """Tests for WindowManager.__init__."""

    def test_hwnd_initially_none(self):
        mgr = WindowManager()
        self.assertIsNone(mgr._hwnd)


class TestWindowManagerGetWindowByTitle(unittest.TestCase):
    """Tests for WindowManager.get_window_by_title."""

    def setUp(self):
        self.mgr = WindowManager()

    @patch.object(WindowManager, "_get_window_info")
    def test_returns_window_info_when_found(self, mock_get_info):
        mock_window = MagicMock()
        mock_window._hwnd = 1234
        mock_pygetwindow.getWindowsWithTitle.reset_mock()
        mock_pygetwindow.getWindowsWithTitle.return_value = [mock_window]

        expected_info = WindowInfo(
            hwnd=1234, title="Game", left=0, top=0, width=800, height=600, process_id=10
        )
        mock_get_info.return_value = expected_info

        result = self.mgr.get_window_by_title("Game")
        self.assertEqual(result, expected_info)
        mock_pygetwindow.getWindowsWithTitle.assert_called_once_with("Game")
        mock_get_info.assert_called_once_with(1234)

    def test_returns_none_when_no_windows(self):
        mock_pygetwindow.getWindowsWithTitle.reset_mock()
        mock_pygetwindow.getWindowsWithTitle.return_value = []
        result = self.mgr.get_window_by_title("NonExistent")
        self.assertIsNone(result)

    def test_returns_none_when_empty_title(self):
        mock_pygetwindow.getWindowsWithTitle.reset_mock()
        mock_pygetwindow.getWindowsWithTitle.return_value = []
        result = self.mgr.get_window_by_title("")
        self.assertIsNone(result)


class TestWindowManagerGetWindowByProcessName(unittest.TestCase):
    """Tests for WindowManager.get_window_by_process_name."""

    def setUp(self):
        self.mgr = WindowManager()

    @patch.object(WindowManager, "_get_window_info")
    def test_finds_window_by_process_name(self, mock_get_info):
        """Simulates EnumWindows finding a matching hwnd."""
        expected_info = WindowInfo(
            hwnd=500, title="notepad", left=0, top=0, width=800, height=600, process_id=99
        )
        mock_get_info.return_value = expected_info

        def fake_enum_windows(callback, result_list):
            callback(500, result_list)

        mock_win32gui.EnumWindows.reset_mock()
        mock_win32gui.EnumWindows.side_effect = fake_enum_windows
        mock_win32gui.IsWindowVisible.reset_mock()
        mock_win32gui.IsWindowVisible.return_value = True
        mock_win32gui.GetWindowText.reset_mock()
        mock_win32gui.GetWindowText.return_value = "Untitled - Notepad"
        mock_win32process.GetWindowThreadProcessId.reset_mock()
        mock_win32process.GetWindowThreadProcessId.return_value = (1, 99)

        mock_proc = MagicMock()
        mock_proc.stdout.read.return_value = b'"notepad.exe","99","Console","1"\r\n'
        mock_proc.returncode = 0

        with patch("action.window_manager.subprocess.Popen", return_value=mock_proc):
            result = self.mgr.get_window_by_process_name("notepad")

        self.assertEqual(result, expected_info)
        mock_get_info.assert_called_once_with(500)

    def test_returns_none_when_no_matching_process(self):
        """EnumWindows runs but no hwnd matches the target process name."""

        def fake_enum_windows(callback, result_list):
            callback(100, result_list)

        mock_win32gui.EnumWindows.reset_mock()
        mock_win32gui.EnumWindows.side_effect = fake_enum_windows
        mock_win32gui.IsWindowVisible.reset_mock()
        mock_win32gui.IsWindowVisible.return_value = True
        mock_win32gui.GetWindowText.reset_mock()
        mock_win32gui.GetWindowText.return_value = "Some Window"
        mock_win32process.GetWindowThreadProcessId.reset_mock()
        mock_win32process.GetWindowThreadProcessId.return_value = (1, 55)

        mock_proc = MagicMock()
        mock_proc.stdout.read.return_value = b'"explorer.exe","55","Console","1"\r\n'

        with patch("action.window_manager.subprocess.Popen", return_value=mock_proc):
            result = self.mgr.get_window_by_process_name("notepad.exe")

        self.assertIsNone(result)

    def test_returns_none_when_enum_windows_raises(self):
        mock_win32gui.EnumWindows.reset_mock()
        mock_win32gui.EnumWindows.side_effect = Exception("enum failed")
        result = self.mgr.get_window_by_process_name("anything")
        self.assertIsNone(result)

    def test_invisible_windows_are_skipped(self):
        """If IsWindowVisible returns False, the window should not be inspected."""
        collected = []

        def fake_enum_windows(callback, result_list):
            callback(200, result_list)
            collected.extend(result_list)

        mock_win32gui.EnumWindows.reset_mock()
        mock_win32gui.EnumWindows.side_effect = fake_enum_windows
        mock_win32gui.IsWindowVisible.reset_mock()
        mock_win32gui.IsWindowVisible.return_value = False

        result = self.mgr.get_window_by_process_name("whatever")
        self.assertIsNone(result)
        self.assertEqual(collected, [])

    def test_empty_title_window_is_skipped(self):
        """Windows with empty titles should not be processed."""

        def fake_enum_windows(callback, result_list):
            callback(300, result_list)

        mock_win32gui.EnumWindows.reset_mock()
        mock_win32gui.EnumWindows.side_effect = fake_enum_windows
        mock_win32gui.IsWindowVisible.reset_mock()
        mock_win32gui.IsWindowVisible.return_value = True
        mock_win32gui.GetWindowText.reset_mock()
        mock_win32gui.GetWindowText.return_value = ""

        result = self.mgr.get_window_by_process_name("anything")
        self.assertIsNone(result)

    def test_subprocess_exception_is_swallowed(self):
        """If Popen raises, the callback should still return True."""

        def fake_enum_windows(callback, result_list):
            callback(400, result_list)

        mock_win32gui.EnumWindows.reset_mock()
        mock_win32gui.EnumWindows.side_effect = fake_enum_windows
        mock_win32gui.IsWindowVisible.reset_mock()
        mock_win32gui.IsWindowVisible.return_value = True
        mock_win32gui.GetWindowText.reset_mock()
        mock_win32gui.GetWindowText.return_value = "Window"
        mock_win32process.GetWindowThreadProcessId.reset_mock()
        mock_win32process.GetWindowThreadProcessId.return_value = (1, 77)

        with patch("action.window_manager.subprocess.Popen", side_effect=OSError("fail")):
            result = self.mgr.get_window_by_process_name("anything")

        self.assertIsNone(result)


class TestWindowManagerGetWindowByPid(unittest.TestCase):
    """Tests for WindowManager.get_window_by_pid."""

    def setUp(self):
        self.mgr = WindowManager()

    @patch.object(WindowManager, "_get_window_info")
    def test_finds_window_by_pid(self, mock_get_info):
        expected_info = WindowInfo(
            hwnd=700, title="App", left=0, top=0, width=100, height=100, process_id=42
        )
        mock_get_info.return_value = expected_info

        def fake_enum_windows(callback, result_list):
            callback(700, result_list)

        mock_win32gui.EnumWindows.reset_mock()
        mock_win32gui.EnumWindows.side_effect = fake_enum_windows
        mock_win32gui.IsWindowVisible.reset_mock()
        mock_win32gui.IsWindowVisible.return_value = True
        mock_win32process.GetWindowThreadProcessId.reset_mock()
        mock_win32process.GetWindowThreadProcessId.return_value = (1, 42)

        result = self.mgr.get_window_by_pid(42)
        self.assertEqual(result, expected_info)
        mock_get_info.assert_called_once_with(700)

    def test_returns_none_when_pid_not_found(self):
        def fake_enum_windows(callback, result_list):
            callback(800, result_list)

        mock_win32gui.EnumWindows.reset_mock()
        mock_win32gui.EnumWindows.side_effect = fake_enum_windows
        mock_win32gui.IsWindowVisible.reset_mock()
        mock_win32gui.IsWindowVisible.return_value = True
        mock_win32process.GetWindowThreadProcessId.reset_mock()
        mock_win32process.GetWindowThreadProcessId.return_value = (1, 999)

        result = self.mgr.get_window_by_pid(42)
        self.assertIsNone(result)

    def test_returns_none_when_enum_windows_raises(self):
        mock_win32gui.EnumWindows.reset_mock()
        mock_win32gui.EnumWindows.side_effect = Exception("fail")
        result = self.mgr.get_window_by_pid(42)
        self.assertIsNone(result)

    def test_invisible_windows_are_skipped(self):
        def fake_enum_windows(callback, result_list):
            callback(900, result_list)

        mock_win32gui.EnumWindows.reset_mock()
        mock_win32gui.EnumWindows.side_effect = fake_enum_windows
        mock_win32gui.IsWindowVisible.reset_mock()
        mock_win32gui.IsWindowVisible.return_value = False

        result = self.mgr.get_window_by_pid(42)
        self.assertIsNone(result)

    def test_get_window_thread_process_id_exception_is_swallowed(self):
        """If GetWindowThreadProcessId raises, the callback continues."""
        collected = []

        def fake_enum_windows(callback, result_list):
            callback(950, result_list)
            collected.extend(result_list)

        mock_win32gui.EnumWindows.reset_mock()
        mock_win32gui.EnumWindows.side_effect = fake_enum_windows
        mock_win32gui.IsWindowVisible.reset_mock()
        mock_win32gui.IsWindowVisible.return_value = True
        mock_win32process.GetWindowThreadProcessId.reset_mock()
        mock_win32process.GetWindowThreadProcessId.side_effect = Exception("fail")

        result = self.mgr.get_window_by_pid(42)
        self.assertIsNone(result)
        self.assertEqual(collected, [])


class TestWindowManagerGetWindowInfo(unittest.TestCase):
    """Tests for WindowManager._get_window_info."""

    def setUp(self):
        self.mgr = WindowManager()

    def test_builds_window_info_correctly(self):
        mock_win32gui.GetWindowText.reset_mock()
        mock_win32gui.GetWindowRect.reset_mock()
        mock_win32process.GetWindowThreadProcessId.reset_mock()
        mock_win32process.GetWindowThreadProcessId.side_effect = None

        mock_win32gui.GetWindowText.return_value = "My Window"
        mock_win32gui.GetWindowRect.return_value = (10, 20, 810, 620)
        mock_win32process.GetWindowThreadProcessId.return_value = (1, 1234)

        info = self.mgr._get_window_info(5555)

        self.assertEqual(info.hwnd, 5555)
        self.assertEqual(info.title, "My Window")
        self.assertEqual(info.left, 10)
        self.assertEqual(info.top, 20)
        self.assertEqual(info.width, 800)   # 810 - 10
        self.assertEqual(info.height, 600)  # 620 - 20
        self.assertEqual(info.process_id, 1234)

    def test_zero_size_window(self):
        mock_win32gui.GetWindowText.reset_mock()
        mock_win32gui.GetWindowRect.reset_mock()
        mock_win32process.GetWindowThreadProcessId.reset_mock()
        mock_win32process.GetWindowThreadProcessId.side_effect = None

        mock_win32gui.GetWindowText.return_value = ""
        mock_win32gui.GetWindowRect.return_value = (0, 0, 0, 0)
        mock_win32process.GetWindowThreadProcessId.return_value = (0, 0)

        info = self.mgr._get_window_info(0)
        self.assertEqual(info.width, 0)
        self.assertEqual(info.height, 0)

    def test_uses_correct_hwnd(self):
        mock_win32gui.GetWindowText.reset_mock()
        mock_win32gui.GetWindowRect.reset_mock()
        mock_win32process.GetWindowThreadProcessId.reset_mock()
        mock_win32process.GetWindowThreadProcessId.side_effect = None

        mock_win32gui.GetWindowText.return_value = "X"
        mock_win32gui.GetWindowRect.return_value = (0, 0, 1, 1)
        mock_win32process.GetWindowThreadProcessId.return_value = (0, 1)

        self.mgr._get_window_info(9999)
        mock_win32gui.GetWindowText.assert_called_with(9999)
        mock_win32gui.GetWindowRect.assert_called_with(9999)
        mock_win32process.GetWindowThreadProcessId.assert_called_with(9999)


class TestWindowManagerActivateWindow(unittest.TestCase):
    """Tests for WindowManager.activate_window."""

    def setUp(self):
        self.mgr = WindowManager()

    def test_returns_true_on_success(self):
        mock_win32gui.ShowWindow.reset_mock()
        mock_win32gui.ShowWindow.side_effect = None
        mock_win32gui.SetForegroundWindow.reset_mock()
        mock_win32gui.SetForegroundWindow.side_effect = None
        mock_win32gui.ShowWindow.return_value = True
        mock_win32gui.SetForegroundWindow.return_value = None

        result = self.mgr.activate_window(1234)
        self.assertTrue(result)
        mock_win32gui.ShowWindow.assert_called_once_with(1234, mock_win32con.SW_RESTORE)
        mock_win32gui.SetForegroundWindow.assert_called_once_with(1234)

    def test_returns_false_on_show_window_exception(self):
        mock_win32gui.ShowWindow.reset_mock()
        mock_win32gui.ShowWindow.side_effect = Exception("show failed")
        result = self.mgr.activate_window(1234)
        self.assertFalse(result)

    def test_returns_false_on_set_foreground_exception(self):
        mock_win32gui.ShowWindow.reset_mock()
        mock_win32gui.SetForegroundWindow.reset_mock()
        mock_win32gui.ShowWindow.return_value = True
        mock_win32gui.SetForegroundWindow.side_effect = Exception("fg failed")
        result = self.mgr.activate_window(1234)
        self.assertFalse(result)

    def test_returns_false_on_invalid_hwnd(self):
        mock_win32gui.ShowWindow.reset_mock()
        mock_win32gui.ShowWindow.side_effect = Exception("invalid hwnd")
        result = self.mgr.activate_window(0)
        self.assertFalse(result)


class TestWindowManagerWaitForWindow(unittest.TestCase):
    """Tests for WindowManager.wait_for_window.

    Note on time.time() call sequencing:
        start_time = time.time()          # call 1
        while time.time() - start_time < timeout:  # call 2 (loop condition)
            ... body ...
            time.sleep(0.5)
            # back to while -> call 3, etc.
    """

    def setUp(self):
        self.mgr = WindowManager()

    @patch.object(WindowManager, "get_window_by_pid")
    def test_returns_window_found_by_pid_immediately(self, mock_by_pid):
        """Window found on first iteration -- no sleep needed."""
        mock_proc = MagicMock()
        mock_proc.poll.return_value = None  # process still running
        mock_proc.pid = 42

        expected_info = WindowInfo(
            hwnd=100, title="App", left=0, top=0, width=100, height=100, process_id=42
        )
        mock_by_pid.return_value = expected_info

        with patch("action.window_manager.time") as mock_time:
            # time.time() call 1: start_time = 0.0
            # time.time() call 2: while check -> 0.0 (< timeout=10, enter loop)
            mock_time.time.side_effect = [0.0, 0.0]
            result = self.mgr.wait_for_window(mock_proc, timeout=10)

        self.assertEqual(result, expected_info)
        mock_by_pid.assert_called_once_with(42)

    @patch.object(WindowManager, "get_window_by_pid")
    @patch.object(WindowManager, "get_window_by_title")
    def test_returns_window_found_by_title(self, mock_by_title, mock_by_pid):
        """PID lookup fails, but title lookup succeeds."""
        mock_proc = MagicMock()
        mock_proc.poll.return_value = None
        mock_proc.pid = 42

        mock_by_pid.return_value = None
        expected_info = WindowInfo(
            hwnd=200, title="Game", left=0, top=0, width=100, height=100, process_id=42
        )
        mock_by_title.return_value = expected_info

        with patch("action.window_manager.time") as mock_time:
            # time.time() call 1: start_time = 0.0
            # time.time() call 2: while check -> 0.0 (enter loop)
            mock_time.time.side_effect = [0.0, 0.0]
            result = self.mgr.wait_for_window(mock_proc, timeout=10, title="Game")

        self.assertEqual(result, expected_info)
        mock_by_title.assert_called_once_with("Game")

    @patch.object(WindowManager, "get_window_by_pid")
    def test_returns_none_on_timeout(self, mock_by_pid):
        """Simulates timeout: time advances past the deadline."""
        mock_proc = MagicMock()
        mock_proc.poll.return_value = None
        mock_proc.pid = 42
        mock_by_pid.return_value = None

        with patch("action.window_manager.time") as mock_time:
            # time.time() call 1: start_time = 0.0
            # time.time() call 2: while check -> 1.0 (< 5, enter loop)
            # time.time() call 3: while check -> 99.0 (>= 5, exit loop)
            mock_time.time.side_effect = [0.0, 1.0, 99.0]
            mock_time.sleep.return_value = None
            result = self.mgr.wait_for_window(mock_proc, timeout=5)

        self.assertIsNone(result)
        mock_time.sleep.assert_called_once_with(0.5)

    @patch.object(WindowManager, "get_window_by_pid")
    def test_retries_until_found(self, mock_by_pid):
        """First call returns None, second returns a window."""
        mock_proc = MagicMock()
        mock_proc.poll.return_value = None
        mock_proc.pid = 42

        expected_info = WindowInfo(
            hwnd=300, title="App", left=0, top=0, width=100, height=100, process_id=42
        )
        mock_by_pid.side_effect = [None, expected_info]

        with patch("action.window_manager.time") as mock_time:
            # time.time() call 1: start_time = 0.0
            # time.time() call 2: while check -> 0.0 (< 10, enter loop), get None, sleep
            # time.time() call 3: while check -> 0.5 (< 10, enter loop), get info, return
            mock_time.time.side_effect = [0.0, 0.0, 0.5]
            mock_time.sleep.return_value = None
            result = self.mgr.wait_for_window(mock_proc, timeout=10)

        self.assertEqual(result, expected_info)
        self.assertEqual(mock_by_pid.call_count, 2)
        mock_time.sleep.assert_called_once_with(0.5)

    @patch.object(WindowManager, "get_window_by_pid")
    def test_no_title_search_when_title_is_none(self, mock_by_pid):
        """When title is None (default), get_window_by_title should never be called."""
        mock_proc = MagicMock()
        mock_proc.poll.return_value = None
        mock_proc.pid = 42

        mock_by_pid.return_value = None

        with patch.object(self.mgr, "get_window_by_title") as mock_by_title, \
             patch("action.window_manager.time") as mock_time:
            # call 1: start_time = 0.0
            # call 2: while check -> 1.0 (< 5, enter loop)
            # call 3: while check -> 100.0 (>= 5, exit loop)
            mock_time.time.side_effect = [0.0, 1.0, 100.0]
            mock_time.sleep.return_value = None
            self.mgr.wait_for_window(mock_proc, timeout=5)

        mock_by_title.assert_not_called()

    @patch.object(WindowManager, "get_window_by_pid")
    def test_exception_in_try_block_is_caught(self, mock_by_pid):
        """If an exception occurs inside the try block, it is caught and loop continues."""
        mock_proc = MagicMock()
        mock_proc.poll.return_value = None
        mock_proc.pid = 42

        # First call raises, second succeeds
        mock_by_pid.side_effect = [Exception("boom"), WindowInfo(
            hwnd=400, title="A", left=0, top=0, width=10, height=10, process_id=42
        )]

        with patch("action.window_manager.time") as mock_time:
            # call 1: start_time = 0.0
            # call 2: while -> 0.0 (enter), exception caught, sleep
            # call 3: while -> 0.5 (enter), returns info
            mock_time.time.side_effect = [0.0, 0.0, 0.5]
            mock_time.sleep.return_value = None
            result = self.mgr.wait_for_window(mock_proc, timeout=10)

        self.assertIsNotNone(result)
        self.assertEqual(result.hwnd, 400)


class TestWindowManagerIsWindowValid(unittest.TestCase):
    """Tests for WindowManager.is_window_valid."""

    def setUp(self):
        self.mgr = WindowManager()

    def test_returns_true_when_valid_and_visible(self):
        mock_win32gui.IsWindow.reset_mock()
        mock_win32gui.IsWindow.side_effect = None
        mock_win32gui.IsWindowVisible.reset_mock()
        mock_win32gui.IsWindowVisible.side_effect = None
        mock_win32gui.IsWindow.return_value = True
        mock_win32gui.IsWindowVisible.return_value = True

        result = self.mgr.is_window_valid(1234)
        self.assertTrue(result)
        mock_win32gui.IsWindow.assert_called_once_with(1234)
        mock_win32gui.IsWindowVisible.assert_called_once_with(1234)

    def test_returns_false_when_not_a_window(self):
        mock_win32gui.IsWindow.reset_mock()
        mock_win32gui.IsWindow.return_value = False
        result = self.mgr.is_window_valid(0)
        self.assertFalse(result)

    def test_returns_false_when_not_visible(self):
        mock_win32gui.IsWindow.reset_mock()
        mock_win32gui.IsWindowVisible.reset_mock()
        mock_win32gui.IsWindow.return_value = True
        mock_win32gui.IsWindowVisible.return_value = False
        result = self.mgr.is_window_valid(1234)
        self.assertFalse(result)

    def test_returns_false_on_exception(self):
        mock_win32gui.IsWindow.reset_mock()
        mock_win32gui.IsWindow.side_effect = Exception("error")
        result = self.mgr.is_window_valid(1234)
        self.assertFalse(result)

    def test_returns_false_on_is_window_visible_exception(self):
        mock_win32gui.IsWindow.reset_mock()
        mock_win32gui.IsWindowVisible.reset_mock()
        mock_win32gui.IsWindow.return_value = True
        mock_win32gui.IsWindowVisible.side_effect = Exception("error")
        result = self.mgr.is_window_valid(1234)
        self.assertFalse(result)


if __name__ == "__main__":
    unittest.main()
