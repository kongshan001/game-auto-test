"""
Unit tests for game.game_launcher.GameLauncher

Mocks all external dependencies: subprocess.Popen, pathlib.Path,
time.sleep, os.name.
"""
import os
import subprocess
import sys
import unittest
from pathlib import Path
from unittest.mock import MagicMock, Mock, patch

# ---------------------------------------------------------------------------
# Adjust sys.path so that ``from game.game_launcher import GameLauncher`` works
# regardless of where the test runner is invoked.
# ---------------------------------------------------------------------------
_PROJECT_ROOT = os.path.abspath(
    os.path.join(os.path.dirname(__file__), os.pardir, os.pardir, "src")
)
if _PROJECT_ROOT not in sys.path:
    sys.path.insert(0, _PROJECT_ROOT)

from game.game_launcher import GameLauncher  # noqa: E402


def _make_mock_exe_path(exists=True, path_str="/games/game.exe"):
    """Create a MagicMock that behaves like a pathlib.Path for exe_path."""
    mock_path = MagicMock()
    mock_path.exists.return_value = exists
    mock_path.__str__.return_value = path_str
    mock_path.parent = MagicMock()
    mock_path.parent.__str__.return_value = os.path.dirname(path_str)
    return mock_path


def _make_mock_process(pid=1234, poll_return=None, returncode=None):
    """Create a MagicMock that behaves like a subprocess.Popen object."""
    mock_proc = MagicMock()
    mock_proc.pid = pid
    mock_proc.poll.return_value = poll_return
    mock_proc.returncode = returncode
    return mock_proc


# ===================================================================
# __init__
# ===================================================================
class TestGameLauncherInit(unittest.TestCase):
    """Tests for GameLauncher.__init__"""

    def test_default_parameters(self):
        """Default init stores exe_path, None window_title, and startup_delay=5"""
        launcher = GameLauncher("/games/game.exe")
        self.assertEqual(str(launcher.exe_path), os.path.normpath("/games/game.exe"))
        self.assertIsNone(launcher.window_title)
        self.assertEqual(launcher.startup_delay, 5)
        self.assertIsNone(launcher.process)

    def test_custom_parameters(self):
        """Custom init stores all provided values"""
        launcher = GameLauncher(
            exe_path="/games/my_game.exe",
            window_title="My Game",
            startup_delay=10,
        )
        self.assertEqual(
            str(launcher.exe_path), os.path.normpath("/games/my_game.exe")
        )
        self.assertEqual(launcher.window_title, "My Game")
        self.assertEqual(launcher.startup_delay, 10)
        self.assertIsNone(launcher.process)

    def test_exe_path_converted_to_path(self):
        """exe_path string is converted to a pathlib.Path object"""
        launcher = GameLauncher("/games/game.exe")
        self.assertIsInstance(launcher.exe_path, Path)

    def test_zero_startup_delay(self):
        """startup_delay can be set to 0"""
        launcher = GameLauncher("/games/game.exe", startup_delay=0)
        self.assertEqual(launcher.startup_delay, 0)


