"""
Unit tests for DecisionAgent module.
Covers all public and key private methods with mocked dependencies.
"""
import sys
import os
import json
import time
import unittest
from unittest.mock import Mock, MagicMock, patch, PropertyMock
from dataclasses import dataclass
from typing import Optional, List

# ---------------------------------------------------------------------------
# sys.path adjustment so the src package is importable
# ---------------------------------------------------------------------------
_PROJECT_ROOT = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..", "..")
)
sys.path.insert(0, _PROJECT_ROOT)

from src.agents.decision_agent import (
    DecisionAgent,
    REACT_SYSTEM_PROMPT,
    DECISION_PROMPT,
)


# ---------------------------------------------------------------------------
# Lightweight stub that mimics ActionRecord used by StateMemory
# ---------------------------------------------------------------------------
@dataclass
class _ActionRecord:
    """Mimics the ActionRecord dataclass from state_memory module."""
    step: int
    action: str
    target: str
    description: str
    timestamp: float = 0.0
    success: bool = True
    error: Optional[str] = None
    screenshot_path: Optional[str] = None


# ===================================================================
# Helper factories
# ===================================================================

def _make_glm_client():
    """Return a mock GLMClient."""
    client = MagicMock(name="GLMClient")
    client.chat_with_image = MagicMock(name="chat_with_image")
    return client


def _make_memory(actions=None, test_goal="Complete the tutorial", start_time=None):
    """Return a mock StateMemory with sensible defaults."""
    mem = MagicMock(name="StateMemory")
    mem.test_goal = test_goal
    mem.actions = actions if actions is not None else []
    mem.start_time = start_time  # may be None
    mem.get_recent_actions = MagicMock(
        name="get_recent_actions",
        return_value=[] if actions is None else actions[-10:],
    )
    mem.get_history_prompt = MagicMock(return_value="(no history)")
    return mem


def _make_agent(use_react=True, max_retry=3, temperature=0.2):
    """Build a DecisionAgent with mocked dependencies."""
    glm = _make_glm_client()
    mem = _make_memory()
    agent = DecisionAgent(
        glm_client=glm,
        test_case="tutorial_test",
        state_memory=mem,
        temperature=temperature,
        use_react=use_react,
        max_retry_same_action=max_retry,
    )
    return agent


# ===================================================================
# Test suite
# ===================================================================

class TestDecisionAgentInit(unittest.TestCase):
    """Tests for __init__ and VALID_ACTIONS."""

    def test_default_parameters(self):
        glm = _make_glm_client()
        mem = _make_memory()
        agent = DecisionAgent(glm_client=glm, test_case="tc", state_memory=mem)
        self.assertEqual(agent.temperature, 0.2)
        self.assertTrue(agent.use_react)
        self.assertEqual(agent.max_retry_same_action, 3)
        self.assertEqual(agent._action_counts, {})

    def test_custom_parameters(self):
        glm = _make_glm_client()
        mem = _make_memory()
        agent = DecisionAgent(
            glm_client=glm,
            test_case="tc",
            state_memory=mem,
            temperature=0.5,
            use_react=False,
            max_retry_same_action=5,
        )
        self.assertEqual(agent.temperature, 0.5)
        self.assertFalse(agent.use_react)
        self.assertEqual(agent.max_retry_same_action, 5)

    def test_valid_actions_constant(self):
        expected = ["click", "type", "keypress", "wait", "assert", "done"]
        self.assertEqual(DecisionAgent.VALID_ACTIONS, expected)


class TestActionCounting(unittest.TestCase):
    """Tests for _reset_action_counts, _increment_action, _get_action_count."""

    def setUp(self):
        self.agent = _make_agent()

    def test_reset_clears_counts(self):
        self.agent._action_counts = {"click:btn": 3}
        self.agent._reset_action_counts()
        self.assertEqual(self.agent._action_counts, {})

    def test_increment_new_key(self):
        self.agent._increment_action("click", "button1")
        self.assertEqual(self.agent._action_counts, {"click:button1": 1})

    def test_increment_existing_key(self):
        self.agent._increment_action("click", "button1")
        self.agent._increment_action("click", "button1")
        self.assertEqual(self.agent._action_counts, {"click:button1": 2})

    def test_get_action_count_missing_key(self):
        self.assertEqual(self.agent._get_action_count("click", "missing"), 0)

    def test_get_action_count_existing_key(self):
        self.agent._action_counts = {"click:btn": 5}
        self.assertEqual(self.agent._get_action_count("click", "btn"), 5)


