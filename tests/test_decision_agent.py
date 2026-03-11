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
        return memory
    
    @pytest.fixture
    def decision_agent(self, mock_glm_client, mock_state_memory):
        """创建决策Agent实例"""
        from src.agents.decision_agent import DecisionAgent
        return DecisionAgent(
            glm_client=mock_glm_client,
            test_case="测试登录",
            state_memory=mock_state_memory
        )
    
    def test_init(self, decision_agent, mock_glm_client, mock_state_memory):
        """测试初始化"""
        assert decision_agent.glm_client == mock_glm_client
        assert decision_agent.test_case == "测试登录"
        assert decision_agent.state_memory == mock_state_memory
    
    def test_decide_success(self, decision_agent, mock_glm_client):
        """测试决策成功"""
        mock_glm_client.chat_with_image.return_value = '{"action": "click", "target": "登录按钮"}'
        
        img = Image.new('RGB', (100, 100))
        action = decision_agent.decide(img)
        
        assert action["action"] == "click"
        assert action["target"] == "登录按钮"
    
    def test_decide_with_scene_description(self, decision_agent, mock_glm_client):
        """测试带场景描述的决策"""
        mock_glm_client.chat_with_image.return_value = '{"action": "wait", "seconds": 2}'
        
        img = Image.new('RGB', (100, 100))
        action = decision_agent.decide(img, scene_description="登录界面")
        
        assert action["action"] == "wait"
        mock_glm_client.chat_with_image.assert_called_once()
    
    def test_decide_glm_exception(self, decision_agent, mock_glm_client):
        """测试GLM调用异常"""
        mock_glm_client.chat_with_image.side_effect = Exception("API错误")
        
        img = Image.new('RGB', (100, 100))
        action = decision_agent.decide(img)
        
        assert action["action"] == "wait"
        assert "error" in action
    
    def test_parse_response_valid_json(self, decision_agent):
        """测试解析有效JSON"""
        response = '{"action": "click", "target": "按钮"}'
        action = decision_agent._parse_response(response)
        
        assert action["action"] == "click"
        assert action["target"] == "按钮"
    
    def test_parse_response_nested_json(self, decision_agent):
        """测试解析嵌套JSON"""
        response = '这里有一些文本 {"action": "type", "target": "输入框", "text": "test"} 更多文本'
        action = decision_agent._parse_response(response)
        
        assert action["action"] == "type"
    
    def test_parse_response_empty(self, decision_agent):
        """测试解析空响应"""
        action = decision_agent._parse_response("")
        
        assert action["action"] == "wait"
    
    def test_parse_response_invalid_json(self, decision_agent):
        """测试解析无效JSON"""
        response = '这不是有效的JSON'
        action = decision_agent._parse_response(response)
        
        assert action["action"] == "wait"
    
    def test_parse_text_action_done(self, decision_agent):
        """测试解析文本动作-完成"""
        action = decision_agent._parse_text_action("测试完成")
        
        assert action["action"] == "done"
        assert action["success"] is True
    
    def test_parse_text_action_wait(self, decision_agent):
        """测试解析文本动作-等待"""
        action = decision_agent._parse_text_action("等待5秒")
        
        assert action["action"] == "wait"
        assert action["seconds"] == 5
    
    def test_parse_text_action_click(self, decision_agent):
        """测试解析文本动作-点击"""
        action = decision_agent._parse_text_action('点击"开始按钮"')
        
        assert action["action"] == "click"
    
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
    
    def test_validate_action_keypress_missing_key(self, decision_agent):
        """测试验证keypress缺少key"""
        assert not decision_agent.validate_action({"action": "keypress"})
    
    def test_validate_action_assert_missing_condition(self, decision_agent):
        """测试验证assert缺少condition"""
        assert not decision_agent.validate_action({"action": "assert"})
    
    def test_validate_action_wait_defaults_seconds(self, decision_agent):
        """测试验证wait提供默认seconds"""
        action = {"action": "wait"}
        assert decision_agent.validate_action(action)
        assert action["seconds"] == 1
    
    def test_validate_action_non_dict(self, decision_agent):
        """测试验证非字典输入"""
        assert not decision_agent.validate_action("click")
        assert not decision_agent.validate_action(None)