# ===================================================================
# launch
# ===================================================================
class TestGameLauncherLaunch(unittest.TestCase):
    """Tests for GameLauncher.launch"""

    @patch("game.game_launcher.time.sleep")
    @patch("game.game_launcher.subprocess.Popen")
    def test_launch_basic(self, mock_popen, mock_sleep):
        """Basic launch with no extra args calls Popen with the exe path"""
        mock_process = _make_mock_process()
        mock_popen.return_value = mock_process

        launcher = GameLauncher("/games/game.exe", startup_delay=1)
        launcher.exe_path = _make_mock_exe_path()

        result = launcher.launch()

        mock_popen.assert_called_once()
        cmd = mock_popen.call_args[0][0]
        self.assertEqual(cmd[0], "/games/game.exe")
        self.assertEqual(result, mock_process)
        self.assertEqual(launcher.process, mock_process)
        mock_sleep.assert_called_once_with(1)

    @patch("game.game_launcher.time.sleep")
    @patch("game.game_launcher.subprocess.Popen")
    def test_launch_with_args(self, mock_popen, mock_sleep):
        """Extra args are appended to the command list"""
        mock_process = _make_mock_process()
        mock_popen.return_value = mock_process

        launcher = GameLauncher("/games/game.exe", startup_delay=0)
        launcher.exe_path = _make_mock_exe_path()

        launcher.launch(args=["--windowed", "--resolution", "1920x1080"])

        cmd = mock_popen.call_args[0][0]
        self.assertIn("--windowed", cmd)
        self.assertIn("--resolution", cmd)
        self.assertIn("1920x1080", cmd)
        mock_sleep.assert_not_called()

    @patch("game.game_launcher.time.sleep")
    @patch("game.game_launcher.subprocess.Popen")
    def test_launch_with_cwd(self, mock_popen, mock_sleep):
        """Custom cwd overrides the default parent directory"""
        mock_process = _make_mock_process()
        mock_popen.return_value = mock_process

        launcher = GameLauncher("/games/game.exe", startup_delay=0)
        launcher.exe_path = _make_mock_exe_path()

        launcher.launch(cwd="/custom/work/dir")

        call_kwargs = mock_popen.call_args[1]
        self.assertEqual(call_kwargs["cwd"], "/custom/work/dir")

    @patch("game.game_launcher.subprocess.Popen")
    def test_launch_file_not_found(self, mock_popen):
        """launch raises FileNotFoundError when exe_path does not exist"""
        launcher = GameLauncher("/nonexistent/game.exe")
        launcher.exe_path = _make_mock_exe_path(exists=False)

        with self.assertRaises(FileNotFoundError) as ctx:
            launcher.launch()

        self.assertIn(str(launcher.exe_path), str(ctx.exception))
        mock_popen.assert_not_called()

    @patch("game.game_launcher.time.sleep")
    @patch("game.game_launcher.subprocess.Popen")
    def test_launch_failure_raises(self, mock_popen, mock_sleep):
        """If Popen itself raises, the exception propagates"""
        mock_popen.side_effect = OSError("Permission denied")

        launcher = GameLauncher("/games/game.exe", startup_delay=0)
        launcher.exe_path = _make_mock_exe_path()

        with self.assertRaises(OSError):
            launcher.launch()

    @patch("game.game_launcher.time.sleep")
    @patch("game.game_launcher.subprocess.Popen")
    def test_launch_creation_flags_nt(self, mock_popen, mock_sleep):
        """On Windows (os.name == 'nt'), CREATE_NEW_CONSOLE flag is used"""
        mock_process = _make_mock_process()
        mock_popen.return_value = mock_process

        launcher = GameLauncher("/games/game.exe", startup_delay=0)
        launcher.exe_path = _make_mock_exe_path()

        with patch("game.game_launcher.os") as mock_os:
            mock_os.name = "nt"
            mock_os.path = os.path
            launcher.launch()

        call_kwargs = mock_popen.call_args[1]
        self.assertIn("creationflags", call_kwargs)

    @patch("game.game_launcher.time.sleep")
    @patch("game.game_launcher.subprocess.Popen")
    def test_launch_creation_flags_posix(self, mock_popen, mock_sleep):
        """On non-Windows, creationflags is 0"""
        mock_process = _make_mock_process()
        mock_popen.return_value = mock_process

        launcher = GameLauncher("/games/game.exe", startup_delay=0)
        launcher.exe_path = _make_mock_exe_path()

        with patch("game.game_launcher.os") as mock_os:
            mock_os.name = "posix"
            mock_os.path = os.path
            launcher.launch()

        call_kwargs = mock_popen.call_args[1]
        self.assertEqual(call_kwargs["creationflags"], 0)

    @patch("game.game_launcher.time.sleep")
    @patch("game.game_launcher.subprocess.Popen")
    def test_launch_uses_parent_dir_as_default_cwd(self, mock_popen, mock_sleep):
        """When no cwd is given, exe_path.parent is used as cwd"""
        mock_process = _make_mock_process()
        mock_popen.return_value = mock_process

        mock_path = _make_mock_exe_path()
        launcher = GameLauncher("/games/game.exe", startup_delay=0)
        launcher.exe_path = mock_path

        launcher.launch()

        call_kwargs = mock_popen.call_args[1]
        self.assertEqual(call_kwargs["cwd"], str(mock_path.parent))

    @patch("game.game_launcher.time.sleep")
    @patch("game.game_launcher.subprocess.Popen")
    def test_launch_stdout_stderr_piped(self, mock_popen, mock_sleep):
        """launch() passes stdout=PIPE and stderr=PIPE to Popen"""
        mock_process = _make_mock_process()
        mock_popen.return_value = mock_process

        launcher = GameLauncher("/games/game.exe", startup_delay=0)
        launcher.exe_path = _make_mock_exe_path()

        launcher.launch()

        call_kwargs = mock_popen.call_args[1]
        self.assertEqual(call_kwargs["stdout"], subprocess.PIPE)
        self.assertEqual(call_kwargs["stderr"], subprocess.PIPE)

    @patch("game.game_launcher.time.sleep")
    @patch("game.game_launcher.subprocess.Popen")
    def test_launch_returns_popen_object(self, mock_popen, mock_sleep):
        """launch() returns the same Popen object stored in self.process"""
        mock_process = _make_mock_process()
        mock_popen.return_value = mock_process

        launcher = GameLauncher("/games/game.exe", startup_delay=0)
        launcher.exe_path = _make_mock_exe_path()

        result = launcher.launch()

        self.assertIs(result, launcher.process)
        self.assertIs(result, mock_process)


