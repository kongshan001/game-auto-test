"""Tests for src.agents.state_memory — unittest suite."""
import unittest
import json
import time
import os
import tempfile

import sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', '..'))

from src.agents.state_memory import StateMemory, ActionRecord


class TestActionRecord(unittest.TestCase):
    """Tests for ActionRecord dataclass."""

    def test_init_defaults(self):
        record = ActionRecord(step=1, action="click", target="按钮", description="点击")
        self.assertEqual(record.step, 1)
        self.assertEqual(record.action, "click")
        self.assertEqual(record.target, "按钮")
        self.assertEqual(record.description, "点击")
        self.assertTrue(record.success)
        self.assertIsNone(record.error)
        self.assertIsNone(record.screenshot_path)
        self.assertIsInstance(record.timestamp, float)

    def test_init_custom_values(self):
        record = ActionRecord(
            step=5,
            action="type",
            target="input",
            description="typing",
            success=False,
            error="not found",
            screenshot_path="/tmp/shot.png",
        )
        self.assertEqual(record.step, 5)
        self.assertFalse(record.success)
        self.assertEqual(record.error, "not found")
        self.assertEqual(record.screenshot_path, "/tmp/shot.png")

    def test_to_dict(self):
        record = ActionRecord(step=1, action="click", target="btn", description="click btn")
        d = record.to_dict()
        self.assertIsInstance(d, dict)
        self.assertEqual(d["step"], 1)
        self.assertEqual(d["action"], "click")
        self.assertEqual(d["target"], "btn")
        self.assertEqual(d["description"], "click btn")
        self.assertIn("timestamp", d)
        self.assertIn("success", d)
        self.assertIn("error", d)
        self.assertIn("screenshot_path", d)

    def test_to_prompt_text(self):
        record = ActionRecord(step=3, action="click", target="登录按钮", description="点击登录")
        text = record.to_prompt_text()
        self.assertIn("步骤3", text)
        self.assertIn("click", text)
        self.assertIn("登录按钮", text)
        self.assertIn("点击登录", text)

    def test_to_prompt_text_format(self):
        record = ActionRecord(step=1, action="wait", target="页面加载", description="等待")
        text = record.to_prompt_text()
        self.assertTrue(text.startswith("步骤1:"))


class TestStateMemoryInit(unittest.TestCase):
    """Tests for StateMemory initialization."""

    def test_init_defaults(self):
        mem = StateMemory()
        self.assertEqual(mem.max_history, 20)
        self.assertEqual(len(mem.actions), 0)
        self.assertEqual(mem.test_case, "")
        self.assertEqual(mem.test_goal, "")
        self.assertIsNone(mem.start_time)
        self.assertIsNone(mem.end_time)

    def test_init_custom_max_history(self):
        mem = StateMemory(max_history=50)
        self.assertEqual(mem.max_history, 50)


class TestSetTestCase(unittest.TestCase):
    """Tests for set_test_case."""

    def test_set_test_case(self):
        mem = StateMemory()
        mem.set_test_case("测试登录：输入账号，点击登录，验证成功")
        self.assertEqual(mem.test_case, "测试登录：输入账号，点击登录，验证成功")

    def test_goal_extracted_from_verify(self):
        mem = StateMemory()
        mem.set_test_case("测试登录，验证进入主界面")
        self.assertIn("主界面", mem.test_goal)

    def test_goal_extracted_from_check(self):
        mem = StateMemory()
        mem.set_test_case("测试按钮，检查是否可用")
        self.assertIn("是否可用", mem.test_goal)

    def test_goal_extracted_from_confirm(self):
        mem = StateMemory()
        mem.set_test_case("执行操作，确认结果正确")
        self.assertIn("结果正确", mem.test_goal)

    def test_goal_no_keyword_returns_full(self):
        mem = StateMemory()
        mem.set_test_case("执行游戏任务")
        self.assertEqual(mem.test_goal, "执行游戏任务")

    def test_goal_empty_string(self):
        mem = StateMemory()
        mem.set_test_case("")
        self.assertEqual(mem.test_goal, "")


