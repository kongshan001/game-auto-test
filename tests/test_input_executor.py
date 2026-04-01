"""测试动作执行器模块"""
import time
from unittest.mock import MagicMock, patch, call

import pytest

import src.action.input_executor as _input_executor_module
from src.action.input_executor import ActionExecutor


# ---------------------------------------------------------------------------
# Fixtures: mock pydirectinput + time.sleep at the module namespace
# ---------------------------------------------------------------------------

@pytest.fixture()
def mock_pydirectinput():
    """将 input_executor 模块中的 pydirectinput 名称替换为 MagicMock，返回该 mock。

    同时将 HAS_PYDIRECTINPUT 设为 True 以便 _check_available 通过。
    """
    fake_pdi = MagicMock()
    with patch.object(_input_executor_module, "pydirectinput", fake_pdi):
        with patch.object(_input_executor_module, "HAS_PYDIRECTINPUT", True):
            yield fake_pdi


@pytest.fixture()
def mock_time_sleep():
    """mock time.sleep 以避免真实等待。"""
    with patch("src.action.input_executor.time.sleep") as mock_sleep:
        yield mock_sleep


@pytest.fixture()
def mock_window_info():
    """模拟窗口信息对象。"""
    info = MagicMock()
    info.left = 100
    info.top = 200
    info.width = 800
    info.height = 600
    return info


# ======================== 初始化测试 ========================

class TestActionExecutorInit:
    """ActionExecutor 初始化测试"""

    def test_init_defaults(self):
        """测试默认参数初始化"""
        executor = ActionExecutor()

        assert executor.window_info is None
        assert executor.click_delay == 0.5
        assert executor.type_delay == 0.1
        assert executor.keypress_delay == 0.3

    def test_init_with_window_info_and_custom_delays(self, mock_window_info):
        """测试带窗口信息和自定义延迟初始化"""
        executor = ActionExecutor(
            window_info=mock_window_info,
            click_delay=0.2,
            type_delay=0.05,
            keypress_delay=0.1,
        )

        assert executor.window_info is mock_window_info
        assert executor.click_delay == 0.2
        assert executor.type_delay == 0.05
        assert executor.keypress_delay == 0.1


# ======================== 坐标转换测试 (真实逻辑) ========================

class TestCoordinateTransform:
    """坐标转换测试 —— 使用真实逻辑，不做 mock"""

    def test_to_absolute_without_window_info(self):
        """测试无窗口信息时_to_absolute返回原始坐标"""
        executor = ActionExecutor()
        assert executor._to_absolute(50, 60) == (50, 60)

    def test_to_absolute_with_window_info(self, mock_window_info):
        """测试有窗口信息时_to_absolute加上偏移"""
        executor = ActionExecutor(window_info=mock_window_info)
        result = executor._to_absolute(50, 60)
        assert result == (50 + 100, 60 + 200)

    def test_to_relative_without_window_info(self):
        """测试无窗口信息时_to_relative返回原始坐标"""
        executor = ActionExecutor()
        assert executor._to_relative(150, 260) == (150, 260)

    def test_to_relative_with_window_info(self, mock_window_info):
        """测试有窗口信息时_to_relative减去偏移"""
        executor = ActionExecutor(window_info=mock_window_info)
        result = executor._to_relative(150, 260)
        assert result == (150 - 100, 260 - 200)


# ======================== 可用性检查测试 ========================

class TestCheckAvailable:
    """_check_available 测试"""

    def test_raises_runtime_error_when_not_available(self):
        """测试pydirectinput不可用时_check_available抛出RuntimeError"""
        with patch("src.action.input_executor.HAS_PYDIRECTINPUT", False):
            executor = ActionExecutor()
            with pytest.raises(RuntimeError, match="pydirectinput不可用"):
                executor._check_available()


# ======================== click 测试 ========================

class TestClick:
    """click 测试"""

    def test_click_with_coordinate_target(
        self, mock_pydirectinput, mock_time_sleep
    ):
        """测试坐标目标点击调用moveTo和click"""
        executor = ActionExecutor()
        result = executor.click(target=(300, 400))

        assert result is True
        mock_pydirectinput.moveTo.assert_called_with(300, 400)
        mock_pydirectinput.click.assert_called_once()

    def test_click_with_string_target_and_locator(
        self, mock_pydirectinput, mock_time_sleep
    ):
        """测试字符串目标使用locator定位后点击"""
        executor = ActionExecutor()
        mock_locator = MagicMock()
        mock_locator.get_element_center.return_value = (250, 350)

        result = executor.click(
            target="登录按钮", image=MagicMock(), locator=mock_locator
        )

        assert result is True
        mock_locator.get_element_center.assert_called_once()
        mock_pydirectinput.moveTo.assert_called_with(250, 350)

    def test_click_with_string_target_no_locator_returns_false(self, mock_pydirectinput):
        """测试字符串目标没有locator时返回False（ValueError被内部捕获）"""
        executor = ActionExecutor()
        result = executor.click(target="按钮")
        assert result is False

    def test_click_locator_returns_none_returns_false(self, mock_pydirectinput):
        """测试locator返回None时click返回False"""
        executor = ActionExecutor()
        mock_locator = MagicMock()
        mock_locator.get_element_center.return_value = None

        result = executor.click(
            target="不存在的按钮", image=MagicMock(), locator=mock_locator
        )
        assert result is False

    def test_click_right_button(self, mock_pydirectinput, mock_time_sleep):
        """测试右键点击调用rightClick"""
        executor = ActionExecutor()
        result = executor.click(target=(100, 200), button="right")

        assert result is True
        mock_pydirectinput.rightClick.assert_called_once()

    def test_click_middle_button(self, mock_pydirectinput, mock_time_sleep):
        """测试中键点击调用middleClick"""
        executor = ActionExecutor()
        result = executor.click(target=(100, 200), button="middle")

        assert result is True
        mock_pydirectinput.middleClick.assert_called_once()


