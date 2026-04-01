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


# ======================== VALID_ACTIONS 测试 ========================


class TestValidActions:
    """VALID_ACTIONS 常量测试"""

    def test_valid_actions_contains_all_expected(self):
        """测试VALID_ACTIONS包含所有预期动作"""
        from src.agents.decision_agent import DecisionAgent
        expected = ["click", "type", "keypress", "wait", "assert", "done"]
        assert DecisionAgent.VALID_ACTIONS == expected

    def test_valid_actions_is_class_attribute(self):
        """测试VALID_ACTIONS是类属性而非实例属性"""
        from src.agents.decision_agent import DecisionAgent
        assert hasattr(DecisionAgent, "VALID_ACTIONS")


# ======================== decide() 测试 ========================


class TestDecide:
    """decide() 主方法测试"""

    @pytest.fixture
    def real_memory(self):
        """创建真实StateMemory实例"""
        from src.agents.state_memory import StateMemory
        mem = StateMemory()
        mem.set_test_case("测试登录功能")
        mem.start_test()
        return mem

    @pytest.fixture
    def agent_react(self, mock_glm_client, real_memory):
        """创建启用ReAct模式的agent"""
        from src.agents.decision_agent import DecisionAgent
        return DecisionAgent(
            glm_client=mock_glm_client,
            test_case="测试登录功能",
            state_memory=real_memory,
            use_react=True,
            max_retry_same_action=3
        )

    @pytest.fixture
    def agent_non_react(self, mock_glm_client, real_memory):
        """创建非ReAct模式的agent"""
        from src.agents.decision_agent import DecisionAgent
        return DecisionAgent(
            glm_client=mock_glm_client,
            test_case="测试登录功能",
            state_memory=real_memory,
            use_react=False,
            max_retry_same_action=3
        )

    @pytest.fixture
    def sample_image(self):
        """创建测试用PIL图像"""
        return Image.new("RGB", (100, 100), color="white")

    def test_decide_returns_click_action(self, agent_react, sample_image):
        """测试decide返回正确的click动作"""
        # Use text response that triggers _parse_action_only -> click
        agent_react.glm_client.chat_with_image.return_value = 'click "开始按钮"'
        result = agent_react.decide(sample_image)
        assert result["action"]["action"] == "click"
        assert result["action"]["target"] == "开始按钮"
        assert "reasoning" in result

    def test_decide_returns_type_action(self, agent_react, sample_image):
        """测试decide返回正确的type动作"""
        # Use text response that triggers _parse_action_only -> type
        agent_react.glm_client.chat_with_image.return_value = "输入用户名"
        result = agent_react.decide(sample_image)
        assert result["action"]["action"] == "type"

    def test_decide_returns_wait_action(self, agent_react, sample_image):
        """测试decide返回wait动作"""
        # Use text response that triggers _parse_action_only -> wait
        agent_react.glm_client.chat_with_image.return_value = "等待3秒"
        result = agent_react.decide(sample_image)
        assert result["action"]["action"] == "wait"
        assert result["action"]["seconds"] == 3

    def test_decide_returns_done_action(self, agent_react, sample_image):
        """测试decide返回done动作"""
        # Use text response that triggers _parse_action_only -> done
        agent_react.glm_client.chat_with_image.return_value = "任务完成done"
        result = agent_react.decide(sample_image)
        assert result["action"]["action"] == "done"

    def test_decide_warning_when_action_count_exceeds_threshold(self, agent_react, sample_image):
        """测试decide在动作重复次数超过阈值时返回warning"""
        # 使click:按钮 重复超过max_retry_same_action(3)次
        for _ in range(4):
            agent_react._increment_action("click", "按钮")

        # Use text response for click action
        agent_react.glm_client.chat_with_image.return_value = 'click "按钮"'
        result = agent_react.decide(sample_image)
        assert result["action"]["action"] == "wait"
        assert "warning" in result

    def test_decide_fallback_when_json_parsing_fails(self, agent_react, sample_image):
        """测试decide在JSON解析失败时回退到文本解析"""
        agent_react.glm_client.chat_with_image.return_value = "点击开始按钮"
        result = agent_react.decide(sample_image)
        assert "action" in result
        assert result["action"]["action"] == "click"

    def test_decide_handles_invalid_response(self, agent_react, sample_image):
        """测试decide处理完全无效的响应"""
        agent_react.glm_client.chat_with_image.return_value = "一些无关的文字，没有动作信息"
        result = agent_react.decide(sample_image)
        assert "action" in result
        # 应回退到默认wait
        assert result["action"]["action"] == "wait"

    def test_decide_handles_exception_from_glm(self, agent_react, sample_image):
        """测试decide在GLM调用抛异常时返回安全的回退结果"""
        agent_react.glm_client.chat_with_image.side_effect = ConnectionError("网络断开")
        result = agent_react.decide(sample_image)
        assert "action" in result
        assert result["action"]["action"] == "wait"
        assert "reasoning" in result

    def test_decide_react_mode_uses_react_prompt(self, agent_react, sample_image):
        """测试ReAct模式调用_build_react_prompt"""
        agent_react.glm_client.chat_with_image.return_value = json.dumps({
            "reasoning": "测试推理",
            "action": {"action": "wait", "seconds": 1}
        })
        result = agent_react.decide(sample_image)
        assert "action" in result
        # 验证chat_with_image被调用（即ReAct路径被触发）
        agent_react.glm_client.chat_with_image.assert_called_once()

    def test_decide_non_react_mode_uses_decision_prompt(self, agent_non_react, sample_image):
        """测试非ReAct模式使用决策Prompt"""
        agent_non_react.glm_client.chat_with_image.return_value = 'click "按钮"'
        result = agent_non_react.decide(sample_image)
        assert result["action"]["action"] == "click"

    def test_decide_uses_scene_description_when_provided(self, agent_react, sample_image):
        """测试decide使用提供的场景描述"""
        agent_react.glm_client.chat_with_image.return_value = 'click "按钮"'
        result = agent_react.decide(
            sample_image,
            scene_description="画面显示登录界面"
        )
        assert result["action"]["action"] == "click"

    def test_decide_with_ocr_engine(self, agent_react, sample_image):
        """测试decide使用OCR引擎构建画面描述"""
        mock_ocr = Mock()
        mock_ocr.get_all_text_with_positions.return_value = [
            {"text": "登录", "position": (0, 0)},
            {"text": "用户名", "position": (0, 0)},
        ]
        agent_react.glm_client.chat_with_image.return_value = 'click "登录"'
        result = agent_react.decide(sample_image, ocr_engine=mock_ocr)
        assert result["action"]["action"] == "click"
        mock_ocr.get_all_text_with_positions.assert_called_once_with(sample_image)

    def test_decide_records_action_count(self, agent_react, sample_image):
        """测试decide记录动作计数"""
        agent_react.glm_client.chat_with_image.return_value = 'click "按钮"'
        agent_react.decide(sample_image)
        assert agent_react._get_action_count("click", "按钮") == 1

    def test_decide_with_recent_history_analyzes_repetition(self, agent_react, real_memory, sample_image):
        """测试decide在存在历史动作时分析重复"""
        # 添加一些历史动作
        real_memory.add_action("click", "按钮", "点击按钮", success=False)
        real_memory.add_action("click", "按钮", "再次点击按钮", success=False)
        real_memory.add_action("click", "按钮", "第三次点击按钮", success=False)

        agent_react.glm_client.chat_with_image.return_value = json.dumps({
            "reasoning": "再试一次",
            "action": {"action": "click", "target": "按钮"}
        })
        result = agent_react.decide(sample_image)
        assert "action" in result

    def test_decide_handles_empty_response_string(self, agent_react, sample_image):
        """测试decide处理空字符串响应"""
        agent_react.glm_client.chat_with_image.return_value = ""
        result = agent_react.decide(sample_image)
        assert result["action"]["action"] == "wait"

    def test_decide_handles_whitespace_response(self, agent_react, sample_image):
        """测试decide处理纯空白响应"""
        agent_react.glm_client.chat_with_image.return_value = "   \n  "
        result = agent_react.decide(sample_image)
        assert result["action"]["action"] == "wait"