# ===================================================================
# is_running
# ===================================================================
class TestGameLauncherIsRunning(unittest.TestCase):
    """Tests for GameLauncher.is_running"""

    def test_is_running_with_alive_process(self):
        """poll() returning None means the process is alive"""
        launcher = GameLauncher("/games/game.exe")
        launcher.process = _make_mock_process(poll_return=None)

        self.assertTrue(launcher.is_running())

    def test_is_running_with_dead_process(self):
        """poll() returning an exit code means the process is dead"""
        launcher = GameLauncher("/games/game.exe")
        launcher.process = _make_mock_process(poll_return=0)

        self.assertFalse(launcher.is_running())

    def test_is_running_no_process(self):
        """No process (None) means not running"""
        launcher = GameLauncher("/games/game.exe")
        launcher.process = None

        self.assertFalse(launcher.is_running())

    def test_is_running_process_exited_with_error(self):
        """poll() returning a non-zero exit code means not running"""
        launcher = GameLauncher("/games/game.exe")
        launcher.process = _make_mock_process(poll_return=1)

        self.assertFalse(launcher.is_running())


# ===================================================================
# close
# ===================================================================
class TestGameLauncherClose(unittest.TestCase):
    """Tests for GameLauncher.close"""

    def test_close_no_process(self):
        """Closing when no process exists returns True immediately"""
        launcher = GameLauncher("/games/game.exe")
        launcher.process = None

        self.assertTrue(launcher.close())

    def test_close_normal(self):
        """Normal close calls terminate() then wait()"""
        launcher = GameLauncher("/games/game.exe")
        mock_process = _make_mock_process()
        launcher.process = mock_process

        result = launcher.close()

        mock_process.terminate.assert_called_once()
        mock_process.wait.assert_called_once_with(timeout=5)
        self.assertTrue(result)

    def test_close_force(self):
        """Force close calls kill() directly"""
        launcher = GameLauncher("/games/game.exe")
        mock_process = _make_mock_process()
        launcher.process = mock_process

        result = launcher.close(force=True)

        mock_process.kill.assert_called_once()
        mock_process.terminate.assert_not_called()
        self.assertTrue(result)

    def test_close_timeout_then_kill(self):
        """If terminate + wait times out, kill is called as fallback"""
        launcher = GameLauncher("/games/game.exe")
        mock_process = _make_mock_process()
        mock_process.wait.side_effect = subprocess.TimeoutExpired(
            cmd="game", timeout=5
        )
        launcher.process = mock_process

        result = launcher.close()

        mock_process.terminate.assert_called_once()
        mock_process.wait.assert_called_once_with(timeout=5)
        mock_process.kill.assert_called_once()
        self.assertTrue(result)

    def test_close_failure(self):
        """Exception during close returns False"""
        launcher = GameLauncher("/games/game.exe")
        mock_process = _make_mock_process()
        mock_process.terminate.side_effect = OSError("kill failed")
        launcher.process = mock_process

        self.assertFalse(launcher.close())

    def test_close_force_failure(self):
        """Exception during force close returns False"""
        launcher = GameLauncher("/games/game.exe")
        mock_process = _make_mock_process()
        mock_process.kill.side_effect = OSError("force kill failed")
        launcher.process = mock_process

        self.assertFalse(launcher.close(force=True))


# ===================================================================
# restart
# ===================================================================
class TestGameLauncherRestart(unittest.TestCase):
    """Tests for GameLauncher.restart"""

    @patch("game.game_launcher.time.sleep")
    @patch("game.game_launcher.subprocess.Popen")
    def test_restart_success(self, mock_popen, mock_sleep):
        """restart closes the old process and launches a new one"""
        new_process = _make_mock_process(pid=5678)
        mock_popen.return_value = new_process

        launcher = GameLauncher("/games/game.exe", startup_delay=0)
        launcher.exe_path = _make_mock_exe_path()
        old_process = _make_mock_process(pid=1111, poll_return=None)
        launcher.process = old_process

        result = launcher.restart()

        # Old process should have been force-closed
        old_process.kill.assert_called_once()
        # A new process should have been launched
        mock_popen.assert_called_once()
        self.assertEqual(result, new_process)
        # time.sleep called once for the 2s restart delay
        mock_sleep.assert_called_once_with(2)

    @patch("game.game_launcher.time.sleep")
    @patch("game.game_launcher.subprocess.Popen")
    def test_restart_failure_launch_raises(self, mock_popen, mock_sleep):
        """If launch fails during restart, exception propagates"""
        mock_popen.side_effect = OSError("launch error")

        launcher = GameLauncher("/games/game.exe", startup_delay=0)
        launcher.exe_path = _make_mock_exe_path()
        launcher.process = _make_mock_process()

        with self.assertRaises(OSError):
            launcher.restart()


