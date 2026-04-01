"""共享 pytest fixture。"""
import pytest
from unittest.mock import MagicMock, patch
import tempfile
import os

from src.agents.state_memory import StateMemory
from src.utils.config import Config


@pytest.fixture
def mock_glm_client():
    """Mock GLMClient，避免真实网络调用。"""
    client = MagicMock()
    client.chat.return_value = '{"action": "click", "target": "btn"}'
    client.chat_with_image.return_value = '{"action": "click", "target": "btn"}'
    client.describe_scene.return_value = "游戏画面描述"
    client.close.return_value = None
    return client


@pytest.fixture
def real_state_memory():
    """真实 StateMemory 实例。"""
    mem = StateMemory(max_history=10)
    mem.set_test_case("测试用例")
    return mem


@pytest.fixture
def sample_config(tmp_path):
    """真实 Config 实例（测试专用，无需 .env）。"""
    return Config(
        glm_api_key="test_api_key_12345",
        glm_model="glm-4v",
        game_exe_path=str(tmp_path / "game.exe"),
        game_window_title="测试游戏",
        game_startup_delay=0,
        test_case="点击开始按钮",
        max_steps=10,
        step_timeout=5,
        log_level="DEBUG",
        screenshot_save_path=str(tmp_path / "screenshots"),
    )


@pytest.fixture
def mock_window_info():
    """Mock WindowInfo 数据。"""
    from dataclasses import dataclass
    from typing import Tuple

    @dataclass
    class FakeWindowInfo:
        hwnd: int
        title: str
        left: int
        top: int
        width: int
        height: int
        process_id: int

        @property
        def center(self) -> Tuple[int, int]:
            return (self.left + self.width // 2, self.top + self.height // 2)

        @property
        def rect(self) -> Tuple[int, int, int, int]:
            return (self.left, self.top, self.left + self.width, self.top + self.height)

    return FakeWindowInfo(
        hwnd=12345, title="测试窗口", left=100, top=100,
        width=800, height=600, process_id=9999
    )
