"""
Unit tests for src/main.py - GameAutoTester, setup_logging, and main().

Covers every public method of GameAutoTester (__init__, initialize, execute_action,
run, cleanup) plus the module-level setup_logging and main functions.
All external and internal dependencies are mocked via unittest.mock.
"""
import os
import sys
import unittest
from unittest.mock import (
    MagicMock,
    Mock,
    patch,
    call,
)

# ---------------------------------------------------------------------------
# Adjust sys.path so that imports resolve correctly during test execution.
# ---------------------------------------------------------------------------
_PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
_SRC_DIR = os.path.join(_PROJECT_ROOT, "src")
if _SRC_DIR not in sys.path:
    sys.path.insert(0, _SRC_DIR)

# ---------------------------------------------------------------------------
# Mock *every* internal module import before importing the module under test.
# This prevents real side-effects (file I/O, network calls, GUI operations).
# ---------------------------------------------------------------------------
_MOCK_MODULES = {
    "utils": MagicMock(),
    "utils.config": MagicMock(),
    "utils.glm_client": MagicMock(),
    "game": MagicMock(),
    "game.game_launcher": MagicMock(),
    "action": MagicMock(),
    "action.window_manager": MagicMock(),
    "vision": MagicMock(),
    "vision.screen_capture": MagicMock(),
    "vision.ocr_engine": MagicMock(),
    "vision.element_locator": MagicMock(),
    "action.input_executor": MagicMock(),
    "agents": MagicMock(),
    "agents.decision_agent": MagicMock(),
    "agents.state_memory": MagicMock(),
}

for _mod_name, _mod_val in _MOCK_MODULES.items():
    sys.modules[_mod_name] = _mod_val

# Grab references to the mock *classes* (callable mocks).
# Each time the constructor is called, .return_value gives the instance.
MockConfig = _MOCK_MODULES["utils.config"].Config
MockGLMClient = _MOCK_MODULES["utils.glm_client"].GLMClient
MockGameLauncher = _MOCK_MODULES["game.game_launcher"].GameLauncher
MockWindowManager = _MOCK_MODULES["action.window_manager"].WindowManager
MockScreenCapture = _MOCK_MODULES["vision.screen_capture"].ScreenCapture
MockOCREngine = _MOCK_MODULES["vision.ocr_engine"].OCREngine
MockElementLocator = _MOCK_MODULES["vision.element_locator"].ElementLocator
MockActionExecutor = _MOCK_MODULES["action.input_executor"].ActionExecutor
MockDecisionAgent = _MOCK_MODULES["agents.decision_agent"].DecisionAgent
MockStateMemory = _MOCK_MODULES["agents.state_memory"].StateMemory

# Now safe to import the module under test.
from main import GameAutoTester, setup_logging, main as app_main  # noqa: E402


# ---------------------------------------------------------------------------
# Helper: build a fake Config object with sensible defaults.
# ---------------------------------------------------------------------------
def _make_mock_config(**overrides):
    """Return a MagicMock that quacks like a Config instance."""
    cfg = MagicMock()
    cfg.glm_api_key = overrides.get("glm_api_key", "test-key")
    cfg.glm_model = overrides.get("glm_model", "glm-4")
    cfg.game_exe_path = overrides.get("game_exe_path", "C:/game.exe")
    cfg.game_window_title = overrides.get("game_window_title", "TestGame")
    cfg.game_startup_delay = overrides.get("game_startup_delay", 5)
    cfg.screenshot_save_path = overrides.get("screenshot_save_path", "./screenshots")
    cfg.ocr_languages = overrides.get("ocr_languages", ["chi_sim", "eng"])
    cfg.ocr_enabled = overrides.get("ocr_enabled", True)
    cfg.click_delay = overrides.get("click_delay", 0.1)
    cfg.type_delay = overrides.get("type_delay", 0.05)
    cfg.keypress_delay = overrides.get("keypress_delay", 0.1)
    cfg.test_case = overrides.get("test_case", "Click the Start button")
    cfg.max_steps = overrides.get("max_steps", 10)
    cfg.save_screenshots = overrides.get("save_screenshots", True)
    cfg.log_level = overrides.get("log_level", "INFO")
    return cfg


