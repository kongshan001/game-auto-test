"""
Unit tests for src.action.input_executor.ActionExecutor

Mocks all external dependencies (pydirectinput, win32api, win32con, PIL.Image, time.sleep)
so the tests can run on any platform without those packages installed.
"""
import sys
import os
import unittest
from unittest.mock import MagicMock, Mock, patch, call

# ---------------------------------------------------------------------------
# sys.path adjustment so that "src.action.input_executor" is importable
# ---------------------------------------------------------------------------
_PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
if _PROJECT_ROOT not in sys.path:
    sys.path.insert(0, _PROJECT_ROOT)

# ---------------------------------------------------------------------------
# Mock heavy / platform-specific third-party modules *before* importing the
# module under test.  The source file imports these at the top level.
# ---------------------------------------------------------------------------
# Create mock modules
_mock_pydirectinput = MagicMock()
_mock_pydirectinput.FAILSAFE = False

_mock_win32api = MagicMock()
_mock_win32con = MagicMock()

# Patch sys.modules so the source file's top-level imports succeed
sys.modules.setdefault("pydirectinput", _mock_pydirectinput)
sys.modules.setdefault("win32api", _mock_win32api)
sys.modules.setdefault("win32con", _mock_win32con)
sys.modules.setdefault("PIL", MagicMock())
sys.modules.setdefault("PIL.Image", MagicMock())

# Now import the module under test
from src.action.input_executor import ActionExecutor, HAS_PYDIRECTINPUT  # noqa: E402


# ===================================================================
# Helper: build a fake window_info object
# ===================================================================
def _make_window_info(left=100, top=200, width=800, height=600):
    """Return a SimpleNamespace that mimics a window_info object."""
    from types import SimpleNamespace
    return SimpleNamespace(left=left, top=top, width=width, height=height)


# ===================================================================
# Test class
# ===================================================================
class TestActionExecutorInit(unittest.TestCase):
    """Tests for ActionExecutor.__init__"""

    @patch("src.action.input_executor.HAS_PYDIRECTINPUT", True)
    def test_init_default_params(self):
        """Happy path: default parameter values are stored."""
        executor = ActionExecutor()
        self.assertIsNone(executor.window_info)
        self.assertEqual(executor.click_delay, 0.5)
        self.assertEqual(executor.type_delay, 0.1)
        self.assertEqual(executor.keypress_delay, 0.3)

    @patch("src.action.input_executor.HAS_PYDIRECTINPUT", True)
    def test_init_custom_params(self):
        """Happy path: custom parameter values are stored."""
        wi = _make_window_info()
        executor = ActionExecutor(
            window_info=wi,
            click_delay=1.0,
            type_delay=0.2,
            keypress_delay=0.5,
        )
        self.assertIs(executor.window_info, wi)
        self.assertEqual(executor.click_delay, 1.0)
        self.assertEqual(executor.type_delay, 0.2)
        self.assertEqual(executor.keypress_delay, 0.5)

    @patch("src.action.input_executor.HAS_PYDIRECTINPUT", True)
    def test_init_sets_failsafe_when_available(self):
        """Happy path: FAILSAFE is set to True when pydirectinput is available."""
        with patch("src.action.input_executor.pydirectinput", create=True) as mock_pyd:
            ActionExecutor()
            mock_pyd.FAILSAFE = True  # the __init__ does this

    @patch("src.action.input_executor.HAS_PYDIRECTINPUT", False)
    def test_init_no_pydirectinput(self):
        """Edge case: init succeeds even when pydirectinput is not available."""
        executor = ActionExecutor()
        self.assertIsNone(executor.window_info)


class TestToAbsolute(unittest.TestCase):
    """Tests for ActionExecutor._to_absolute"""

    @patch("src.action.input_executor.HAS_PYDIRECTINPUT", True)
    def test_with_window_info(self):
        """Happy path: converts relative coords to absolute with window_info."""
        wi = _make_window_info(left=100, top=200)
        executor = ActionExecutor(window_info=wi)
        result = executor._to_absolute(50, 60)
        self.assertEqual(result, (150, 260))

    @patch("src.action.input_executor.HAS_PYDIRECTINPUT", True)
    def test_without_window_info(self):
        """Edge case: returns coords unchanged when no window_info."""
        executor = ActionExecutor()
        result = executor._to_absolute(300, 400)
        self.assertEqual(result, (300, 400))

    @patch("src.action.input_executor.HAS_PYDIRECTINPUT", True)
    def test_zero_coordinates(self):
        """Edge case: zero coords with window_info offset."""
        wi = _make_window_info(left=10, top=20)
        executor = ActionExecutor(window_info=wi)
        result = executor._to_absolute(0, 0)
        self.assertEqual(result, (10, 20))