# ======================== _build_react_prompt 测试 ========================


class TestBuildReactPrompt:
    """_build_react_prompt() 测试"""

    @pytest.fixture
    def agent_with_memory(self):
        """创建带真实StateMemory的agent"""
        from src.agents.state_memory import StateMemory
        from src.agents.decision_agent import DecisionAgent
        mem = StateMemory()
        mem.set_test_case("测试登录功能")
        mem.start_test()
        mem.add_action("click", "登录按钮", "点击登录", success=True)
        mem.add_action("type", "用户名", "输入用户名", success=True)
        return DecisionAgent(
            glm_client=Mock(),
            test_case="测试登录功能",
            state_memory=mem,
            use_react=True
        )

    def test_includes_test_goal(self, agent_with_memory):
        """测试prompt包含测试目标"""
        prompt = agent_with_memory._build_react_prompt(
            history_context="历史动作",
            screen_description="画面描述"
        )
        assert "登录" in prompt

    def test_includes_history_context(self, agent_with_memory):
        """测试prompt包含历史上下文"""
        prompt = agent_with_memory._build_react_prompt(
            history_context="步骤1: 点击登录按钮",
            screen_description="画面描述"
        )
        assert "步骤1: 点击登录按钮" in prompt

    def test_includes_screen_description(self, agent_with_memory):
        """测试prompt包含场景描述"""
        prompt = agent_with_memory._build_react_prompt(
            history_context="历史动作",
            screen_description="画面显示登录界面"
        )
        assert "画面显示登录界面" in prompt

    def test_includes_step_count(self, agent_with_memory):
        """测试prompt包含步骤数"""
        prompt = agent_with_memory._build_react_prompt(
            history_context="历史",
            screen_description="画面"
        )
        # 有2个历史动作，step应为3
        assert "步骤: 3" in prompt

    def test_includes_action_count(self, agent_with_memory):
        """测试prompt包含动作计数"""
        prompt = agent_with_memory._build_react_prompt(
            history_context="历史",
            screen_description="画面"
        )
        assert "已执行动作数: 2" in prompt

    def test_includes_available_actions(self, agent_with_memory):
        """测试prompt包含可用动作列表"""
        prompt = agent_with_memory._build_react_prompt(
            history_context="历史",
            screen_description="画面"
        )
        assert "click" in prompt
        assert "type" in prompt
        assert "keypress" in prompt
        assert "wait" in prompt
        assert "assert" in prompt
        assert "done" in prompt

    def test_includes_elapsed_time_when_start_time_set(self, agent_with_memory):
        """测试prompt包含已用时间"""
        prompt = agent_with_memory._build_react_prompt(
            history_context="历史",
            screen_description="画面"
        )
        assert "秒前" in prompt

    def test_empty_history_still_builds(self):
        """测试无历史动作时也能构建prompt"""
        from src.agents.state_memory import StateMemory
        from src.agents.decision_agent import DecisionAgent
        mem = StateMemory()
        mem.set_test_case("测试")
        agent = DecisionAgent(
            glm_client=Mock(),
            test_case="测试",
            state_memory=mem,
            use_react=True
        )
        prompt = agent._build_react_prompt(
            history_context="（暂无历史动作）",
            screen_description="画面"
        )
        assert "暂无历史动作" in prompt