# ======================== double_click 测试 ========================

class TestDoubleClick:
    """double_click 测试"""

    def test_double_click_calls_pydirectinput(
        self, mock_pydirectinput, mock_time_sleep
    ):
        """测试双击调用pydirectinput.doubleClick"""
        executor = ActionExecutor()
        result = executor.double_click(target=(100, 200))

        assert result is True
        mock_pydirectinput.doubleClick.assert_called_once()


# ======================== right_click 测试 ========================

class TestRightClick:
    """right_click 测试"""

    def test_right_click_delegates_to_click_with_right(
        self, mock_pydirectinput, mock_time_sleep
    ):
        """测试right_click委托给click并传入button='right'"""
        executor = ActionExecutor()
        result = executor.right_click(target=(100, 200))

        assert result is True
        mock_pydirectinput.rightClick.assert_called_once()


# ======================== type_text 测试 ========================

class TestTypeText:
    """type_text 测试"""

    def test_type_text_without_target(
        self, mock_pydirectinput, mock_time_sleep
    ):
        """测试无目标输入文本逐字符调用write"""
        executor = ActionExecutor(type_delay=0.01)
        result = executor.type_text("abc")

        assert result is True
        assert mock_pydirectinput.write.call_count == 3
        calls = [call("a"), call("b"), call("c")]
        mock_pydirectinput.write.assert_has_calls(calls)

    def test_type_text_with_target_clicks_first(
        self, mock_pydirectinput, mock_time_sleep
    ):
        """测试有目标时先点击目标再输入"""
        executor = ActionExecutor()
        result = executor.type_text("hi", target=(400, 500))

        assert result is True
        # 先点击了目标
        mock_pydirectinput.moveTo.assert_called_with(400, 500)
        mock_pydirectinput.click.assert_called()
        # 再逐字符输入
        assert mock_pydirectinput.write.call_count == 2

    def test_type_text_with_clear_first(
        self, mock_pydirectinput, mock_time_sleep
    ):
        """测试clear_first=True时先全选再删除"""
        executor = ActionExecutor()
        result = executor.type_text(
            "new", target=(100, 200), clear_first=True
        )

        assert result is True
        mock_pydirectinput.hotkey.assert_called_with("ctrl", "a")
        mock_pydirectinput.press.assert_called_with("backspace")
        assert mock_pydirectinput.write.call_count == 3


# ======================== press_key 测试 ========================

class TestPressKey:
    """press_key 测试"""

    def test_press_key_calls_pydirectinput_press(
        self, mock_pydirectinput, mock_time_sleep
    ):
        """测试press_key调用pydirectinput.press"""
        executor = ActionExecutor()
        result = executor.press_key("enter")

        assert result is True
        mock_pydirectinput.press.assert_called_once_with("enter")


# ======================== press_keys 测试 ========================

class TestPressKeys:
    """press_keys 测试"""

    def test_press_keys_calls_hotkey(
        self, mock_pydirectinput, mock_time_sleep
    ):
        """测试press_keys调用pydirectinput.hotkey"""
        executor = ActionExecutor()
        result = executor.press_keys(["ctrl", "c"])

        assert result is True
        mock_pydirectinput.hotkey.assert_called_once_with("ctrl", "c")


# ======================== wait 测试 ========================

class TestWait:
    """wait 测试"""

    def test_wait_calls_time_sleep(self, mock_time_sleep):
        """测试wait调用time.sleep"""
        executor = ActionExecutor()
        result = executor.wait(2.5)

        assert result is True
        mock_time_sleep.assert_called_with(2.5)


# ======================== scroll 测试 ========================

class TestScroll:
    """scroll 测试"""

    def test_scroll_without_position(
        self, mock_pydirectinput, mock_time_sleep
    ):
        """测试不带位置的滚动"""
        executor = ActionExecutor()
        result = executor.scroll(clicks=3)

        assert result is True
        mock_pydirectinput.scroll.assert_called_once_with(3)
        mock_pydirectinput.moveTo.assert_not_called()

    def test_scroll_with_position_moves_mouse_first(
        self, mock_pydirectinput, mock_time_sleep
    ):
        """测试带位置的滚动先移动鼠标"""
        executor = ActionExecutor()
        result = executor.scroll(clicks=5, x=500, y=300)

        assert result is True
        mock_pydirectinput.moveTo.assert_called_with(500, 300)
        mock_pydirectinput.scroll.assert_called_once_with(5)


# ======================== drag 测试 ========================

class TestDrag:
    """drag 测试"""

    def test_drag_moves_from_start_to_end(
        self, mock_pydirectinput, mock_time_sleep
    ):
        """测试拖拽从起点移动到终点"""
        executor = ActionExecutor()
        result = executor.drag(start=(100, 100), end=(200, 200), duration=0.1)

        assert result is True
        # 验证移到起点
        mock_pydirectinput.moveTo.assert_called_with(100, 100)
        # 验证按下鼠标
        mock_pydirectinput.mouseDown.assert_called_once()
        # 验证移动鼠标（分段移动）
        assert mock_pydirectinput.move.called
        # 验证释放鼠标
        mock_pydirectinput.mouseUp.assert_called_once()