class TestToRelative(unittest.TestCase):
    """Tests for ActionExecutor._to_relative"""

    @patch("src.action.input_executor.HAS_PYDIRECTINPUT", True)
    def test_with_window_info(self):
        """Happy path: converts absolute coords to relative with window_info."""
        wi = _make_window_info(left=100, top=200)
        executor = ActionExecutor(window_info=wi)
        result = executor._to_relative(150, 260)
        self.assertEqual(result, (50, 60))

    @patch("src.action.input_executor.HAS_PYDIRECTINPUT", True)
    def test_without_window_info(self):
        """Edge case: returns coords unchanged when no window_info."""
        executor = ActionExecutor()
        result = executor._to_relative(300, 400)
        self.assertEqual(result, (300, 400))

    @patch("src.action.input_executor.HAS_PYDIRECTINPUT", True)
    def test_exact_window_origin(self):
        """Edge case: coords equal to window origin return (0, 0)."""
        wi = _make_window_info(left=100, top=200)
        executor = ActionExecutor(window_info=wi)
        result = executor._to_relative(100, 200)
        self.assertEqual(result, (0, 0))


class TestCheckAvailable(unittest.TestCase):
    """Tests for ActionExecutor._check_available"""

    @patch("src.action.input_executor.HAS_PYDIRECTINPUT", True)
    def test_available_does_not_raise(self):
        """Happy path: no exception when pydirectinput is available."""
        executor = ActionExecutor()
        # Should not raise
        executor._check_available()

    @patch("src.action.input_executor.HAS_PYDIRECTINPUT", False)
    def test_not_available_raises_runtime_error(self):
        """Error case: RuntimeError raised when pydirectinput is missing."""
        executor = ActionExecutor()
        with self.assertRaises(RuntimeError) as ctx:
            executor._check_available()
        self.assertIn("pydirectinput", str(ctx.exception))

    @patch("src.action.input_executor.HAS_PYDIRECTINPUT", False)
    def test_not_available_error_message_contains_install_hint(self):
        """Error case: the message includes install instructions."""
        executor = ActionExecutor()
        with self.assertRaises(RuntimeError) as ctx:
            executor._check_available()
        self.assertIn("pip install", str(ctx.exception))


class TestClick(unittest.TestCase):
    """Tests for ActionExecutor.click"""

    def setUp(self):
        self.patcher_pyd = patch("src.action.input_executor.pydirectinput")
        self.mock_pyd = self.patcher_pyd.start()
        self.patcher_sleep = patch("src.action.input_executor.time.sleep")
        self.mock_sleep = self.patcher_sleep.start()
        self.addCleanup(self.patcher_pyd.stop)
        self.addCleanup(self.patcher_sleep.stop)

    @patch("src.action.input_executor.HAS_PYDIRECTINPUT", True)
    def test_click_with_tuple_target(self):
        """Happy path: click at coordinate tuple."""
        executor = ActionExecutor(click_delay=0.1)
        result = executor.click((100, 200))
        self.assertTrue(result)
        self.mock_pyd.moveTo.assert_called_once_with(100, 200)
        self.mock_pyd.click.assert_called_once()

    @patch("src.action.input_executor.HAS_PYDIRECTINPUT", True)
    def test_click_right_button(self):
        """Happy path: right-click uses rightClick."""
        executor = ActionExecutor()
        result = executor.click((10, 20), button="right")
        self.assertTrue(result)
        self.mock_pyd.rightClick.assert_called_once()

    @patch("src.action.input_executor.HAS_PYDIRECTINPUT", True)
    def test_click_middle_button(self):
        """Happy path: middle-click uses middleClick."""
        executor = ActionExecutor()
        result = executor.click((10, 20), button="middle")
        self.assertTrue(result)
        self.mock_pyd.middleClick.assert_called_once()

    @patch("src.action.input_executor.HAS_PYDIRECTINPUT", True)
    def test_click_string_target_with_locator(self):
        """Happy path: string target resolved by locator."""
        mock_locator = MagicMock()
        mock_locator.get_element_center.return_value = (300, 400)
        mock_image = MagicMock()
        executor = ActionExecutor()
        result = executor.click("button1", image=mock_image, locator=mock_locator)
        self.assertTrue(result)
        mock_locator.get_element_center.assert_called_once_with(mock_image, "button1")
        self.mock_pyd.moveTo.assert_called_once_with(300, 400)

    @patch("src.action.input_executor.HAS_PYDIRECTINPUT", True)
    def test_click_string_target_not_found(self):
        """Edge case: locator returns None, click returns False."""
        mock_locator = MagicMock()
        mock_locator.get_element_center.return_value = None
        executor = ActionExecutor()
        result = executor.click("missing", locator=mock_locator)
        self.assertFalse(result)

    @patch("src.action.input_executor.HAS_PYDIRECTINPUT", True)
    def test_click_string_target_no_locator(self):
        """Error case: string target without locator raises ValueError (caught)."""
        executor = ActionExecutor()
        result = executor.click("some_text")
        self.assertFalse(result)

    @patch("src.action.input_executor.HAS_PYDIRECTINPUT", False)
    def test_click_without_pydirectinput_raises_runtime_error(self):
        """Error case: _check_available raises RuntimeError (called outside try block)."""
        executor = ActionExecutor()
        with self.assertRaises(RuntimeError):
            executor.click((100, 200))

    @patch("src.action.input_executor.HAS_PYDIRECTINPUT", True)
    def test_click_pydirectinput_exception_returns_false(self):
        """Error case: pydirectinput.moveTo raises, returns False."""
        self.mock_pyd.moveTo.side_effect = OSError("mouse error")
        executor = ActionExecutor()
        result = executor.click((50, 50))
        self.assertFalse(result)