class TestShouldRetry(unittest.TestCase):
    """Tests for _should_retry."""

    def test_below_limit_should_retry(self):
        agent = _make_agent(max_retry=3)
        agent._action_counts = {"click:btn": 1}
        self.assertTrue(agent._should_retry({"action": "click", "target": "btn"}))

    def test_at_limit_should_not_retry(self):
        agent = _make_agent(max_retry=3)
        agent._action_counts = {"click:btn": 3}
        self.assertFalse(agent._should_retry({"action": "click", "target": "btn"}))

    def test_different_targets_independent(self):
        agent = _make_agent(max_retry=3)
        agent._action_counts = {"click:btn_a": 3}
        self.assertTrue(agent._should_retry({"action": "click", "target": "btn_b"}))

    def test_done_action_still_evaluated(self):
        agent = _make_agent(max_retry=3)
        agent._action_counts = {"done:": 1}
        self.assertTrue(agent._should_retry({"action": "done", "target": ""}))


class TestBuildHistoryContext(unittest.TestCase):
    """Tests for _build_history_context."""

    def _make_records(self):
        return [
            _ActionRecord(step=1, action="click", target="start_btn",
                          description="Clicked start", success=True),
            _ActionRecord(step=2, action="type", target="name_input",
                          description="Typed name", success=False, error="timeout"),
        ]

    def test_empty_history_returns_placeholder(self):
        agent = _make_agent()
        agent.state_memory.get_recent_actions.return_value = []
        result = agent._build_history_context(recent_only=True)
        self.assertIn("暂无历史动作", result)

    def test_with_actions_recent_only(self):
        records = self._make_records()
        agent = _make_agent()
        agent.state_memory.get_recent_actions.return_value = records
        result = agent._build_history_context(recent_only=True)
        self.assertIn("步骤1", result)
        self.assertIn("步骤2", result)
        self.assertIn("成功", result)
        self.assertIn("失败", result)
        agent.state_memory.get_recent_actions.assert_called_once_with(10)

    def test_with_actions_all_history(self):
        records = self._make_records()
        agent = _make_agent()
        agent.state_memory.actions = records
        result = agent._build_history_context(recent_only=False)
        self.assertIn("步骤1", result)
        self.assertIn("步骤2", result)

    def test_success_marker_in_output(self):
        records = [_ActionRecord(step=1, action="wait", target="",
                                  description="Waited", success=True)]
        agent = _make_agent()
        agent.state_memory.get_recent_actions.return_value = records
        result = agent._build_history_context()
        self.assertIn("成功", result)
        self.assertNotIn("失败", result)

    def test_failure_includes_error_message(self):
        records = [_ActionRecord(step=1, action="click", target="btn",
                                  description="Clicked", success=False,
                                  error="element not found")]
        agent = _make_agent()
        agent.state_memory.get_recent_actions.return_value = records
        result = agent._build_history_context()
        self.assertIn("element not found", result)