def _reset_mock_classes():
    """Reset all mock-class call counts and replace return_value with fresh mocks.

    Calling cls.reset_mock() does NOT clear deep child side-effects (e.g.
    return_value.launch.side_effect).  The only reliable way is to assign a
    brand-new MagicMock as the return_value.
    """
    for cls in (
        MockGLMClient, MockGameLauncher, MockWindowManager,
        MockScreenCapture, MockOCREngine, MockElementLocator,
        MockActionExecutor, MockStateMemory, MockDecisionAgent,
    ):
        cls.reset_mock()
        cls.return_value = MagicMock()


# ===================================================================
# Test: setup_logging
# ===================================================================
class TestSetupLogging(unittest.TestCase):
    """Tests for the module-level setup_logging function."""

    @patch("main.logging")
    @patch("main.Path")
    def test_setup_logging_creates_log_dir_and_configures(self, mock_path_cls, mock_logging):
        """setup_logging should create logs/ dir and call basicConfig."""
        mock_log_dir = MagicMock()
        mock_path_cls.return_value = mock_log_dir

        setup_logging("DEBUG")

        mock_log_dir.mkdir.assert_called_once_with(exist_ok=True)
        mock_logging.basicConfig.assert_called_once()
        call_kwargs = mock_logging.basicConfig.call_args[1]
        self.assertEqual(call_kwargs["level"], mock_logging.DEBUG)

    @patch("main.logging")
    @patch("main.Path")
    def test_setup_logging_default_level(self, mock_path_cls, mock_logging):
        """setup_logging defaults to INFO when no level is passed."""
        mock_log_dir = MagicMock()
        mock_path_cls.return_value = mock_log_dir

        setup_logging()

        call_kwargs = mock_logging.basicConfig.call_args[1]
        self.assertEqual(call_kwargs["level"], mock_logging.INFO)


# ===================================================================
# Test: GameAutoTester.__init__
# ===================================================================
class TestGameAutoTesterInit(unittest.TestCase):
    """Tests for GameAutoTester.__init__."""

    def setUp(self):
        _reset_mock_classes()

    def test_init_creates_all_modules_with_ocr_enabled(self):
        """When OCR is enabled, all modules including OCREngine should be created."""
        cfg = _make_mock_config(ocr_enabled=True)
        tester = GameAutoTester(cfg)

        MockGLMClient.assert_called_once_with(
            api_key=cfg.glm_api_key, model=cfg.glm_model
        )
        MockGameLauncher.assert_called_once_with(
            exe_path=cfg.game_exe_path,
            window_title=cfg.game_window_title,
            startup_delay=cfg.game_startup_delay,
        )
        MockWindowManager.assert_called_once()
        MockScreenCapture.assert_called_once_with(save_path=cfg.screenshot_save_path)
        MockOCREngine.assert_called_once_with(languages=cfg.ocr_languages, use_gpu=False)
        MockElementLocator.assert_called_once_with(
            ocr_engine=tester.ocr_engine, glm_client=tester.glm_client
        )
        MockActionExecutor.assert_called_once_with(
            click_delay=cfg.click_delay,
            type_delay=cfg.type_delay,
            keypress_delay=cfg.keypress_delay,
        )
        MockStateMemory.assert_called_once()
        tester.state_memory.set_test_case.assert_called_once_with(cfg.test_case)

        self.assertIsNone(tester.window_info)
        self.assertFalse(tester.running)

    def test_init_ocr_disabled_sets_engine_to_none(self):
        """When OCR is disabled, ocr_engine should be None."""
        cfg = _make_mock_config(ocr_enabled=False)
        tester = GameAutoTester(cfg)

        MockOCREngine.assert_not_called()
        self.assertIsNone(tester.ocr_engine)

    def test_init_stores_config(self):
        """Config should be stored as-is on the tester instance."""
        cfg = _make_mock_config()
        tester = GameAutoTester(cfg)
        self.assertIs(tester.config, cfg)

    def test_init_creates_logger(self):
        """A logger named after the class should be created."""
        cfg = _make_mock_config()
        tester = GameAutoTester(cfg)
        self.assertEqual(tester.logger.name, "GameAutoTester")