# ===================================================================
# get_pid
# ===================================================================
class TestGameLauncherGetPid(unittest.TestCase):
    """Tests for GameLauncher.get_pid"""

    def test_get_pid_with_process(self):
        """Returns the pid when a process exists"""
        launcher = GameLauncher("/games/game.exe")
        launcher.process = _make_mock_process(pid=42)

        self.assertEqual(launcher.get_pid(), 42)

    def test_get_pid_without_process(self):
        """Returns None when no process exists"""
        launcher = GameLauncher("/games/game.exe")
        launcher.process = None

        self.assertIsNone(launcher.get_pid())


# ===================================================================
# get_process_info
# ===================================================================
class TestGameLauncherGetProcessInfo(unittest.TestCase):
    """Tests for GameLauncher.get_process_info"""

    def test_get_process_info_with_running_process(self):
        """Returns dict with pid, running=True, returncode for a live process"""
        launcher = GameLauncher("/games/game.exe")
        launcher.process = _make_mock_process(pid=99, poll_return=None, returncode=None)

        info = launcher.get_process_info()
        self.assertEqual(info["pid"], 99)
        self.assertTrue(info["running"])
        self.assertIsNone(info["returncode"])

    def test_get_process_info_with_dead_process(self):
        """Returns dict with pid, running=False, returncode for a dead process"""
        launcher = GameLauncher("/games/game.exe")
        launcher.process = _make_mock_process(pid=99, poll_return=0, returncode=0)

        info = launcher.get_process_info()
        self.assertEqual(info["pid"], 99)
        self.assertFalse(info["running"])
        self.assertEqual(info["returncode"], 0)

    def test_get_process_info_without_process(self):
        """Returns empty dict when no process exists"""
        launcher = GameLauncher("/games/game.exe")
        launcher.process = None

        info = launcher.get_process_info()
        self.assertEqual(info, {})


# ===================================================================
# Edge cases
# ===================================================================
class TestGameLauncherEdgeCases(unittest.TestCase):
    """Edge-case and integration-style tests"""

    @patch("game.game_launcher.time.sleep")
    @patch("game.game_launcher.subprocess.Popen")
    def test_full_launch_and_close_lifecycle(self, mock_popen, mock_sleep):
        """Simulate a complete launch -> is_running -> close lifecycle"""
        mock_process = _make_mock_process(pid=5555, poll_return=None)
        mock_popen.return_value = mock_process

        launcher = GameLauncher("/games/game.exe", startup_delay=0)
        launcher.exe_path = _make_mock_exe_path()
        launcher.launch()

        self.assertTrue(launcher.is_running())
        self.assertEqual(launcher.get_pid(), 5555)
        self.assertTrue(launcher.close())
        mock_process.terminate.assert_called_once()

    @patch("game.game_launcher.time.sleep")
    @patch("game.game_launcher.subprocess.Popen")
    def test_process_already_running_on_launch(self, mock_popen, mock_sleep):
        """Launching again replaces the old process reference"""
        new_process = _make_mock_process(pid=2222)
        mock_popen.return_value = new_process

        launcher = GameLauncher("/games/game.exe", startup_delay=0)
        launcher.exe_path = _make_mock_exe_path()
        old_process = _make_mock_process(pid=1111)
        launcher.process = old_process

        launcher.launch()

        self.assertEqual(launcher.process, new_process)
        self.assertEqual(launcher.get_pid(), 2222)

    @patch("game.game_launcher.time.sleep")
    @patch("game.game_launcher.subprocess.Popen")
    def test_close_after_process_already_terminated(self, mock_popen, mock_sleep):
        """Closing an already-terminated process still succeeds"""
        launcher = GameLauncher("/games/game.exe")
        launcher.process = _make_mock_process(poll_return=0)

        self.assertTrue(launcher.close())

    def test_windows_path_accepted(self):
        """Windows-style paths are handled correctly by Path conversion"""
        launcher = GameLauncher("C:\\Games\\MyGame\\game.exe")
        self.assertIsInstance(launcher.exe_path, Path)


if __name__ == "__main__":
    unittest.main()