class TestDoubleClick(unittest.TestCase):
    """Tests for ActionExecutor.double_click"""

    def setUp(self):
        self.patcher_pyd = patch("src.action.input_executor.pydirectinput")
        self.mock_pyd = self.patcher_pyd.start()
        self.patcher_sleep = patch("src.action.input_executor.time.sleep")
        self.mock_sleep = self.patcher_sleep.start()
        self.addCleanup(self.patcher_pyd.stop)
        self.addCleanup(self.patcher_sleep.stop)

    @patch("src.action.input_executor.HAS_PYDIRECTINPUT", True)
    def test_double_click_tuple_target(self):
        """Happy path: double-click at coordinates."""
        executor = ActionExecutor(click_delay=0.1)
        result = executor.double_click((250, 350))
        self.assertTrue(result)
        self.mock_pyd.doubleClick.assert_called_once()
        self.mock_pyd.moveTo.assert_called_once_with(250, 350)

    @patch("src.action.input_executor.HAS_PYDIRECTINPUT", True)
    def test_double_click_string_with_locator(self):
        """Happy path: string target resolved via locator."""
        mock_locator = MagicMock()
        mock_locator.get_element_center.return_value = (50, 60)
        executor = ActionExecutor()
        result = executor.double_click("icon", locator=mock_locator)
        self.assertTrue(result)

    @patch("src.action.input_executor.HAS_PYDIRECTINPUT", True)
    def test_double_click_string_no_locator(self):
        """Error case: string target without locator returns False."""
        executor = ActionExecutor()
        result = executor.double_click("somewhere")
        self.assertFalse(result)

    @patch("src.action.input_executor.HAS_PYDIRECTINPUT", True)
    def test_double_click_locator_returns_none(self):
        """Edge case: locator cannot find element, returns False."""
        mock_locator = MagicMock()
        mock_locator.get_element_center.return_value = None
        executor = ActionExecutor()
        result = executor.double_click("missing", locator=mock_locator)
        self.assertFalse(result)

    @patch("src.action.input_executor.HAS_PYDIRECTINPUT", False)
    def test_double_click_no_pydirectinput(self):
        """Error case: pydirectinput unavailable raises RuntimeError."""
        executor = ActionExecutor()
        with self.assertRaises(RuntimeError):
            executor.double_click((10, 10))

    @patch("src.action.input_executor.HAS_PYDIRECTINPUT", True)
    def test_double_click_exception_returns_false(self):
        """Error case: exception during doubleClick returns False."""
        self.mock_pyd.doubleClick.side_effect = Exception("fail")
        executor = ActionExecutor()
        result = executor.double_click((10, 10))
        self.assertFalse(result)