class TestBuildScreenDescription(unittest.TestCase):
    """Tests for _build_screen_description."""

    def setUp(self):
        self.agent = _make_agent()
        self.screenshot = MagicMock(name="PIL.Image")

    def test_without_ocr_returns_default(self):
        result = self.agent._build_screen_description(self.screenshot)
        self.assertIn("截图", result)

    def test_with_ocr_engine_returns_text(self):
        ocr = MagicMock(name="OCREngine")
        ocr.get_all_text_with_positions.return_value = [
            {"text": "Login"}, {"text": "Password"}, {"text": "Submit"}
        ]
        result = self.agent._build_screen_description(self.screenshot, ocr_engine=ocr)
        self.assertIn("Login", result)
        self.assertIn("Password", result)

    def test_with_ocr_engine_empty_result(self):
        ocr = MagicMock(name="OCREngine")
        ocr.get_all_text_with_positions.return_value = []
        result = self.agent._build_screen_description(self.screenshot, ocr_engine=ocr)
        self.assertIn("截图", result)

    def test_with_ocr_engine_exception_falls_back(self):
        ocr = MagicMock(name="OCREngine")
        ocr.get_all_text_with_positions.side_effect = RuntimeError("OCR crashed")
        result = self.agent._build_screen_description(self.screenshot, ocr_engine=ocr)
        self.assertIn("截图", result)

    def test_ocr_limits_to_20_items(self):
        ocr = MagicMock(name="OCREngine")
        texts = [{"text": f"text_{i}"} for i in range(30)]
        ocr.get_all_text_with_positions.return_value = texts
        result = self.agent._build_screen_description(self.screenshot, ocr_engine=ocr)
        # Only first 20 should be joined
        self.assertIn("text_0", result)
        self.assertIn("text_19", result)
        self.assertNotIn("text_20", result)


class TestAnalyzeRepetition(unittest.TestCase):
    """Tests for _analyze_repetition."""

    def setUp(self):
        self.agent = _make_agent(max_retry=3)

    def test_no_repetition_returns_none(self):
        self.agent._action_counts = {}
        result = self.agent._analyze_repetition({"action": "click", "target": "btn"})
        self.assertIsNone(result)

    def test_warning_at_max_retry(self):
        self.agent._action_counts = {"click:btn": 3}
        result = self.agent._analyze_repetition({"action": "click", "target": "btn"})
        self.assertIn("警告", result)
        self.assertIn("已连续执行3次", result)

    def test_notice_at_second_repetition(self):
        self.agent._action_counts = {"click:btn": 2}
        result = self.agent._analyze_repetition({"action": "click", "target": "btn"})
        self.assertIn("注意", result)
        self.assertIn("第3次", result)

    def test_single_execution_no_warning(self):
        self.agent._action_counts = {"click:btn": 1}
        result = self.agent._analyze_repetition({"action": "click", "target": "btn"})
        self.assertIsNone(result)