# ===================================================================
# Test: GameAutoTester.initialize
# ===================================================================
class TestGameAutoTesterInitialize(unittest.TestCase):
    """Tests for GameAutoTester.initialize."""

    def setUp(self):
        _reset_mock_classes()
        self.cfg = _make_mock_config()
        self.tester = GameAutoTester(self.cfg)
        # Prepare a fake window_info mock
        self.fake_window = MagicMock()
        self.fake_window.title = "TestGame"
        self.fake_window.width = 1920
        self.fake_window.height = 1080
        self.fake_window.hwnd = 12345

    def test_initialize_success(self):
        """initialize should launch game, find window, wire up modules, and set running."""
        self.tester.window_manager.wait_for_window.return_value = self.fake_window

        self.tester.initialize()

        self.tester.game_launcher.launch.assert_called_once()
        self.tester.window_manager.wait_for_window.assert_called_once_with(
            self.tester.game_launcher.process,
            timeout=30,
            title=self.cfg.game_window_title,
        )
        self.tester.screen_capture.set_window.assert_called_once_with(self.fake_window)
        self.assertEqual(self.tester.element_locator.window_info, self.fake_window)
        self.assertEqual(self.tester.action_executor.window_info, self.fake_window)
        self.tester.window_manager.activate_window.assert_called_once_with(12345)
        self.assertTrue(self.tester.running)
        self.assertIs(self.tester.window_info, self.fake_window)
        self.tester.state_memory.start_test.assert_called_once()

        # DecisionAgent should have been created with correct args
        MockDecisionAgent.assert_called_once_with(
            glm_client=self.tester.glm_client,
            test_case=self.cfg.test_case,
            state_memory=self.tester.state_memory,
            use_react=True,
            max_retry_same_action=3,
        )
        # The decision_agent attribute should now exist
        self.assertIsNotNone(self.tester.decision_agent)

    def test_initialize_game_launch_failure_raises(self):
        """If game_launcher.launch() raises, initialize should propagate the error."""
        self.tester.game_launcher.launch.side_effect = RuntimeError("Launch failed")

        with self.assertRaises(RuntimeError):
            self.tester.initialize()

    def test_initialize_window_not_found_raises(self):
        """If wait_for_window returns None, initialize should raise RuntimeError."""
        self.tester.window_manager.wait_for_window.return_value = None

        with self.assertRaises(RuntimeError) as ctx:
            self.tester.initialize()
        self.assertIn("无法获取游戏窗口", str(ctx.exception))