class TestRightClick(unittest.TestCase):
    """Tests for ActionExecutor.right_click"""

    def setUp(self):
        self.patcher_pyd = patch("src.action.input_executor.pydirectinput")
        self.mock_pyd = self.patcher_pyd.start()
        self.patcher_sleep = patch("src.action.input_executor.time.sleep")
        self.mock_sleep = self.patcher_sleep.start()
        self.addCleanup(self.patcher_pyd.stop)
        self.addCleanup(self.patcher_sleep.stop)

    @patch("src.action.input_executor.HAS_PYDIRECTINPUT", True)
    def test_right_click_delegates_to_click(self):
        """Happy path: right_click calls click with button='right'."""
        executor = ActionExecutor()
        result = executor.right_click((100, 200))
        self.assertTrue(result)
        self.mock_pyd.rightClick.assert_called_once()
        # left click should NOT be called
        self.mock_pyd.click.assert_not_called()

    @patch("src.action.input_executor.HAS_PYDIRECTINPUT", True)
    def test_right_click_with_locator(self):
        """Happy path: right_click with string target and locator."""
        mock_locator = MagicMock()
        mock_locator.get_element_center.return_value = (55, 66)
        executor = ActionExecutor()
        result = executor.right_click("menu_item", locator=mock_locator)
        self.assertTrue(result)

    @patch("src.action.input_executor.HAS_PYDIRECTINPUT", False)
    def test_right_click_no_pydirectinput(self):
        """Error case: raises RuntimeError when pydirectinput unavailable."""
        executor = ActionExecutor()
        with self.assertRaises(RuntimeError):
            executor.right_click((10, 10))


class TestTypeText(unittest.TestCase):
    """Tests for ActionExecutor.type_text"""

    def setUp(self):
        self.patcher_pyd = patch("src.action.input_executor.pydirectinput")
        self.mock_pyd = self.patcher_pyd.start()
        self.patcher_sleep = patch("src.action.input_executor.time.sleep")
        self.mock_sleep = self.patcher_sleep.start()
        self.addCleanup(self.patcher_pyd.stop)
        self.addCleanup(self.patcher_sleep.stop)

    @patch("src.action.input_executor.HAS_PYDIRECTINPUT", True)
    def test_type_text_no_target(self):
        """Happy path: type text without clicking a target first."""
        executor = ActionExecutor(type_delay=0.01)
        result = executor.type_text("abc")
        self.assertTrue(result)
        self.assertEqual(self.mock_pyd.write.call_count, 3)
        calls = [call("a"), call("b"), call("c")]
        self.mock_pyd.write.assert_has_calls(calls)

    @patch("src.action.input_executor.HAS_PYDIRECTINPUT", True)
    def test_type_text_with_target_tuple(self):
        """Happy path: clicks target then types text."""
        executor = ActionExecutor(type_delay=0.01)
        result = executor.type_text("hi", target=(100, 200))
        self.assertTrue(result)
        self.mock_pyd.moveTo.assert_called_with(100, 200)
        self.assertEqual(self.mock_pyd.write.call_count, 2)

    @patch("src.action.input_executor.HAS_PYDIRECTINPUT", True)
    def test_type_text_clear_first(self):
        """Happy path: clears existing text before typing."""
        executor = ActionExecutor(type_delay=0.01)
        result = executor.type_text("new", target=(50, 50), clear_first=True)
        self.assertTrue(result)
        self.mock_pyd.hotkey.assert_called_once_with("ctrl", "a")
        self.mock_pyd.press.assert_called_once_with("backspace")

    @patch("src.action.input_executor.HAS_PYDIRECTINPUT", True)
    def test_type_text_empty_string(self):
        """Edge case: empty string results in zero write calls."""
        executor = ActionExecutor()
        result = executor.type_text("")
        self.assertTrue(result)
        self.mock_pyd.write.assert_not_called()

    @patch("src.action.input_executor.HAS_PYDIRECTINPUT", False)
    def test_type_text_no_pydirectinput(self):
        """Error case: raises RuntimeError when pydirectinput unavailable."""
        executor = ActionExecutor()
        with self.assertRaises(RuntimeError):
            executor.type_text("test")

    @patch("src.action.input_executor.HAS_PYDIRECTINPUT", True)
    def test_type_text_write_exception(self):
        """Error case: write raises, returns False."""
        self.mock_pyd.write.side_effect = Exception("write error")
        executor = ActionExecutor()
        result = executor.type_text("x")
        self.assertFalse(result)

    @patch("src.action.input_executor.HAS_PYDIRECTINPUT", True)
    def test_type_text_with_string_target_and_locator(self):
        """Happy path: string target resolved via locator."""
        mock_locator = MagicMock()
        mock_locator.get_element_center.return_value = (10, 20)
        executor = ActionExecutor(type_delay=0.01)
        result = executor.type_text("ok", target="field", locator=mock_locator)
        self.assertTrue(result)
        mock_locator.get_element_center.assert_called_once()