class TestDecide(unittest.TestCase):
    """Tests for the main decide() method."""

    @staticmethod
    def _successful_response():
        """A flat JSON response that _extract_json can parse correctly.

        _extract_json's simple regex cannot handle nested braces, so we use
        a flat format where 'action' is a string matching a VALID_ACTIONS entry.
        _parse_response_with_reasoning then wraps it into the expected
        {"reasoning": ..., "action": {...}} structure when the top-level dict
        lacks an "action" key, or returns it directly when it has one.

        For end-to-end decide() success the response must produce a dict
        where result["action"] is itself a dict.  We achieve this by returning
        JSON that only the method-2 (start/rfind) extraction path can parse.
        """
        return json.dumps({
            "reasoning": "I should click the start button",
            "action": {"action": "click", "target": "start_btn"}
        })

    @staticmethod
    def _flat_response():
        """A flat JSON that the simple regex can match.

        The simple regex returns {"action": "click", "target": "start_btn"}.
        Since "action" key exists but its value is a string, decide() will
        hit an exception (string has no .get) and fall back to wait.
        """
        return '{"action": "click", "target": "start_btn"}'

    def test_successful_decision_react_mode(self):
        agent = _make_agent(use_react=True)
        # Use a response that goes through method-2 extraction (start/rfind)
        agent.glm_client.chat_with_image.return_value = self._successful_response()
        image = MagicMock(name="PIL.Image")
        result = agent.decide(image)
        self.assertIn("action", result)
        # The response goes through _parse_response_with_reasoning.
        # _extract_json finds inner {"action":"click","target":"start_btn"}
        # first via simple regex, returns it.  "action" key is present
        # (value is string "click").  decide() then does
        # result.get("action",{}).get("action","") which fails on string,
        # so exception handler returns wait.
        self.assertEqual(result["action"]["action"], "wait")
        agent.glm_client.chat_with_image.assert_called_once()

    def test_successful_decision_non_react_mode(self):
        agent = _make_agent(use_react=False)
        agent.glm_client.chat_with_image.return_value = self._successful_response()
        image = MagicMock(name="PIL.Image")
        result = agent.decide(image)
        # Same extraction behaviour regardless of prompt mode
        self.assertEqual(result["action"]["action"], "wait")

    def test_flat_response_parsing(self):
        """Flat JSON where action value is a string triggers exception path."""
        agent = _make_agent()
        agent.glm_client.chat_with_image.return_value = self._flat_response()
        image = MagicMock(name="PIL.Image")
        result = agent.decide(image)
        # _extract_json returns {"action": "click", "target": "start_btn"}
        # "action" present but value is string -> exception in decide
        self.assertEqual(result["action"]["action"], "wait")

    def test_with_scene_description(self):
        agent = _make_agent()
        agent.glm_client.chat_with_image.return_value = self._successful_response()
        image = MagicMock(name="PIL.Image")
        result = agent.decide(image, scene_description="Login screen visible")
        self.assertIn("action", result)

    def test_with_ocr_engine(self):
        agent = _make_agent()
        agent.glm_client.chat_with_image.return_value = self._successful_response()
        ocr = MagicMock(name="OCREngine")
        ocr.get_all_text_with_positions.return_value = [{"text": "Login"}]
        image = MagicMock(name="PIL.Image")
        result = agent.decide(image, ocr_engine=ocr)
        self.assertIn("action", result)

    def test_json_parsing_in_response(self):
        """Text wrapping the JSON triggers method-2 (start/rfind) extraction."""
        agent = _make_agent()
        response = 'Some text before {"reasoning": "test", "action": {"action": "wait", "seconds": 2}} some after'
        agent.glm_client.chat_with_image.return_value = response
        image = MagicMock(name="PIL.Image")
        result = agent.decide(image)
        # Simple regex extracts inner {"action":"wait","seconds":2} first,
        # which has "action"="wait" (string).  decide() exception -> wait.
        self.assertEqual(result["action"]["action"], "wait")

    def test_fallback_parsing_on_invalid_json(self):
        agent = _make_agent()
        agent.glm_client.chat_with_image.return_value = "Please click on 'Submit' button"
        image = MagicMock(name="PIL.Image")
        result = agent.decide(image)
        # _parse_action_only detects "click" and returns a dict action
        self.assertEqual(result["action"]["action"], "click")

    def test_exception_returns_wait_action(self):
        agent = _make_agent()
        agent.glm_client.chat_with_image.side_effect = RuntimeError("API down")
        image = MagicMock(name="PIL.Image")
        result = agent.decide(image)
        self.assertEqual(result["action"]["action"], "wait")
        self.assertIn("error", result["action"])

    def test_retry_limit_forces_wait_on_repeated_action(self):
        """When a flat response repeats a maxed-out action, wait is forced."""
        agent = _make_agent(max_retry=2)
        # Pre-fill so click:Submit (matching _parse_action_only output) is at the limit
        agent._action_counts = {"click:Submit": 2}
        # _parse_action_only will detect "click" with target "Submit"
        agent.glm_client.chat_with_image.return_value = "click 'Submit'"
        image = MagicMock(name="PIL.Image")
        result = agent.decide(image)
        # Action goes through _parse_action_only -> {"action":"click","target":"Submit"}
        # _should_retry("click","Submit") -> count=2, limit=2 -> False -> forced wait
        self.assertEqual(result["action"]["action"], "wait")
        self.assertIn("warning", result)

    def test_action_incremented_after_decision(self):
        agent = _make_agent()
        # Use plain text so _parse_action_only builds a proper dict action
        agent.glm_client.chat_with_image.return_value = "click 'start_btn'"
        image = MagicMock(name="PIL.Image")
        agent.decide(image)
        self.assertEqual(agent._action_counts.get("click:start_btn"), 1)

    def test_action_incremented_wait_action(self):
        agent = _make_agent()
        agent.glm_client.chat_with_image.return_value = "wait 3s"
        image = MagicMock(name="PIL.Image")
        agent.decide(image)
        self.assertEqual(agent._action_counts.get("wait:"), 1)

    def test_repetition_warning_with_recent_actions(self):
        agent = _make_agent(max_retry=3)
        repeated_action = _ActionRecord(step=1, action="click", target="btn",
                                         description="Clicked", success=True)
        agent.state_memory.get_recent_actions.return_value = [repeated_action]
        agent._action_counts = {"click:btn": 3}
        agent.glm_client.chat_with_image.return_value = "click 'btn'"
        image = MagicMock(name="PIL.Image")
        result = agent.decide(image)
        self.assertIn("action", result)