# ===================================================================
# Test: GameAutoTester.execute_action
# ===================================================================
class TestGameAutoTesterExecuteAction(unittest.TestCase):
    """Tests for GameAutoTester.execute_action covering every action type."""

    def setUp(self):
        _reset_mock_classes()
        self.cfg = _make_mock_config(ocr_enabled=True)
        self.tester = GameAutoTester(self.cfg)
        # Simulate initialized state
        self.tester.running = True
        self.tester.window_info = MagicMock()

    # ---- click ----

    def test_execute_action_click_success(self):
        """click action delegates to action_executor.click and records result."""
        self.tester.action_executor.click.return_value = True
        self.tester.screen_capture.capture.return_value = "screenshot_data"

        result = self.tester.execute_action({
            "action": "click",
            "target": "start_btn",
            "reasoning": "Need to start the game",
        })

        self.assertTrue(result)
        self.tester.action_executor.click.assert_called_once_with(
            target="start_btn",
            image="screenshot_data",
            locator=self.tester.element_locator,
        )
        self.tester.state_memory.add_action.assert_called_once()
        add_kwargs = self.tester.state_memory.add_action.call_args[1]
        self.assertEqual(add_kwargs["action"], "click")
        self.assertTrue(add_kwargs["success"])

    def test_execute_action_click_failure(self):
        """click action returns False when executor fails."""
        self.tester.action_executor.click.return_value = False
        self.tester.screen_capture.capture.return_value = "img"

        result = self.tester.execute_action({"action": "click", "target": "btn"})

        self.assertFalse(result)
        add_kwargs = self.tester.state_memory.add_action.call_args[1]
        self.assertFalse(add_kwargs["success"])

    def test_execute_action_click_no_reasoning(self):
        """click without reasoning uses a default description."""
        self.tester.action_executor.click.return_value = True
        self.tester.screen_capture.capture.return_value = "img"

        self.tester.execute_action({"action": "click", "target": "ok_btn"})

        add_kwargs = self.tester.state_memory.add_action.call_args[1]
        self.assertIn("ok_btn", add_kwargs["description"])

    # ---- type ----

    def test_execute_action_type_success(self):
        """type action delegates to action_executor.type_text."""
        self.tester.action_executor.type_text.return_value = True
        self.tester.screen_capture.capture.return_value = "img"

        result = self.tester.execute_action({
            "action": "type",
            "target": "name_field",
            "text": "hello",
            "reasoning": "Enter player name",
        })

        self.assertTrue(result)
        self.tester.action_executor.type_text.assert_called_once_with(
            text="hello",
            target="name_field",
            image="img",
            locator=self.tester.element_locator,
        )

    def test_execute_action_type_default_empty_text(self):
        """type action with no text defaults to empty string."""
        self.tester.action_executor.type_text.return_value = True
        self.tester.screen_capture.capture.return_value = "img"

        self.tester.execute_action({"action": "type", "target": "field"})

        call_args = self.tester.action_executor.type_text.call_args
        self.assertEqual(call_args[1]["text"], "")

    # ---- keypress ----

    def test_execute_action_keypress_success(self):
        """keypress action delegates to action_executor.press_key."""
        self.tester.action_executor.press_key.return_value = True

        result = self.tester.execute_action({
            "action": "keypress",
            "key": "enter",
            "reasoning": "Confirm dialog",
        })

        self.assertTrue(result)
        self.tester.action_executor.press_key.assert_called_once_with("enter")

    def test_execute_action_keypress_failure(self):
        """keypress action returns False when press_key fails."""
        self.tester.action_executor.press_key.return_value = False

        result = self.tester.execute_action({"action": "keypress", "key": "esc"})

        self.assertFalse(result)

    # ---- wait ----

    def test_execute_action_wait_default_seconds(self):
        """wait action with no seconds defaults to 1."""
        result = self.tester.execute_action({"action": "wait"})

        self.assertTrue(result)
        self.tester.action_executor.wait.assert_called_once_with(1)

    def test_execute_action_wait_custom_seconds(self):
        """wait action passes the specified seconds to executor."""
        result = self.tester.execute_action({
            "action": "wait",
            "seconds": 5,
        })

        self.assertTrue(result)
        self.tester.action_executor.wait.assert_called_once_with(5)

    # ---- assert ----

    def test_execute_action_assert_with_ocr_match(self):
        """assert with OCR returning matches should succeed."""
        self.tester.screen_capture.capture.return_value = "img"
        self.tester.ocr_engine.search_text.return_value = ["matched"]

        result = self.tester.execute_action({
            "action": "assert",
            "condition": "Game Over",
            "reasoning": "Check for game over screen",
        })

        self.assertTrue(result)
        self.tester.ocr_engine.search_text.assert_called_once_with("img", "Game Over")

    def test_execute_action_assert_with_ocr_no_match(self):
        """assert with OCR returning no matches should fail."""
        self.tester.screen_capture.capture.return_value = "img"
        self.tester.ocr_engine.search_text.return_value = []

        result = self.tester.execute_action({
            "action": "assert",
            "condition": "not present text",
        })

        self.assertFalse(result)

    def test_execute_action_assert_ocr_disabled(self):
        """assert with OCR disabled should log warning and return False."""
        cfg = _make_mock_config(ocr_enabled=False)
        tester = GameAutoTester(cfg)
        tester.running = True
        tester.window_info = MagicMock()
        tester.screen_capture.capture.return_value = "img"

        result = tester.execute_action({
            "action": "assert",
            "condition": "some text",
        })

        self.assertFalse(result)

    # ---- done ----

    def test_execute_action_done_default_success(self):
        """done action defaults to success=True."""
        result = self.tester.execute_action({
            "action": "done",
            "reason": "All steps completed",
        })

        self.assertTrue(result)

    def test_execute_action_done_explicit_failure(self):
        """done action can be marked as failure."""
        result = self.tester.execute_action({
            "action": "done",
            "success": False,
            "reason": "Critical error encountered",
        })

        self.assertFalse(result)

    def test_execute_action_done_with_reasoning(self):
        """done action records reasoning in description when provided."""
        self.tester.execute_action({
            "action": "done",
            "reasoning": "AI decided test is complete",
            "reason": "ok",
        })

        add_kwargs = self.tester.state_memory.add_action.call_args[1]
        self.assertIn("AI decided test is complete", add_kwargs["description"])

    # ---- unknown ----

    def test_execute_action_unknown_type_returns_false(self):
        """Unknown action type should return False."""
        result = self.tester.execute_action({"action": "fly"})

        self.assertFalse(result)

    def test_execute_action_missing_action_key_returns_false(self):
        """Missing 'action' key should return False (action_type is None -> else)."""
        result = self.tester.execute_action({})
        self.assertFalse(result)

    # ---- exception handling ----

    def test_execute_action_exception_returns_false(self):
        """If an exception is raised inside action handling, returns False and records error."""
        self.tester.screen_capture.capture.side_effect = Exception("capture failed")

        result = self.tester.execute_action({
            "action": "click",
            "target": "btn",
        })

        self.assertFalse(result)
        add_kwargs = self.tester.state_memory.add_action.call_args[1]
        self.assertFalse(add_kwargs["success"])
        self.assertIn("error", add_kwargs)

    def test_execute_action_exception_in_keypress(self):
        """Exception during keypress is caught and False is returned."""
        self.tester.action_executor.press_key.side_effect = RuntimeError("Key not found")

        result = self.tester.execute_action({"action": "keypress", "key": "f25"})

        self.assertFalse(result)


