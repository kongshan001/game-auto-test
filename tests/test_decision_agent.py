"""测试决策Agent"""
import pytest
from unittest.mock import Mock, MagicMock
import json
from PIL import Image


class TestDecisionAgent:
    """DecisionAgent测试"""
    
    @pytest.fixture
    def mock_glm_client(self):
        """创建mock的GLM客户端"""
        client = Mock()
        client.chat_with_image = Mock(return_value='{"action": "click", "target": "按钮"}')
        return client
    
    @pytest.fixture
    def mock_state_memory(self):
        """创建mock的状态记忆"""
        memory = Mock()
        memory.test_goal = "测试登录"
        memory.get_history_prompt = Mock(return_value="步骤1: 点击登录")
        memory.actions = []  # 真实列表
        memory.start_time = None
        return memory
    
    @pytest.fixture
    def decision_agent(self, mock_glm_client, mock_state_memory):
        """创建决策Agent实例"""
        from src.agents.decision_agent import DecisionAgent
        return DecisionAgent(
            glm_client=mock_glm_client,
            test_case="测试登录",
            state_memory=mock_state_memory,
            use_react=False
        )
    
    def test_init(self, decision_agent, mock_glm_client, mock_state_memory):
        """测试初始化"""
        assert decision_agent.glm_client == mock_glm_client
        assert decision_agent.test_case == "测试登录"
        assert decision_agent.state_memory == mock_state_memory
        assert decision_agent.use_react is False
        assert decision_agent.max_retry_same_action == 3
    
    def test_init_with_custom_params(self, mock_glm_client, mock_state_memory):
        """测试自定义参数初始化"""
        from src.agents.decision_agent import DecisionAgent
        
        agent = DecisionAgent(
            glm_client=mock_glm_client,
            test_case="测试",
            state_memory=mock_state_memory,
            use_react=True,
            max_retry_same_action=5
        )
        
        assert agent.use_react is True
        assert agent.max_retry_same_action == 5
    
    def test_action_count_tracking(self, mock_glm_client, mock_state_memory):
        """测试动作计数"""
        from src.agents.decision_agent import DecisionAgent
        
        agent = DecisionAgent(
            glm_client=mock_glm_client,
            test_case="测试",
            state_memory=mock_state_memory
        )
        
        agent._increment_action("click", "按钮")
        agent._increment_action("click", "按钮")
        
        assert agent._get_action_count("click", "按钮") == 2
        assert agent._get_action_count("click", "其他") == 0
    
    def test_should_retry(self, mock_glm_client, mock_state_memory):
        """测试重试判断"""
        from src.agents.decision_agent import DecisionAgent
        
        agent = DecisionAgent(
            glm_client=mock_glm_client,
            test_case="测试",
            state_memory=mock_state_memory,
            max_retry_same_action=2
        )
        
        agent._increment_action("click", "按钮")
        agent._increment_action("click", "按钮")
        
        # 第三次应该返回False
        assert agent._should_retry({"action": "click", "target": "按钮"}) is False
        # 新动作应该允许重试
        assert agent._should_retry({"action": "click", "target": "新按钮"}) is True
    
    def test_reset_action_counts(self, mock_glm_client, mock_state_memory):
        """测试重置计数"""
        from src.agents.decision_agent import DecisionAgent
        
        agent = DecisionAgent(
            glm_client=mock_glm_client,
            test_case="测试",
            state_memory=mock_state_memory
        )
        
        agent._increment_action("click", "按钮")
        agent._reset_action_counts()
        
        assert agent._get_action_count("click", "按钮") == 0
    
    def test_build_history_context_empty(self):
        """测试空历史"""
        from src.agents.decision_agent import DecisionAgent
        
        # 使用真实的StateMemory
        from src.agents.state_memory import StateMemory
        memory = StateMemory()
        memory.set_test_case("测试")
        
        mock_client = Mock()
        
        agent = DecisionAgent(
            glm_client=mock_client,
            test_case="测试",
            state_memory=memory,
            use_react=False
        )
        
        context = agent._build_history_context()
        assert "暂无历史动作" in context
    
    def test_extract_json_valid(self):
        """测试提取有效JSON"""
        from src.agents.decision_agent import DecisionAgent
        
        # 需要实例
        mock_client = Mock()
        mock_memory = Mock()
        mock_memory.test_goal = "测试"
        mock_memory.get_history_prompt = Mock(return_value="")
        mock_memory.actions = []
        mock_memory.start_time = None
        
        agent = DecisionAgent(mock_client, "测试", mock_memory)
        
        result = agent._extract_json('{"action": "click", "target": "按钮"}')
        assert result["action"] == "click"
    
    def test_extract_json_with_reasoning(self):
        """测试提取带推理的JSON"""
        from src.agents.decision_agent import DecisionAgent
        
        mock_client = Mock()
        mock_memory = Mock()
        mock_memory.test_goal = "测试"
        mock_memory.get_history_prompt = Mock(return_value="")
        mock_memory.actions = []
        mock_memory.start_time = None
        
        agent = DecisionAgent(mock_client, "测试", mock_memory)
        
        # 测试包含reasoning的格式
        result = agent._parse_response_with_reasoning(
            '{"reasoning": "分析", "action": {"action": "wait", "seconds": 2}}'
        )
        assert "reasoning" in result
        assert "action" in result
    
    def test_parse_action_only(self):
        """测试仅解析动作"""
        from src.agents.decision_agent import DecisionAgent
        
        mock_client = Mock()
        mock_memory = Mock()
        mock_memory.test_goal = "测试"
        mock_memory.get_history_prompt = Mock(return_value="")
        mock_memory.actions = []
        mock_memory.start_time = None
        
        agent = DecisionAgent(mock_client, "测试", mock_memory)
        
        # 测试检测完成
        action = agent._parse_action_only("测试完成")
        assert action["action"] == "done"
    
    def test_validate_action_valid(self, decision_agent):
        """测试验证有效动作"""
        assert decision_agent.validate_action({"action": "click", "target": "按钮"})
        assert decision_agent.validate_action({"action": "wait", "seconds": 1})
        assert decision_agent.validate_action({"action": "done", "success": True})
    
    def test_validate_action_missing_action(self, decision_agent):
        """测试验证缺少action"""
        assert not decision_agent.validate_action({"target": "按钮"})
    
    def test_validate_action_invalid_type(self, decision_agent):
        """测试验证无效动作类型"""
        assert not decision_agent.validate_action({"action": "invalid"})
    
    def test_validate_action_click_missing_target(self, decision_agent):
        """测试验证click缺少target"""
        assert not decision_agent.validate_action({"action": "click"})
    
    def test_validate_action_type_missing_fields(self, decision_agent):
        """测试验证type缺少字段"""
        assert not decision_agent.validate_action({"action": "type", "target": "输入框"})
        assert not decision_agent.validate_action({"action": "type", "text": "hello"})
    
    def test_validate_action_non_dict(self, decision_agent):
        """测试验证非字典输入"""
        assert not decision_agent.validate_action("click")
        assert not decision_agent.validate_action(None)