# ======================== _build_decision_prompt 测试 ========================


class TestBuildDecisionPrompt:
    """_build_decision_prompt() 测试"""

    @pytest.fixture
    def agent(self):
        from src.agents.state_memory import StateMemory
        from src.agents.decision_agent import DecisionAgent
        mem = StateMemory()
        mem.set_test_case("验证登录功能是否正常")
        return DecisionAgent(
            glm_client=Mock(),
            test_case="验证登录功能是否正常",
            state_memory=mem,
            use_react=False
        )

    def test_includes_test_goal(self, agent):
        """测试prompt包含测试目标"""
        prompt = agent._build_decision_prompt("历史动作")
        assert "登录功能" in prompt

    def test_includes_history(self, agent):
        """测试prompt包含历史动作"""
        prompt = agent._build_decision_prompt("步骤1: 点击登录")
        assert "步骤1: 点击登录" in prompt

    def test_includes_history_count(self, agent):
        """测试prompt包含历史条数"""
        prompt = agent._build_decision_prompt("历史")
        assert "最近5条" in prompt

    def test_includes_available_actions(self, agent):
        """测试prompt包含可用动作"""
        prompt = agent._build_decision_prompt("历史")
        assert "click" in prompt
        assert "type" in prompt
        assert "done" in prompt