# ===================================================================
# Test: GameAutoTester.run
# ===================================================================
class TestGameAutoTesterRun(unittest.TestCase):
    """Tests for GameAutoTester.run covering the main execution loop."""

    def setUp(self):
        _reset_mock_classes()
        self.cfg = _make_mock_config(max_steps=3, save_screenshots=True)
        self.tester = GameAutoTester(self.cfg)
        self.fake_window = MagicMock()
        self.fake_window.title = "TestGame"
        self.fake_window.width = 800
        self.fake_window.height = 600
        self.fake_window.hwnd = 999

        # configure window_manager to find the fake window during initialize()
        self.tester.window_manager.wait_for_window.return_value = self.fake_window

        # Provide a default decision_agent mock for tests that need to
        # configure it *before* initialize() is called.  The agent is
        # normally created inside initialize(), but because we want to
        # pre-configure decide/validate_action, we set the attribute early
        # so that tests can set side_effects.  initialize() will overwrite
        # it via MockDecisionAgent(), but we let that happen and re-assign
        # afterwards by configuring MockDecisionAgent.return_value.
        self._mock_decision_agent = MagicMock()
        MockDecisionAgent.return_value = self._mock_decision_agent

    def _configure_run_defaults(self):
        """Set up common mock returns so run() can proceed past initialize()."""
        self._mock_decision_agent.validate_action.return_value = True
        self.tester.screen_capture.capture.return_value = "img"

    # ---- successful completion via "done" action ----

    @patch("main.time.sleep")
    def test_run_successful_completion(self, mock_sleep):
        """run should execute steps until a 'done' action is received."""
        self._mock_decision_agent.decide.side_effect = [
            {
                "reasoning": "Click start",
                "action": {"action": "click", "target": "start"},
            },
            {
                "reasoning": "Test complete",
                "action": {"action": "done", "success": True, "reason": "All good"},
            },
        ]
        self._configure_run_defaults()
        self.tester.action_executor.click.return_value = True

        self.tester.run()

        self.assertEqual(self._mock_decision_agent.decide.call_count, 2)
        self.assertFalse(self.tester.running)
        self.tester.state_memory.end_test.assert_called_once_with(success=True)
        # cleanup should be called in finally
        self.tester.state_memory.save_to_file.assert_called_with(
            "logs/test_record.json"
        )

    # ---- max_steps reached ----

    @patch("main.time.sleep")
    def test_run_max_steps_reached(self, mock_sleep):
        """run should stop when max_steps is reached and mark test as failed."""
        self._mock_decision_agent.decide.return_value = {
            "reasoning": "Keep clicking",
            "action": {"action": "click", "target": "btn"},
        }
        self._configure_run_defaults()
        self.tester.action_executor.click.return_value = True

        self.tester.run()

        # decide should have been called max_steps times (3)
        self.assertEqual(self._mock_decision_agent.decide.call_count, 3)
        self.tester.state_memory.end_test.assert_called_once_with(success=False)

    # ---- consecutive failures trigger forced wait ----

    @patch("main.time.sleep")
    def test_run_consecutive_failures_force_wait(self, mock_sleep):
        """After 5 consecutive failures, a forced wait should be triggered."""
        _reset_mock_classes()
        cfg = _make_mock_config(max_steps=7, save_screenshots=True)
        tester = GameAutoTester(cfg)
        tester.window_manager.wait_for_window.return_value = self.fake_window

        mock_da = MagicMock()
        MockDecisionAgent.return_value = mock_da

        # First 5 steps fail, then a "done" action
        fail_decision = {
            "reasoning": "Trying",
            "action": {"action": "click", "target": "btn"},
        }
        done_decision = {
            "reasoning": "Giving up",
            "action": {"action": "done", "success": False},
        }
        mock_da.decide.side_effect = [
            fail_decision, fail_decision, fail_decision,
            fail_decision, fail_decision, done_decision,
        ]
        mock_da.validate_action.return_value = True
        tester.action_executor.click.return_value = False
        tester.screen_capture.capture.return_value = "img"

        tester.run()

        # The forced wait(3) should have been called once after 5 failures
        tester.action_executor.wait.assert_any_call(3)

    # ---- invalid action format falls back to wait ----

    @patch("main.time.sleep")
    def test_run_invalid_action_falls_back_to_wait(self, mock_sleep):
        """If validate_action returns False, action falls back to wait(1s)."""
        self._mock_decision_agent.decide.side_effect = [
            {
                "reasoning": "Bad idea",
                "action": {"action": "click"},  # missing target
            },
            {
                "reasoning": "Done",
                "action": {"action": "done", "success": True},
            },
        ]
        # First call returns False (invalid), second returns True
        self._mock_decision_agent.validate_action.side_effect = [False, True]
        self._configure_run_defaults()

        self.tester.run()

        # The fallback action {"action": "wait", "seconds": 1} should be executed
        self.tester.action_executor.wait.assert_called()

    # ---- warning from decision result is logged ----

    @patch("main.time.sleep")
    def test_run_logs_decision_warning(self, mock_sleep):
        """Warnings from decision_result should be logged without crashing."""
        self._mock_decision_agent.decide.side_effect = [
            {
                "reasoning": "Hmm",
                "warning": "Low confidence",
                "action": {"action": "done", "success": True},
            },
        ]
        self._configure_run_defaults()

        # Should not raise
        self.tester.run()

    # ---- KeyboardInterrupt handling ----

    @patch("main.time.sleep")
    def test_run_keyboard_interrupt(self, mock_sleep):
        """KeyboardInterrupt should end test as failure and call cleanup."""
        self._mock_decision_agent.decide.side_effect = KeyboardInterrupt()
        self._configure_run_defaults()

        self.tester.run()

        self.tester.state_memory.end_test.assert_called_once_with(success=False)

    # ---- generic exception propagates after cleanup ----

    @patch("main.time.sleep")
    def test_run_generic_exception_propagates(self, mock_sleep):
        """Non-KeyboardInterrupt exceptions should propagate after cleanup."""
        self._mock_decision_agent.decide.side_effect = RuntimeError("AI broke")
        self._configure_run_defaults()

        with self.assertRaises(RuntimeError):
            self.tester.run()

        self.tester.state_memory.end_test.assert_called_once_with(success=False)

    # ---- screenshots are saved when config.save_screenshots is True ----

    @patch("main.time.sleep")
    def test_run_saves_screenshots_when_enabled(self, mock_sleep):
        """When save_screenshots is True, capture_and_save is called for each step."""
        self._mock_decision_agent.decide.return_value = {
            "action": {"action": "done", "success": True},
        }
        self._configure_run_defaults()

        self.tester.run()

        # capture_and_save should be called (before + after per step)
        self.tester.screen_capture.capture_and_save.assert_called()

    @patch("main.time.sleep")
    def test_run_no_screenshots_when_disabled(self, mock_sleep):
        """When save_screenshots is False, capture_and_save should not be called."""
        _reset_mock_classes()
        cfg = _make_mock_config(max_steps=1, save_screenshots=False)
        tester = GameAutoTester(cfg)
        tester.window_manager.wait_for_window.return_value = self.fake_window

        mock_da = MagicMock()
        MockDecisionAgent.return_value = mock_da
        mock_da.decide.return_value = {
            "action": {"action": "done", "success": True},
        }
        mock_da.validate_action.return_value = True
        tester.screen_capture.capture.return_value = "img"

        tester.run()

        tester.screen_capture.capture_and_save.assert_not_called()

    # ---- reasoning is logged ----

    @patch("main.time.sleep")
    def test_run_logs_reasoning(self, mock_sleep):
        """Reasoning from decision_result should be logged."""
        self._mock_decision_agent.decide.side_effect = [
            {
                "reasoning": "I should click the button",
                "action": {"action": "done", "success": True},
            },
        ]
        self._configure_run_defaults()

        with patch.object(self.tester.logger, "info") as mock_info:
            self.tester.run()
            mock_info.assert_any_call("AI推理: I should click the button")