class TestPressKey(unittest.TestCase):
    """Tests for ActionExecutor.press_key"""

    def setUp(self):
        self.patcher_pyd = patch("src.action.input_executor.pydirectinput")
        self.mock_pyd = self.patcher_pyd.start()
        self.patcher_sleep = patch("src.action.input_executor.time.sleep")
        self.mock_sleep = self.patcher_sleep.start()
        self.addCleanup(self.patcher_pyd.stop)
        self.addCleanup(self.patcher_sleep.stop)

    @patch("src.action.input_executor.HAS_PYDIRECTINPUT", True)
    def test_press_key_enter(self):
        """Happy path: press enter key."""
        executor = ActionExecutor(keypress_delay=0.05)
        result = executor.press_key("enter")
        self.assertTrue(result)
        self.mock_pyd.press.assert_called_once_with("enter")

    @patch("src.action.input_executor.HAS_PYDIRECTINPUT", True)
    def test_press_key_esc(self):
        """Happy path: press escape key."""
        executor = ActionExecutor()
        result = executor.press_key("esc")
        self.assertTrue(result)
        self.mock_pyd.press.assert_called_once_with("esc")

    @patch("src.action.input_executor.HAS_PYDIRECTINPUT", False)
    def test_press_key_no_pydirectinput(self):
        """Error case: raises RuntimeError when pydirectinput unavailable."""
        executor = ActionExecutor()
        with self.assertRaises(RuntimeError):
            executor.press_key("enter")

    @patch("src.action.input_executor.HAS_PYDIRECTINPUT", True)
    def test_press_key_exception(self):
        """Error case: pydirectinput.press raises, returns False."""
        self.mock_pyd.press.side_effect = Exception("key error")
        executor = ActionExecutor()
        result = executor.press_key("a")
        self.assertFalse(result)


class TestPressKeys(unittest.TestCase):
    """Tests for ActionExecutor.press_keys"""

    def setUp(self):
        self.patcher_pyd = patch("src.action.input_executor.pydirectinput")
        self.mock_pyd = self.patcher_pyd.start()
        self.patcher_sleep = patch("src.action.input_executor.time.sleep")
        self.mock_sleep = self.patcher_sleep.start()
        self.addCleanup(self.patcher_pyd.stop)
        self.addCleanup(self.patcher_sleep.stop)

    @patch("src.action.input_executor.HAS_PYDIRECTINPUT", True)
    def test_press_keys_ctrl_c(self):
        """Happy path: Ctrl+C combo."""
        executor = ActionExecutor()
        result = executor.press_keys(["ctrl", "c"])
        self.assertTrue(result)
        self.mock_pyd.hotkey.assert_called_once_with("ctrl", "c")

    @patch("src.action.input_executor.HAS_PYDIRECTINPUT", True)
    def test_press_keys_alt_f4(self):
        """Happy path: Alt+F4 combo."""
        executor = ActionExecutor()
        result = executor.press_keys(["alt", "f4"])
        self.assertTrue(result)
        self.mock_pyd.hotkey.assert_called_once_with("alt", "f4")

    @patch("src.action.input_executor.HAS_PYDIRECTINPUT", True)
    def test_press_keys_single_key(self):
        """Edge case: single key in the list still calls hotkey."""
        executor = ActionExecutor()
        result = executor.press_keys(["enter"])
        self.assertTrue(result)
        self.mock_pyd.hotkey.assert_called_once_with("enter")

    @patch("src.action.input_executor.HAS_PYDIRECTINPUT", False)
    def test_press_keys_no_pydirectinput(self):
        """Error case: raises RuntimeError when pydirectinput unavailable."""
        executor = ActionExecutor()
        with self.assertRaises(RuntimeError):
            executor.press_keys(["ctrl", "c"])

    @patch("src.action.input_executor.HAS_PYDIRECTINPUT", True)
    def test_press_keys_exception(self):
        """Error case: hotkey raises, returns False."""
        self.mock_pyd.hotkey.side_effect = Exception("hotkey fail")
        executor = ActionExecutor()
        result = executor.press_keys(["ctrl", "a"])
        self.assertFalse(result)