class TestAddAction(unittest.TestCase):
    """Tests for add_action."""

    def test_add_single_action(self):
        mem = StateMemory()
        mem.add_action("click", "按钮", "点击按钮")
        self.assertEqual(len(mem.actions), 1)
        self.assertEqual(mem.actions[0].action, "click")
        self.assertEqual(mem.actions[0].target, "按钮")
        self.assertEqual(mem.actions[0].step, 1)

    def test_add_multiple_actions_increment_step(self):
        mem = StateMemory()
        mem.add_action("click", "按钮1", "点击1")
        mem.add_action("type", "输入框", "输入")
        mem.add_action("wait", "页面", "等待")
        self.assertEqual(len(mem.actions), 3)
        self.assertEqual(mem.actions[0].step, 1)
        self.assertEqual(mem.actions[1].step, 2)
        self.assertEqual(mem.actions[2].step, 3)

    def test_add_action_with_error(self):
        mem = StateMemory()
        mem.add_action("click", "按钮", "失败", success=False, error="未找到")
        self.assertFalse(mem.actions[0].success)
        self.assertEqual(mem.actions[0].error, "未找到")

    def test_add_action_default_success(self):
        mem = StateMemory()
        mem.add_action("click", "按钮", "成功")
        self.assertTrue(mem.actions[0].success)
        self.assertIsNone(mem.actions[0].error)

    def test_max_history_limit(self):
        mem = StateMemory(max_history=3)
        for i in range(5):
            mem.add_action("click", f"按钮{i}", f"点击{i}")
        self.assertEqual(len(mem.actions), 3)
        self.assertEqual(mem.actions[0].target, "按钮2")
        self.assertEqual(mem.actions[2].target, "按钮4")

    def test_max_history_keeps_latest(self):
        mem = StateMemory(max_history=5)
        for i in range(10):
            mem.add_action("click", f"btn{i}", f"click{i}")
        self.assertEqual(len(mem.actions), 5)
        self.assertEqual(mem.actions[0].target, "btn5")
        self.assertEqual(mem.actions[4].target, "btn9")


class TestGetRecentActions(unittest.TestCase):
    """Tests for get_recent_actions."""

    def test_get_recent_fewer_than_n(self):
        mem = StateMemory()
        mem.add_action("click", "btn1", "click1")
        mem.add_action("click", "btn2", "click2")
        recent = mem.get_recent_actions(5)
        self.assertEqual(len(recent), 2)

    def test_get_recent_exactly_n(self):
        mem = StateMemory()
        for i in range(3):
            mem.add_action("click", f"btn{i}", f"click{i}")
        recent = mem.get_recent_actions(3)
        self.assertEqual(len(recent), 3)

    def test_get_recent_more_than_n(self):
        mem = StateMemory()
        for i in range(10):
            mem.add_action("click", f"btn{i}", f"click{i}")
        recent = mem.get_recent_actions(3)
        self.assertEqual(len(recent), 3)
        self.assertEqual(recent[0].target, "btn7")
        self.assertEqual(recent[2].target, "btn9")

    def test_get_recent_empty(self):
        mem = StateMemory()
        recent = mem.get_recent_actions(5)
        self.assertEqual(len(recent), 0)


class TestGetHistoryPrompt(unittest.TestCase):
    """Tests for get_history_prompt."""

    def test_with_actions(self):
        mem = StateMemory()
        mem.add_action("click", "btn1", "点击1")
        mem.add_action("type", "input", "输入")
        prompt = mem.get_history_prompt(2)
        self.assertIn("步骤1", prompt)
        self.assertIn("步骤2", prompt)
        self.assertIn("click", prompt)
        self.assertIn("type", prompt)

    def test_empty_history(self):
        mem = StateMemory()
        prompt = mem.get_history_prompt()
        self.assertIn("暂无历史动作", prompt)

    def test_n_parameter(self):
        mem = StateMemory()
        for i in range(5):
            mem.add_action("click", f"btn{i}", f"click{i}")
        prompt = mem.get_history_prompt(2)
        self.assertIn("步骤4", prompt)
        self.assertIn("步骤5", prompt)
        self.assertNotIn("步骤1", prompt)