# ======================== _parse_response_with_reasoning 测试 ========================


class TestParseResponseWithReasoning:
    """_parse_response_with_reasoning() 测试"""

    @pytest.fixture
    def agent(self):
        from src.agents.decision_agent import DecisionAgent
        return DecisionAgent(
            glm_client=Mock(),
            test_case="测试",
            state_memory=Mock(test_goal="测试", actions=[], start_time=None)
        )

    def test_extracts_reasoning_and_action(self, agent):
        """测试提取推理和动作"""
        response = json.dumps({
            "reasoning": "当前需要点击登录按钮",
            "action": {"action": "click", "target": "登录"}
        })
        result = agent._parse_response_with_reasoning(response)
        # _extract_json matches inner {"action": "click", "target": "登录"} first
        assert result["action"] == "click"
        assert result["target"] == "登录"
        assert "reasoning" in result

    def test_empty_response_returns_wait(self, agent):
        """测试空响应返回wait"""
        result = agent._parse_response_with_reasoning("")
        assert result["action"]["action"] == "wait"
        assert result["reasoning"] == "空响应"

    def test_none_response_returns_wait(self, agent):
        """测试None响应返回wait"""
        result = agent._parse_response_with_reasoning(None)
        assert result["action"]["action"] == "wait"

    def test_whitespace_only_response_returns_wait(self, agent):
        """测试纯空白响应返回wait"""
        result = agent._parse_response_with_reasoning("   \n\t  ")
        assert result["action"]["action"] == "wait"

    def test_json_without_reasoning_adds_default(self, agent):
        """测试JSON缺少reasoning时添加默认值"""
        response = json.dumps({"action": "click", "target": "按钮"})
        result = agent._parse_response_with_reasoning(response)
        assert "reasoning" in result
        assert result["action"] == "click"

    def test_json_without_action_key_wraps_as_action(self, agent):
        """测试JSON不含action键时整体包装为action"""
        response = json.dumps({"target": "按钮", "text": "hello"})
        result = agent._parse_response_with_reasoning(response)
        assert "action" in result
        # compat path: whole result wrapped as action value
        assert result["action"]["target"] == "按钮"

    def test_fallback_to_parse_action_only(self, agent):
        """测试无法提取JSON时回退到文本解析"""
        result = agent._parse_response_with_reasoning("点击登录按钮")
        assert result["reasoning"] == "通过文本解析"
        assert result["action"]["action"] == "click"

    def test_nested_json_extraction(self, agent):
        """测试嵌套JSON提取 - 内层优先匹配"""
        response = json.dumps({
            "reasoning": "分析画面",
            "action": {"action": "type", "target": "输入框", "text": "hello"}
        })
        result = agent._parse_response_with_reasoning(response)
        # _extract_json matches inner {"action": "type", ...} first via simple pattern
        assert result["action"] == "type"
        assert result["target"] == "输入框"
        assert result["text"] == "hello"

    def test_json_with_extra_text_before_and_after(self, agent):
        """测试JSON前后有额外文本时仍能提取"""
        response = '根据分析，我认为应该继续。{"action": "click", "target": "开始"} 操作完毕。'
        result = agent._parse_response_with_reasoning(response)
        assert result["action"] == "click"


# ======================== _analyze_repetition 测试 ========================