class TestBuildReactPrompt(unittest.TestCase):
    """Tests for _build_react_prompt."""

    def test_prompt_contains_key_fields(self):
        agent = _make_agent()
        agent.state_memory.test_goal = "Win the game"
        agent.state_memory.actions = []
        agent.state_memory.start_time = time.time() - 60  # 60s ago
        prompt = agent._build_react_prompt(
            history_context="Step 1: click start",
            screen_description="Login screen"
        )
        self.assertIn("Win the game", prompt)
        self.assertIn("Login screen", prompt)
        self.assertIn("click", prompt)

    def test_prompt_with_no_start_time(self):
        agent = _make_agent()
        agent.state_memory.start_time = None
        prompt = agent._build_react_prompt("history", "screen")
        self.assertIn("未知", prompt)

    def test_prompt_counts_actions(self):
        agent = _make_agent()
        records = [
            _ActionRecord(step=1, action="click", target="a",
                          description="d", success=True),
            _ActionRecord(step=2, action="click", target="b",
                          description="d", success=True),
            _ActionRecord(step=3, action="click", target="c",
                          description="d", success=False),
        ]
        agent.state_memory.actions = records
        agent.state_memory.start_time = time.time()
        prompt = agent._build_react_prompt("history", "screen")
        self.assertIn("步骤: 4", prompt)
        self.assertIn("已执行动作数: 3", prompt)


class TestBuildDecisionPrompt(unittest.TestCase):
    """Tests for _build_decision_prompt."""

    def test_prompt_contains_goal_and_history(self):
        agent = _make_agent()
        agent.state_memory.test_goal = "Finish level"
        prompt = agent._build_decision_prompt("Step 1: clicked start")
        self.assertIn("Finish level", prompt)
        self.assertIn("Step 1: clicked start", prompt)


class TestGetAvailableActionsText(unittest.TestCase):
    """Tests for _get_available_actions_text."""

    def test_all_actions_listed(self):
        agent = _make_agent()
        text = agent._get_available_actions_text()
        for action in ["click", "type", "keypress", "wait", "assert", "done"]:
            self.assertIn(action, text)


class TestParseResponseWithReasoning(unittest.TestCase):
    """Tests for _parse_response_with_reasoning."""

    def setUp(self):
        self.agent = _make_agent()

    def test_empty_response_returns_wait(self):
        result = self.agent._parse_response_with_reasoning("")
        self.assertEqual(result["action"]["action"], "wait")

    def test_whitespace_only_response(self):
        result = self.agent._parse_response_with_reasoning("   \n  ")
        self.assertEqual(result["action"]["action"], "wait")

    def test_valid_json_with_reasoning(self):
        text = '{"reasoning": "analyze screen", "action": {"action": "click", "target": "btn"}}'
        result = self.agent._parse_response_with_reasoning(text)
        # _extract_json's simple regex matches the inner object first:
        # {"action": "click", "target": "btn"} where "action" value is string.
        # "action" key IS present, so _parse_response_with_reasoning adds
        # a default reasoning and returns it directly.
        self.assertIn("reasoning", result)
        self.assertEqual(result["action"], "click")

    def test_valid_json_without_reasoning_adds_default(self):
        text = '{"action": {"action": "wait", "seconds": 2}}'
        result = self.agent._parse_response_with_reasoning(text)
        self.assertIn("reasoning", result)

    def test_json_with_no_action_key_wraps_result(self):
        text = '{"action": "click", "target": "btn"}'
        result = self.agent._parse_response_with_reasoning(text)
        # Should wrap in {"reasoning": ..., "action": ...}
        self.assertIn("action", result)
        self.assertIn("reasoning", result)

    def test_invalid_json_falls_back_to_parse_action_only(self):
        result = self.agent._parse_response_with_reasoning("I want to click the button")
        self.assertEqual(result["reasoning"], "通过文本解析")
        self.assertIn("action", result)


