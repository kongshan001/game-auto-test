"""测试状态记忆"""
import pytest
import time
from src.agents.state_memory import StateMemory, ActionRecord


class TestActionRecord:
    """ActionRecord测试"""
    
    def test_init(self):
        """测试初始化"""
        record = ActionRecord(
            step=1,
            action="click",
            target="按钮",
            description="点击按钮"
        )
        
        assert record.step == 1
        assert record.action == "click"
        assert record.target == "按钮"
        assert record.description == "点击按钮"
        assert record.success is True
        assert record.error is None
    
    def test_to_dict(self):
        """测试转换为字典"""
        record = ActionRecord(
            step=1,
            action="click",
            target="按钮",
            description="点击"
        )
        
        d = record.to_dict()
        assert isinstance(d, dict)
        assert d["step"] == 1
        assert d["action"] == "click"
    
    def test_to_prompt_text(self):
        """测试转换为Prompt文本"""
        record = ActionRecord(
            step=1,
            action="click",
            target="按钮",
            description="点击"
        )
        
        text = record.to_prompt_text()
        assert "步骤1" in text
        assert "click" in text
        assert "按钮" in text


class TestStateMemory:
    """StateMemory测试"""
    
    def test_init(self):
        """测试初始化"""
        memory = StateMemory()
        assert memory.max_history == 20
        assert len(memory.actions) == 0
        assert memory.test_case == ""
    
    def test_init_custom_max_history(self):
        """测试自定义历史长度"""
        memory = StateMemory(max_history=10)
        assert memory.max_history == 10
    
    def test_set_test_case(self):
        """测试设置测试用例"""
        memory = StateMemory()
        memory.set_test_case("测试登录：输入账号，点击登录，验证成功")
        
        assert memory.test_case == "测试登录：输入账号，点击登录，验证成功"
        assert memory.test_goal != ""
    
    def test_extract_goal_with_verify(self):
        """测试提取验证目标"""
        memory = StateMemory()
        memory.set_test_case("测试登录：输入账号，点击登录，验证进入主界面")
        
        assert "主界面" in memory.test_goal
    
    def test_add_action(self):
        """测试添加动作"""
        memory = StateMemory()
        memory.add_action("click", "按钮", "点击按钮")
        
        assert len(memory.actions) == 1
        assert memory.actions[0].action == "click"
        assert memory.actions[0].target == "按钮"
    
    def test_add_action_with_error(self):
        """测试添加失败动作"""
        memory = StateMemory()
        memory.add_action("click", "按钮", "点击失败", success=False, error="未找到")
        
        assert len(memory.actions) == 1
        assert memory.actions[0].success is False
        assert memory.actions[0].error == "未找到"
    
    def test_get_recent_actions(self):
        """测试获取最近动作"""
        memory = StateMemory()
        for i in range(10):
            memory.add_action("click", f"按钮{i}", f"点击{i}")
        
        recent = memory.get_recent_actions(3)
        assert len(recent) == 3
        assert recent[0].target == "按钮7"
    
    def test_get_recent_actions_less_than_n(self):
        """测试获取最近动作少于N条"""
        memory = StateMemory()
        memory.add_action("click", "按钮1", "点击1")
        memory.add_action("click", "按钮2", "点击2")
        
        recent = memory.get_recent_actions(5)
        assert len(recent) == 2
    
    def test_get_history_prompt(self):
        """测试获取历史Prompt"""
        memory = StateMemory()
        memory.add_action("click", "按钮1", "点击1")
        memory.add_action("type", "输入框", "输入hello")
        
        prompt = memory.get_history_prompt(2)
        assert "步骤1" in prompt
        assert "步骤2" in prompt
    
    def test_get_history_prompt_empty(self):
        """测试空历史"""
        memory = StateMemory()
        prompt = memory.get_history_prompt()
        
        assert "暂无历史动作" in prompt
    
    def test_start_test(self):
        """测试开始测试"""
        memory = StateMemory()
        memory.start_test()
        
        assert memory.start_time is not None
    
    def test_end_test(self):
        """测试结束测试"""
        memory = StateMemory()
        memory.start_test()
        time.sleep(0.1)
        memory.end_test(success=True)
        
        assert memory.end_time is not None
        assert memory.is_completed()
    
    def test_get_duration(self):
        """测试获取持续时间"""
        memory = StateMemory()
        memory.start_test()
        time.sleep(0.1)
        
        duration = memory.get_duration()
        assert duration is not None
        assert duration >= 0.1
    
    def test_get_duration_before_start(self):
        """测试未开始时获取持续时间"""
        memory = StateMemory()
        assert memory.get_duration() is None
    
    def test_get_summary(self):
        """测试获取摘要"""
        memory = StateMemory()
        memory.set_test_case("测试登录")
        memory.add_action("click", "按钮", "点击", success=True)
        memory.add_action("type", "输入框", "输入", success=True)
        memory.add_action("click", "登录", "点击", success=False)
        memory.start_test()
        time.sleep(0.1)
        memory.end_test(success=True)
        
        summary = memory.get_summary()
        
        assert summary["test_case"] == "测试登录"
        assert summary["total_steps"] == 3
        assert summary["success_steps"] == 2
        assert summary["failed_steps"] == 1
        assert summary["completed"] is True
        assert summary["duration"] is not None
    
    def test_max_history_limit(self):
        """测试历史记录限制"""
        memory = StateMemory(max_history=5)
        
        for i in range(10):
            memory.add_action("click", f"按钮{i}", f"点击{i}")
        
        assert len(memory.actions) == 5
        assert memory.actions[0].target == "按钮5"
    
    def test_to_json(self):
        """测试JSON序列化"""
        memory = StateMemory()
        memory.set_test_case("测试")
        memory.add_action("click", "按钮", "点击")
        memory.start_test()
        
        json_str = memory.to_json()
        
        assert isinstance(json_str, str)
        assert "测试" in json_str
        assert "click" in json_str
    
    def test_save_to_file(self, tmp_path):
        """测试保存到文件"""
        memory = StateMemory()
        memory.set_test_case("测试")
        memory.add_action("click", "按钮", "点击")
        
        filepath = tmp_path / "test.json"
        memory.save_to_file(str(filepath))
        
        assert filepath.exists()
        content = filepath.read_text()
        assert "测试" in content