class TestStartEndTest(unittest.TestCase):
    """Tests for start_test, end_test, get_duration, is_completed."""

    def test_start_test(self):
        mem = StateMemory()
        mem.start_test()
        self.assertIsNotNone(mem.start_time)

    def test_end_test(self):
        mem = StateMemory()
        mem.start_test()
        mem.end_test(success=True)
        self.assertIsNotNone(mem.end_time)
        self.assertTrue(mem.is_completed())

    def test_is_completed_before_start(self):
        mem = StateMemory()
        self.assertFalse(mem.is_completed())

    def test_is_completed_after_start_not_ended(self):
        mem = StateMemory()
        mem.start_test()
        self.assertFalse(mem.is_completed())

    def test_get_duration_running(self):
        mem = StateMemory()
        mem.start_test()
        time.sleep(0.05)
        duration = mem.get_duration()
        self.assertIsNotNone(duration)
        self.assertGreater(duration, 0)

    def test_get_duration_after_end(self):
        mem = StateMemory()
        mem.start_test()
        time.sleep(0.05)
        mem.end_test()
        duration = mem.get_duration()
        self.assertIsNotNone(duration)
        self.assertGreaterEqual(duration, 0.05)

    def test_get_duration_before_start(self):
        mem = StateMemory()
        self.assertIsNone(mem.get_duration())


class TestGetSummary(unittest.TestCase):
    """Tests for get_summary."""

    def test_summary_fields(self):
        mem = StateMemory()
        mem.set_test_case("测试登录")
        mem.add_action("click", "btn", "click", success=True)
        mem.add_action("type", "input", "type", success=True)
        mem.add_action("click", "login", "click", success=False, error="timeout")
        mem.start_test()
        mem.end_test(success=True)

        summary = mem.get_summary()
        self.assertEqual(summary["test_case"], "测试登录")
        self.assertEqual(summary["total_steps"], 3)
        self.assertEqual(summary["success_steps"], 2)
        self.assertEqual(summary["failed_steps"], 1)
        self.assertTrue(summary["completed"])
        self.assertIsNotNone(summary["duration"])

    def test_summary_empty(self):
        mem = StateMemory()
        summary = mem.get_summary()
        self.assertEqual(summary["total_steps"], 0)
        self.assertEqual(summary["success_steps"], 0)
        self.assertEqual(summary["failed_steps"], 0)
        self.assertFalse(summary["completed"])


class TestSerialization(unittest.TestCase):
    """Tests for to_json and save_to_file."""

    def test_to_json(self):
        mem = StateMemory()
        mem.set_test_case("测试")
        mem.add_action("click", "btn", "点击")
        json_str = mem.to_json()
        self.assertIsInstance(json_str, str)
        data = json.loads(json_str)
        self.assertEqual(data["test_case"], "测试")
        self.assertEqual(len(data["actions"]), 1)
        self.assertIn("test_goal", data)

    def test_to_json_chinese(self):
        mem = StateMemory()
        mem.set_test_case("测试中文内容验证")
        json_str = mem.to_json()
        self.assertIn("测试中文内容", json_str)

    def test_save_to_file(self):
        mem = StateMemory()
        mem.set_test_case("测试保存")
        mem.add_action("click", "btn", "点击")

        with tempfile.TemporaryDirectory() as tmpdir:
            filepath = os.path.join(tmpdir, "test_output.json")
            mem.save_to_file(filepath)
            self.assertTrue(os.path.exists(filepath))
            with open(filepath, "r", encoding="utf-8") as f:
                content = f.read()
            self.assertIn("测试保存", content)
            self.assertIn("click", content)

    def test_save_to_file_json_valid(self):
        mem = StateMemory()
        mem.set_test_case("测试")
        mem.add_action("wait", "page", "等待")

        with tempfile.TemporaryDirectory() as tmpdir:
            filepath = os.path.join(tmpdir, "valid.json")
            mem.save_to_file(filepath)
            with open(filepath, "r", encoding="utf-8") as f:
                data = json.load(f)
            self.assertEqual(data["test_case"], "测试")
            self.assertEqual(len(data["actions"]), 1)


if __name__ == '__main__':
    unittest.main()