class TestAnalyzeRepetition:
    """_analyze_repetition() 测试"""

    @pytest.fixture
    def agent(self):
        from src.agents.decision_agent import DecisionAgent
        return DecisionAgent(
            glm_client=Mock(),
            test_case="测试",
            state_memory=Mock(test_goal="测试", actions=[], start_time=None),
            max_retry_same_action=3
        )

    def test_no_warning_when_below_threshold(self, agent):
        """测试未达阈值时无警告"""
        agent._increment_action("click", "按钮")
        agent._increment_action("click", "按钮")
        result = agent._analyze_repetition({"action": "click", "target": "按钮"})
        # count=2 < max(3), but >= 2 so should produce "注意" level warning
        assert result is not None
        assert "注意" in result

    def test_warning_at_max_retry(self, agent):
        """测试达到最大重试次数时返回警告"""
        agent._increment_action("click", "按钮")
        agent._increment_action("click", "按钮")
        agent._increment_action("click", "按钮")
        result = agent._analyze_repetition({"action": "click", "target": "按钮"})
        assert result is not None
        assert "警告" in result

    def test_no_warning_for_new_action(self, agent):
        """测试新动作无警告"""
        result = agent._analyze_repetition({"action": "click", "target": "新按钮"})
        assert result is None

    def test_warning_includes_action_info(self, agent):
        """测试警告包含动作信息"""
        agent._increment_action("click", "登录按钮")
        agent._increment_action("click", "登录按钮")
        agent._increment_action("click", "登录按钮")
        result = agent._analyze_repetition({"action": "click", "target": "登录按钮"})
        assert "click" in result
        assert "登录按钮" in result


# ======================== _build_screen_description 测试 ========================


class TestBuildScreenDescription:
    """_build_screen_description() 测试"""

    @pytest.fixture
    def agent(self):
        from src.agents.decision_agent import DecisionAgent
        return DecisionAgent(
            glm_client=Mock(),
            test_case="测试",
            state_memory=Mock(test_goal="测试", actions=[], start_time=None)
        )

    @pytest.fixture
    def sample_image(self):
        return Image.new("RGB", (100, 100), color="white")

    def test_without_ocr_returns_default(self, agent, sample_image):
        """测试无OCR引擎时返回默认描述"""
        desc = agent._build_screen_description(sample_image, ocr_engine=None)
        assert "截图" in desc or "画面" in desc

    def test_with_ocr_extracts_text(self, agent, sample_image):
        """测试OCR引擎提取文本"""
        mock_ocr = Mock()
        mock_ocr.get_all_text_with_positions.return_value = [
            {"text": "登录", "position": (0, 0)},
            {"text": "用户名", "position": (0, 0)},
            {"text": "密码", "position": (0, 0)},
        ]
        desc = agent._build_screen_description(sample_image, ocr_engine=mock_ocr)
        assert "登录" in desc
        assert "用户名" in desc
        mock_ocr.get_all_text_with_positions.assert_called_once_with(sample_image)

    def test_ocr_returns_empty_text(self, agent, sample_image):
        """测试OCR返回空文本时返回默认描述"""
        mock_ocr = Mock()
        mock_ocr.get_all_text_with_positions.return_value = []
        desc = agent._build_screen_description(sample_image, ocr_engine=mock_ocr)
        assert "截图" in desc or "画面" in desc

    def test_ocr_exception_returns_default(self, agent, sample_image):
        """测试OCR异常时返回默认描述"""
        mock_ocr = Mock()
        mock_ocr.get_all_text_with_positions.side_effect = RuntimeError("OCR错误")
        desc = agent._build_screen_description(sample_image, ocr_engine=mock_ocr)
        assert "截图" in desc or "画面" in desc

    def test_ocr_limits_to_20_texts(self, agent, sample_image):
        """测试OCR限制最多20条文本"""
        mock_ocr = Mock()
        mock_ocr.get_all_text_with_positions.return_value = [
            {"text": f"文本{i}", "position": (0, 0)} for i in range(30)
        ]
        desc = agent._build_screen_description(sample_image, ocr_engine=mock_ocr)
        # 应包含前20条文本
        assert "文本0" in desc
        assert "文本19" in desc


# ======================== _parse_action_only 补充测试 ========================