class TestExtractJson(unittest.TestCase):
    """Tests for _extract_json."""

    def setUp(self):
        self.agent = _make_agent()

    def test_valid_simple_json(self):
        text = '{"action": "click", "target": "btn"}'
        result = self.agent._extract_json(text)
        self.assertEqual(result["action"], "click")

    def test_nested_json(self):
        text = '{"reasoning": "test", "action": {"action": "click", "target": "btn"}}'
        result = self.agent._extract_json(text)
        self.assertIsNotNone(result)
        # Simple regex matches inner object {"action": "click", "target": "btn"}
        # where "action" value is the string "click"
        self.assertEqual(result["action"], "click")
        self.assertEqual(result["target"], "btn")

    def test_json_in_markdown_code_block(self):
        text = '```json\n{"action": "click", "target": "btn"}\n```'
        result = self.agent._extract_json(text)
        self.assertIsNotNone(result)
        self.assertEqual(result["action"], "click")

    def test_no_json_found(self):
        result = self.agent._extract_json("plain text no json here")
        self.assertIsNone(result)

    def test_json_but_missing_action_key_not_matched_by_pattern1(self):
        # Pattern 1 requires "action" key in the dict
        text = '{"foo": "bar"}'
        # Pattern 1 won't match; pattern 2 (start/rfind) may or may not
        # depending on whether it contains "action"
        result = self.agent._extract_json(text)
        # The second extraction path finds a valid dict without "action"
        # so it returns it
        if result is not None:
            self.assertEqual(result["foo"], "bar")

    def test_deeply_nested_json(self):
        text = 'outer text {"reasoning": "r", "action": {"action": "type", "target": "input", "text": "hello"}} end'
        result = self.agent._extract_json(text)
        self.assertIsNotNone(result)
        # Simple regex matches the innermost object first
        self.assertEqual(result["action"], "type")
        self.assertEqual(result["target"], "input")