# ===================================================================
# Test: GameAutoTester.cleanup
# ===================================================================
class TestGameAutoTesterCleanup(unittest.TestCase):
    """Tests for GameAutoTester.cleanup."""

    def setUp(self):
        _reset_mock_classes()
        self.cfg = _make_mock_config()
        self.tester = GameAutoTester(self.cfg)

    def test_cleanup_saves_record_and_closes_running_game(self):
        """cleanup should save test record, close a running game, and close GLM client."""
        self.tester.game_launcher.is_running.return_value = True
        self.tester.glm_client.close = MagicMock()

        self.tester.cleanup()

        self.tester.state_memory.save_to_file.assert_called_once_with(
            "logs/test_record.json"
        )
        self.tester.state_memory.get_summary.assert_called_once()
        self.tester.game_launcher.is_running.assert_called_once()
        self.tester.game_launcher.close.assert_called_once_with(force=True)
        self.tester.glm_client.close.assert_called_once()

    def test_cleanup_does_not_close_game_if_not_running(self):
        """cleanup should not try to close the game if it is not running."""
        self.tester.game_launcher.is_running.return_value = False
        self.tester.glm_client.close = MagicMock()

        self.tester.cleanup()

        self.tester.game_launcher.close.assert_not_called()

    def test_cleanup_partial_glm_client_no_close_method(self):
        """cleanup should handle GLM client that lacks close method gracefully."""
        self.tester.game_launcher.is_running.return_value = False
        # Remove the close attribute to simulate partial cleanup
        del self.tester.glm_client.close

        # Should not raise
        self.tester.cleanup()

        self.tester.state_memory.save_to_file.assert_called_once_with(
            "logs/test_record.json"
        )

    def test_cleanup_summary_is_logged(self):
        """cleanup should log the test summary."""
        self.tester.game_launcher.is_running.return_value = False
        self.tester.state_memory.get_summary.return_value = {"steps": 5, "passed": 3}

        with patch.object(self.tester.logger, "info") as mock_info:
            self.tester.cleanup()
            mock_info.assert_any_call("测试摘要: {'steps': 5, 'passed': 3}")