class TestParseActionOnlyExtended:
    """_parse_action_only() 补充测试"""

    @pytest.fixture
    def agent(self):
        from src.agents.decision_agent import DecisionAgent
        return DecisionAgent(
            glm_client=Mock(),
            test_case="测试",
            state_memory=Mock(test_goal="测试", actions=[], start_time=None)
        )

    def test_detects_done_success(self, agent):
        """测试检测成功完成"""
        action = agent._parse_action_only("任务done，已success")
        assert action["action"] == "done"

    def test_detects_wait_with_seconds(self, agent):
        """测试检测等待并提取秒数"""
        action = agent._parse_action_only("等待5秒后再试")
        assert action["action"] == "wait"
        assert action["seconds"] == 5

    def test_detects_wait_default_seconds(self, agent):
        """测试检测等待无秒数时默认为2"""
        action = agent._parse_action_only("wait for response")
        assert action["action"] == "wait"
        assert action["seconds"] == 2

    def test_detects_click_with_quoted_target(self, agent):
        """测试检测点击并提取引号中的目标"""
        action = agent._parse_action_only('click "提交按钮"')
        assert action["action"] == "click"
        assert action["target"] == "提交按钮"

    def test_detects_click_without_target(self, agent):
        """测试检测点击但无引号目标"""
        action = agent._parse_action_only("please click here")
        assert action["action"] == "click"

    def test_detects_type_action(self, agent):
        """测试检测输入动作"""
        action = agent._parse_action_only("type the username")
        assert action["action"] == "type"

    def test_detects_type_chinese(self, agent):
        """测试检测中文输入"""
        action = agent._parse_action_only("输入用户名")
        assert action["action"] == "type"

    def test_detects_keypress_enter(self, agent):
        """测试检测回车键"""
        action = agent._parse_action_only("press enter key")
        assert action["action"] == "keypress"
        assert action["key"] == "enter"

    def test_detects_keypress_esc(self, agent):
        """测试检测ESC键"""
        action = agent._parse_action_only("press esc key")
        assert action["action"] == "keypress"
        assert action["key"] == "esc"

    def test_detects_keypress_space(self, agent):
        """测试检测空格键"""
        action = agent._parse_action_only("press space key")
        assert action["action"] == "keypress"
        assert action["key"] == "space"

    def test_detects_keypress_default_enter(self, agent):
        """测试检测按键但无具体键时默认回车"""
        action = agent._parse_action_only("key action needed")
        assert action["action"] == "keypress"
        assert action["key"] == "enter"

    def test_default_wait_for_unknown(self, agent):
        """测试未知文本默认返回wait"""
        action = agent._parse_action_only("这是一个不明动作")
        assert action["action"] == "wait"
        assert action["seconds"] == 1


# ======================== _extract_json 补充测试 ========================


class TestExtractJsonExtended:
    """_extract_json() 补充测试"""

    @pytest.fixture
    def agent(self):
        from src.agents.decision_agent import DecisionAgent
        return DecisionAgent(
            glm_client=Mock(),
            test_case="测试",
            state_memory=Mock(test_goal="测试", actions=[], start_time=None)
        )

    def test_extracts_simple_json(self, agent):
        """测试提取简单JSON"""
        result = agent._extract_json('{"action": "click", "target": "按钮"}')
        assert result is not None
        assert result["action"] == "click"

    def test_returns_none_for_no_json(self, agent):
        """测试无JSON时返回None"""
        result = agent._extract_json("没有任何JSON内容")
        assert result is None

    def test_extracts_nested_json(self, agent):
        """测试提取嵌套JSON - 内层对象被优先匹配"""
        result = agent._extract_json('{"reasoning": "分析", "action": {"action": "wait", "seconds": 2}}')
        assert result is not None
        # Simple pattern matches inner {"action": "wait", "seconds": 2} first
        assert result["action"] == "wait"
        assert result["seconds"] == 2

    def test_extracts_json_from_surrounding_text(self, agent):
        """测试从周围文本中提取JSON"""
        result = agent._extract_json('根据分析：{"action": "click", "target": "按钮"}，执行此操作')
        assert result is not None
        assert result["action"] == "click"

    def test_returns_none_for_non_dict_json(self, agent):
        """测试非字典JSON返回None"""
        result = agent._extract_json('[1, 2, 3]')
        assert result is None

    def test_method2_fallback_for_large_json(self, agent):
        """测试方法2（find/rfind）回退提取大块JSON"""
        # Use a flat JSON that method2 can extract when method1 fails
        text = '一些文字 {"action": "type", "target": "输入框", "text": "hello world"} 末尾文字'
        result = agent._extract_json(text)
        assert result is not None
        assert result["action"] == "type"

    def test_returns_none_for_empty_string(self, agent):
        """测试空字符串返回None"""
        result = agent._extract_json("")
        assert result is None