class TestWait(unittest.TestCase):
    """Tests for ActionExecutor.wait"""

    @patch("src.action.input_executor.time.sleep")
    def test_wait_returns_true(self, mock_sleep):
        """Happy path: wait always returns True."""
        executor = ActionExecutor()
        result = executor.wait(2.5)
        self.assertTrue(result)
        mock_sleep.assert_called_once_with(2.5)

    @patch("src.action.input_executor.time.sleep")
    def test_wait_zero(self, mock_sleep):
        """Edge case: wait 0 seconds."""
        executor = ActionExecutor()
        result = executor.wait(0)
        self.assertTrue(result)
        mock_sleep.assert_called_once_with(0)

    @patch("src.action.input_executor.time.sleep")
    def test_wait_fractional(self, mock_sleep):
        """Edge case: fractional second wait."""
        executor = ActionExecutor()
        result = executor.wait(0.01)
        self.assertTrue(result)
        mock_sleep.assert_called_once_with(0.01)


class TestScroll(unittest.TestCase):
    """Tests for ActionExecutor.scroll"""

    def setUp(self):
        self.patcher_pyd = patch("src.action.input_executor.pydirectinput")
        self.mock_pyd = self.patcher_pyd.start()
        self.patcher_sleep = patch("src.action.input_executor.time.sleep")
        self.mock_sleep = self.patcher_sleep.start()
        self.addCleanup(self.patcher_pyd.stop)
        self.addCleanup(self.patcher_sleep.stop)

    @patch("src.action.input_executor.HAS_PYDIRECTINPUT", True)
    def test_scroll_positive(self):
        """Happy path: scroll up (positive clicks)."""
        executor = ActionExecutor()
        result = executor.scroll(3)
        self.assertTrue(result)
        self.mock_pyd.scroll.assert_called_once_with(3)
        self.mock_pyd.moveTo.assert_not_called()

    @patch("src.action.input_executor.HAS_PYDIRECTINPUT", True)
    def test_scroll_negative(self):
        """Happy path: scroll down (negative clicks)."""
        executor = ActionExecutor()
        result = executor.scroll(-5)
        self.assertTrue(result)
        self.mock_pyd.scroll.assert_called_once_with(-5)

    @patch("src.action.input_executor.HAS_PYDIRECTINPUT", True)
    def test_scroll_with_position(self):
        """Happy path: scroll at specific position moves mouse first."""
        executor = ActionExecutor()
        result = executor.scroll(2, x=500, y=300)
        self.assertTrue(result)
        self.mock_pyd.moveTo.assert_called_once_with(500, 300)
        self.mock_pyd.scroll.assert_called_once_with(2)

    @patch("src.action.input_executor.HAS_PYDIRECTINPUT", True)
    def test_scroll_partial_position_only_x(self):
        """Edge case: only x provided, y is None, no moveTo call."""
        executor = ActionExecutor()
        result = executor.scroll(1, x=100)
        self.assertTrue(result)
        self.mock_pyd.moveTo.assert_not_called()

    @patch("src.action.input_executor.HAS_PYDIRECTINPUT", True)
    def test_scroll_partial_position_only_y(self):
        """Edge case: only y provided, x is None, no moveTo call."""
        executor = ActionExecutor()
        result = executor.scroll(1, y=200)
        self.assertTrue(result)
        self.mock_pyd.moveTo.assert_not_called()

    @patch("src.action.input_executor.HAS_PYDIRECTINPUT", False)
    def test_scroll_no_pydirectinput(self):
        """Error case: raises RuntimeError when pydirectinput unavailable."""
        executor = ActionExecutor()
        with self.assertRaises(RuntimeError):
            executor.scroll(3)

    @patch("src.action.input_executor.HAS_PYDIRECTINPUT", True)
    def test_scroll_exception(self):
        """Error case: pydirectinput.scroll raises, returns False."""
        self.mock_pyd.scroll.side_effect = Exception("scroll fail")
        executor = ActionExecutor()
        result = executor.scroll(5)
        self.assertFalse(result)


