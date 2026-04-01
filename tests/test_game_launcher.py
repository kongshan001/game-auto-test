"""测试游戏启动器模块"""
import subprocess
import time
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from src.game.game_launcher import GameLauncher


class TestGameLauncherInit:
    """GameLauncher 初始化测试"""

    def test_init_stores_defaults(self):
        """测试初始化存储exe_path、window_title、startup_delay，process为None"""
        launcher = GameLauncher(exe_path="/tmp/game.exe")

        assert launcher.exe_path == Path("/tmp/game.exe")
        assert launcher.window_title is None
        assert launcher.startup_delay == 5
        assert launcher.process is None

    def test_init_with_all_params(self):
        """测试传入完整参数初始化"""
        launcher = GameLauncher(
            exe_path="/tmp/game.exe",
            window_title="MyGame",
            startup_delay=10,
        )

        assert launcher.exe_path == Path("/tmp/game.exe")
        assert launcher.window_title == "MyGame"
        assert launcher.startup_delay == 10
        assert launcher.process is None

    def test_init_with_path_object(self):
        """测试使用Path对象初始化exe_path"""
        exe = Path("/games/test_game.exe")
        launcher = GameLauncher(exe_path=exe)

        assert launcher.exe_path == exe
        assert isinstance(launcher.exe_path, Path)


class TestGameLauncherNoProcess:
    """GameLauncher 无进程时的行为测试"""

    def test_is_running_no_process(self):
        """测试无进程时is_running返回False"""
        launcher = GameLauncher(exe_path="/tmp/game.exe")
        assert launcher.is_running() is False

    def test_get_pid_no_process(self):
        """测试无进程时get_pid返回None"""
        launcher = GameLauncher(exe_path="/tmp/game.exe")
        assert launcher.get_pid() is None

    def test_get_process_info_no_process(self):
        """测试无进程时get_process_info返回空字典"""
        launcher = GameLauncher(exe_path="/tmp/game.exe")
        assert launcher.get_process_info() == {}


class TestGameLauncherLaunch:
    """GameLauncher launch 测试"""

    def test_launch_raises_when_exe_not_found(self, tmp_path):
        """测试exe不存在时launch抛出FileNotFoundError"""
        nonexistent = tmp_path / "nonexistent_game.exe"
        launcher = GameLauncher(exe_path=str(nonexistent))

        with pytest.raises(FileNotFoundError, match="游戏可执行文件不存在"):
            launcher.launch()

    @patch("src.game.game_launcher.time.sleep")
    @patch("src.game.game_launcher.subprocess.Popen")
    def test_launch_starts_process_with_correct_command(
        self, mock_popen_cls, mock_sleep, tmp_path
    ):
        """测试launch使用正确命令启动进程"""
        fake_exe = tmp_path / "game.exe"
        fake_exe.touch()

        mock_process = MagicMock()
        mock_popen_cls.return_value = mock_process

        launcher = GameLauncher(exe_path=str(fake_exe), startup_delay=3)
        result = launcher.launch()

        assert result is mock_process
        assert launcher.process is mock_process

        # 验证Popen被调用，命令包含exe路径
        popen_call = mock_popen_cls.call_args
        cmd_arg = popen_call.args[0]
        assert str(fake_exe) in cmd_arg

    @patch("src.game.game_launcher.time.sleep")
    @patch("src.game.game_launcher.subprocess.Popen")
    def test_launch_with_args_extends_command(
        self, mock_popen_cls, mock_sleep, tmp_path
    ):
        """测试带参数启动时命令正确扩展"""
        fake_exe = tmp_path / "game.exe"
        fake_exe.touch()

        mock_popen_cls.return_value = MagicMock()

        launcher = GameLauncher(exe_path=str(fake_exe), startup_delay=0)
        launcher.launch(args=["--windowed", "--resolution", "1920x1080"])

        cmd_arg = mock_popen_cls.call_args.args[0]
        assert "--windowed" in cmd_arg
        assert "--resolution" in cmd_arg
        assert "1920x1080" in cmd_arg

    @patch("src.game.game_launcher.time.sleep")
    @patch("src.game.game_launcher.subprocess.Popen")
    def test_launch_with_custom_cwd(
        self, mock_popen_cls, mock_sleep, tmp_path
    ):
        """测试自定义工作目录启动"""
        fake_exe = tmp_path / "game.exe"
        fake_exe.touch()
        custom_cwd = tmp_path / "workdir"
        custom_cwd.mkdir()

        mock_popen_cls.return_value = MagicMock()

        launcher = GameLauncher(exe_path=str(fake_exe), startup_delay=0)
        launcher.launch(cwd=str(custom_cwd))

        popen_kwargs = mock_popen_cls.call_args.kwargs
        assert popen_kwargs["cwd"] == str(custom_cwd)

    @patch("src.game.game_launcher.time.sleep")
    @patch("src.game.game_launcher.subprocess.Popen")
    def test_launch_waits_startup_delay(self, mock_popen_cls, mock_sleep, tmp_path):
        """测试launch等待startup_delay秒"""
        fake_exe = tmp_path / "game.exe"
        fake_exe.touch()

        mock_popen_cls.return_value = MagicMock()

        launcher = GameLauncher(exe_path=str(fake_exe), startup_delay=7)
        launcher.launch()

        # 验证time.sleep被调用了startup_delay秒
        mock_sleep.assert_called_with(7)