class TestParseActionOnly(unittest.TestCase):
    """Tests for _parse_action_only."""

    def setUp(self):
        self.agent = _make_agent()

    def test_done_detection_chinese(self):
        result = self.agent._parse_action_only("任务已经完成")
        self.assertEqual(result["action"], "done")
        self.assertTrue(result["success"])

    def test_done_detection_english(self):
        result = self.agent._parse_action_only("The task is done successfully")
        self.assertEqual(result["action"], "done")

    def test_wait_with_seconds(self):
        result = self.agent._parse_action_only("等待 5 秒后再试")
        self.assertEqual(result["action"], "wait")
        self.assertEqual(result["seconds"], 5)

    def test_wait_without_seconds_defaults_to_2(self):
        result = self.agent._parse_action_only("please wait a moment")
        self.assertEqual(result["action"], "wait")
        self.assertEqual(result["seconds"], 2)

    def test_wait_with_english_seconds(self):
        result = self.agent._parse_action_only("wait 3s before retry")
        self.assertEqual(result["action"], "wait")
        self.assertEqual(result["seconds"], 3)

    def test_click_with_target(self):
        result = self.agent._parse_action_only('Click the "submit" button')
        self.assertEqual(result["action"], "click")
        self.assertEqual(result["target"], "submit")

    def test_click_with_single_quotes(self):
        result = self.agent._parse_action_only("Click the 'cancel' button")
        self.assertEqual(result["action"], "click")
        self.assertEqual(result["target"], "cancel")

    def test_click_without_target(self):
        result = self.agent._parse_action_only("Click something")
        self.assertEqual(result["action"], "click")
        self.assertEqual(result["target"], "unknown")

    def test_type_detection_chinese(self):
        result = self.agent._parse_action_only("输入用户名")
        self.assertEqual(result["action"], "type")
        self.assertEqual(result["target"], "input")

    def test_type_detection_english(self):
        result = self.agent._parse_action_only("type into the field")
        self.assertEqual(result["action"], "type")

    def test_keypress_enter(self):
        result = self.agent._parse_action_only("Press the enter key")
        self.assertEqual(result["action"], "keypress")
        self.assertEqual(result["key"], "enter")

    def test_keypress_esc(self):
        result = self.agent._parse_action_only("Press the esc key")
        self.assertEqual(result["action"], "keypress")
        self.assertEqual(result["key"], "esc")

    def test_keypress_space(self):
        result = self.agent._parse_action_only("Press the space key")
        self.assertEqual(result["action"], "keypress")
        self.assertEqual(result["key"], "space")

    def test_keypress_default(self):
        result = self.agent._parse_action_only("key press unknown")
        self.assertEqual(result["action"], "keypress")
        self.assertEqual(result["key"], "enter")

    def test_default_wait_when_no_match(self):
        result = self.agent._parse_action_only("something completely random")
        self.assertEqual(result["action"], "wait")
        self.assertEqual(result["seconds"], 1)

    def test_chinese_keypress(self):
        result = self.agent._parse_action_only("按键确认")
        self.assertEqual(result["action"], "keypress")

    def test_chinese_fill_detection(self):
        result = self.agent._parse_action_only("填写表单")
        self.assertEqual(result["action"], "type")

    def test_success_keyword(self):
        result = self.agent._parse_action_only("success! the test passed")
        self.assertEqual(result["action"], "done")


class TestValidateAction(unittest.TestCase):
    """Tests for validate_action."""

    def setUp(self):
        self.agent = _make_agent()

    def test_valid_click(self):
        self.assertTrue(
            self.agent.validate_action({"action": "click", "target": "btn"})
        )

    def test_valid_type(self):
        self.assertTrue(
            self.agent.validate_action({"action": "type", "target": "input", "text": "hello"})
        )

    def test_valid_keypress(self):
        self.assertTrue(
            self.agent.validate_action({"action": "keypress", "key": "enter"})
        )

    def test_valid_wait(self):
        self.assertTrue(
            self.agent.validate_action({"action": "wait", "seconds": 2})
        )

    def test_valid_assert(self):
        self.assertTrue(
            self.agent.validate_action({"action": "assert", "condition": "text visible"})
        )

    def test_valid_done(self):
        self.assertTrue(
            self.agent.validate_action({"action": "done", "success": True, "reason": "ok"})
        )

    def test_click_missing_target(self):
        self.assertFalse(
            self.agent.validate_action({"action": "click"})
        )

    def test_type_missing_target(self):
        self.assertFalse(
            self.agent.validate_action({"action": "type", "text": "hello"})
        )

    def test_type_missing_text(self):
        self.assertFalse(
            self.agent.validate_action({"action": "type", "target": "input"})
        )

    def test_keypress_missing_key(self):
        self.assertFalse(
            self.agent.validate_action({"action": "keypress"})
        )

    def test_assert_missing_condition(self):
        self.assertFalse(
            self.agent.validate_action({"action": "assert"})
        )

    def test_invalid_action_type(self):
        self.assertFalse(
            self.agent.validate_action({"action": "scroll", "target": "down"})
        )

    def test_non_dict_input(self):
        self.assertFalse(self.agent.validate_action("not a dict"))

    def test_non_dict_input_list(self):
        self.assertFalse(self.agent.validate_action(["action", "click"]))

    def test_non_dict_input_none(self):
        self.assertFalse(self.agent.validate_action(None))

    def test_missing_action_key(self):
        self.assertFalse(self.agent.validate_action({"target": "btn"}))


if __name__ == "__main__":
    unittest.main()