# ===================================================================
# Test: main() function
# ===================================================================
class TestMainFunction(unittest.TestCase):
    """Tests for the top-level main() entry point."""

    @patch("main.GameAutoTester")
    @patch("main.setup_logging")
    @patch("main.Config")
    def test_main_loads_config_and_runs(self, mock_config_cls, mock_setup_log, mock_tester_cls):
        """main() should load config, set up logging, create tester, and run."""
        mock_cfg = MagicMock()
        mock_config_cls.from_env.return_value = mock_cfg
        mock_tester_instance = MagicMock()
        mock_tester_cls.return_value = mock_tester_instance

        with patch("sys.argv", ["main.py"]):
            app_main()

        mock_config_cls.from_env.assert_called_once()
        mock_cfg.validate.assert_called_once()
        mock_setup_log.assert_called_once_with(mock_cfg.log_level)
        mock_tester_cls.assert_called_once_with(mock_cfg)
        mock_tester_instance.run.assert_called_once()

    @patch("main.GameAutoTester")
    @patch("main.setup_logging")
    @patch("main.Config")
    def test_main_passes_config_path(self, mock_config_cls, mock_setup_log, mock_tester_cls):
        """main() should pass the --config arg to Config.from_env."""
        mock_cfg = MagicMock()
        mock_config_cls.from_env.return_value = mock_cfg

        with patch("sys.argv", ["main.py", "--config", "my_config.env"]):
            app_main()

        mock_config_cls.from_env.assert_called_once_with("my_config.env")

    @patch("main.GameAutoTester")
    @patch("main.setup_logging")
    @patch("main.Config")
    def test_main_default_config_path(self, mock_config_cls, mock_setup_log, mock_tester_cls):
        """main() should default to .env for config path."""
        mock_cfg = MagicMock()
        mock_config_cls.from_env.return_value = mock_cfg

        with patch("sys.argv", ["main.py"]):
            app_main()

        mock_config_cls.from_env.assert_called_once_with(".env")


if __name__ == "__main__":
    unittest.main()