class TestGameLauncherRunning:
    """GameLauncher 进程运行状态测试"""

    def test_is_running_true_when_poll_returns_none(self):
        """测试poll返回None时is_running返回True"""
        launcher = GameLauncher(exe_path="/tmp/game.exe")
        mock_process = MagicMock()
        mock_process.poll.return_value = None
        launcher.process = mock_process

        assert launcher.is_running() is True

    def test_is_running_false_when_poll_returns_exit_code(self):
        """测试poll返回退出码时is_running返回False"""
        launcher = GameLauncher(exe_path="/tmp/game.exe")
        mock_process = MagicMock()
        mock_process.poll.return_value = 0
        launcher.process = mock_process

        assert launcher.is_running() is False

    def test_get_pid_returns_process_pid(self):
        """测试有进程时get_pid返回process.pid"""
        launcher = GameLauncher(exe_path="/tmp/game.exe")
        mock_process = MagicMock()
        mock_process.pid = 12345
        launcher.process = mock_process

        assert launcher.get_pid() == 12345

    def test_get_process_info_returns_correct_dict(self):
        """测试有进程时get_process_info返回正确的字典"""
        launcher = GameLauncher(exe_path="/tmp/game.exe")
        mock_process = MagicMock()
        mock_process.pid = 9999
        mock_process.poll.return_value = None
        mock_process.returncode = None
        launcher.process = mock_process

        info = launcher.get_process_info()
        assert info == {
            "pid": 9999,
            "running": True,
            "returncode": None,
        }


class TestGameLauncherClose:
    """GameLauncher close 测试"""

    def test_close_no_process_returns_true(self):
        """测试无进程时close返回True"""
        launcher = GameLauncher(exe_path="/tmp/game.exe")
        assert launcher.close() is True

    def test_close_normal_termination(self):
        """测试正常关闭调用terminate和wait"""
        launcher = GameLauncher(exe_path="/tmp/game.exe")
        mock_process = MagicMock()
        mock_process.wait.return_value = 0
        launcher.process = mock_process

        result = launcher.close()

        assert result is True
        mock_process.terminate.assert_called_once()
        mock_process.wait.assert_called_once_with(timeout=5)

    def test_close_force_kill(self):
        """测试强制关闭调用kill"""
        launcher = GameLauncher(exe_path="/tmp/game.exe")
        mock_process = MagicMock()
        launcher.process = mock_process

        result = launcher.close(force=True)

        assert result is True
        mock_process.kill.assert_called_once()

    def test_close_timeout_falls_back_to_kill(self):
        """测试terminate超时后回退到kill"""
        launcher = GameLauncher(exe_path="/tmp/game.exe")
        mock_process = MagicMock()
        mock_process.wait.side_effect = subprocess.TimeoutExpired(cmd="game", timeout=5)
        launcher.process = mock_process

        result = launcher.close()

        assert result is True
        mock_process.terminate.assert_called_once()
        mock_process.kill.assert_called_once()

    def test_close_exception_returns_false(self):
        """测试关闭过程异常时返回False"""
        launcher = GameLauncher(exe_path="/tmp/game.exe")
        mock_process = MagicMock()
        mock_process.terminate.side_effect = OSError("Access denied")
        launcher.process = mock_process

        result = launcher.close()

        assert result is False


class TestGameLauncherRestart:
    """GameLauncher restart 测试"""

    @patch("src.game.game_launcher.time.sleep")
    @patch("src.game.game_launcher.subprocess.Popen")
    def test_restart_calls_close_then_launch(
        self, mock_popen_cls, mock_sleep, tmp_path
    ):
        """测试restart先调用close再调用launch"""
        fake_exe = tmp_path / "game.exe"
        fake_exe.touch()

        mock_process = MagicMock()
        mock_popen_cls.return_value = mock_process

        launcher = GameLauncher(exe_path=str(fake_exe), startup_delay=0)
        launcher.process = mock_process

        result = launcher.restart()

        # 验证旧进程被关闭
        mock_process.kill.assert_called_once()
        # 验证新进程被启动
        assert result is mock_process
        assert mock_popen_cls.called