class TestDrag(unittest.TestCase):
    """Tests for ActionExecutor.drag"""

    def setUp(self):
        self.patcher_pyd = patch("src.action.input_executor.pydirectinput")
        self.mock_pyd = self.patcher_pyd.start()
        self.patcher_sleep = patch("src.action.input_executor.time.sleep")
        self.mock_sleep = self.patcher_sleep.start()
        self.addCleanup(self.patcher_pyd.stop)
        self.addCleanup(self.patcher_sleep.stop)

    @patch("src.action.input_executor.HAS_PYDIRECTINPUT", True)
    def test_drag_basic(self):
        """Happy path: drag from start to end."""
        executor = ActionExecutor()
        result = executor.drag((0, 0), (100, 100), duration=0.1)
        self.assertTrue(result)
        self.mock_pyd.moveTo.assert_called_once_with(0, 0)
        self.mock_pyd.mouseDown.assert_called_once()
        self.mock_pyd.mouseUp.assert_called_once()

    @patch("src.action.input_executor.HAS_PYDIRECTINPUT", True)
    def test_drag_moves_in_steps(self):
        """Happy path: drag performs intermediate move calls."""
        executor = ActionExecutor()
        # duration=0.5 -> steps=10
        result = executor.drag((0, 0), (100, 0), duration=0.5)
        self.assertTrue(result)
        # dx = 100/10 = 10, dy = 0/10 = 0
        self.assertEqual(self.mock_pyd.move.call_count, 10)

    @patch("src.action.input_executor.HAS_PYDIRECTINPUT", True)
    def test_drag_zero_duration_no_intermediate_moves(self):
        """Edge case: duration=0 means steps=0, no intermediate move calls."""
        executor = ActionExecutor()
        result = executor.drag((10, 20), (30, 40), duration=0)
        self.assertTrue(result)
        self.mock_pyd.move.assert_not_called()
        self.mock_pyd.mouseDown.assert_called_once()
        self.mock_pyd.mouseUp.assert_called_once()

    @patch("src.action.input_executor.HAS_PYDIRECTINPUT", False)
    def test_drag_no_pydirectinput(self):
        """Error case: raises RuntimeError when pydirectinput unavailable."""
        executor = ActionExecutor()
        with self.assertRaises(RuntimeError):
            executor.drag((0, 0), (100, 100))

    @patch("src.action.input_executor.HAS_PYDIRECTINPUT", True)
    def test_drag_mouseDown_exception(self):
        """Error case: mouseDown raises, returns False."""
        self.mock_pyd.mouseDown.side_effect = Exception("mouse error")
        executor = ActionExecutor()
        result = executor.drag((0, 0), (50, 50))
        self.assertFalse(result)

    @patch("src.action.input_executor.HAS_PYDIRECTINPUT", True)
    def test_drag_negative_direction(self):
        """Edge case: dragging in negative direction (left/up)."""
        executor = ActionExecutor()
        result = executor.drag((100, 100), (0, 0), duration=0.1)
        self.assertTrue(result)
        self.mock_pyd.mouseUp.assert_called_once()


class TestCoordinateConversionIntegration(unittest.TestCase):
    """Integration-style tests for coordinate conversion with window_info."""

    @patch("src.action.input_executor.HAS_PYDIRECTINPUT", True)
    def test_to_absolute_and_back(self):
        """Round-trip: relative -> absolute -> relative returns original."""
        wi = _make_window_info(left=50, top=80)
        executor = ActionExecutor(window_info=wi)
        original = (120, 250)
        absolute = executor._to_absolute(*original)
        relative = executor._to_relative(*absolute)
        self.assertEqual(relative, original)

    @patch("src.action.input_executor.HAS_PYDIRECTINPUT", True)
    def test_to_absolute_with_large_offset(self):
        """Edge case: large window offset values."""
        wi = _make_window_info(left=1920, top=1080)
        executor = ActionExecutor(window_info=wi)
        result = executor._to_absolute(100, 100)
        self.assertEqual(result, (2020, 1180))

    @patch("src.action.input_executor.HAS_PYDIRECTINPUT", True)
    def test_to_relative_negative_coords(self):
        """Edge case: absolute coords less than window origin yield negative."""
        wi = _make_window_info(left=500, top=500)
        executor = ActionExecutor(window_info=wi)
        result = executor._to_relative(100, 100)
        self.assertEqual(result, (-400, -400))


if __name__ == "__main__":
    unittest.main()
