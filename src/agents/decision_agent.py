"""
决策Agent模块 - 带完善错误处理
"""
import json
import re
import logging
from typing import Dict, Any, Optional, List
from PIL import Image


logger = logging.getLogger(__name__)


SYSTEM_PROMPT_TEMPLATE = """你是一个游戏测试自动化AI助手。

## 你的任务
根据当前游戏画面和测试目标，决定下一步要执行的动作。

## 测试目标
{test_goal}

## 历史动作
{history}

## 可用动作类型
1. click: 点击目标
   - 参数: target（目标名称或坐标[x,y]）
   - 示例: {{"action": "click", "target": "登录按钮"}}
   - 示例: {{"action": "click", "target": [100, 200]}}

2. type: 输入文本
   - 参数: target（输入框名称）, text（要输入的文本）
   - 示例: {{"action": "type", "target": "用户名输入框", "text": "admin"}}

3. keypress: 按键
   - 参数: key（按键名称）
   - 示例: {{"action": "keypress", "key": "enter"}}
   - 示例: {{"action": "keypress", "key": "esc"}}

4. wait: 等待
   - 参数: seconds（等待秒数）
   - 示例: {{"action": "wait", "seconds": 2}}

5. assert: 验证条件
   - 参数: condition（验证条件）
   - 示例: {{"action": "assert", "condition": "登录成功"}}

6. done: 测试完成
   - 参数: success（是否成功）, reason（原因）
   - 示例: {{"action": "done", "success": true, "reason": "已成功登录"}}

## 重要规则
1. 只输出一个JSON对象，不要有多余解释
2. 动作必须从上述类型中选择
3. 如果需要输入文本，先确保点击了对应的输入框
4. 等待画面加载完成后再进行下一步
5. 如果画面出现错误弹窗，先处理弹窗
6. 如果无法确定目标位置，使用"画面描述"功能

## 输出格式
只输出JSON格式的动作对象，例如：
{{"action": "click", "target": "开始游戏按钮"}}
"""


class DecisionAgent:
    """决策Agent"""
    
    VALID_ACTIONS = ["click", "type", "keypress", "wait", "assert", "done"]
    
    def __init__(
        self,
        glm_client,
        test_case: str,
        state_memory,
        temperature: float = 0.2
    ):
        self.glm_client = glm_client
        self.test_case = test_case
        self.state_memory = state_memory
        self.temperature = temperature
        
    def decide(
        self,
        image: Image.Image,
        scene_description: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        根据当前画面决定下一步动作
        
        Args:
            image: 当前截图
            scene_description: 可选的场景描述
            
        Returns:
            动作字典
        """
        # 构造系统Prompt
        system_prompt = SYSTEM_PROMPT_TEMPLATE.format(
            test_goal=self.state_memory.test_goal,
            history=self.state_memory.get_history_prompt(5)
        )
        
        # 构造用户Prompt
        if scene_description:
            user_prompt = f"""当前画面描述: {scene_description}

请根据测试目标和当前画面，决定下一步要执行的动作。"""
        else:
            user_prompt = """请根据测试目标和当前画面，决定下一步要执行的动作。

画面中的文本信息将作为图像的一部分提供给你。"""
        
        # 调用GLM
        try:
            response = self.glm_client.chat_with_image(
                prompt=user_prompt,
                image=image,
                system_prompt=system_prompt
            )
            
            # 解析JSON响应
            action = self._parse_response(response)
            
            # 验证动作
            if not self.validate_action(action):
                logger.warning(f"动作验证失败: {action}")
                return {"action": "wait", "seconds": 1}
            
            return action
            
        except Exception as e:
            logger.error(f"决策失败: {e}")
            # 返回等待动作作为后备
            return {
                "action": "wait",
                "seconds": 2,
                "error": str(e)
            }
    
    def _parse_response(self, response: str) -> Dict[str, Any]:
        """解析GLM响应"""
        if not response or not response.strip():
            logger.warning("空响应")
            return {"action": "wait", "seconds": 1}
        
        # 方法1: 尝试提取简单的JSON对象
        json_pattern = r'\{[^{}]*\}'
        matches = re.findall(json_pattern, response)
        
        for match in matches:
            try:
                action = json.loads(match)
                if "action" in action:
                    return action
            except json.JSONDecodeError:
                continue
        
        # 方法2: 尝试整个响应
        try:
            start = response.find('{')
            end = response.rfind('}')
            if start != -1 and end > start:
                json_str = response[start:end+1]
                action = json.loads(json_str)
                if "action" in action:
                    return action
        except (json.JSONDecodeError, ValueError) as e:
            logger.warning(f"JSON解析失败: {e}")
        
        # 方法3: 尝试从文本中提取动作
        action = self._parse_text_action(response)
        if action:
            return action
        
        # 默认返回等待
        logger.warning(f"无法解析响应，返回默认动作: {response[:100]}...")
        return {
            "action": "wait",
            "seconds": 1,
            "raw_response": response[:200]
        }
    
    def _parse_text_action(self, response: str) -> Optional[Dict[str, Any]]:
        """从文本中解析动作"""
        response_lower = response.lower()
        
        # 检查是否包含完成标记
        if "完成" in response or "done" in response_lower or "成功" in response:
            return {"action": "done", "success": True, "reason": "任务完成"}
        
        # 检查等待
        if "等待" in response or "wait" in response_lower:
            import re
            match = re.search(r'(\d+)\s*(秒|second)', response)
            if match:
                seconds = int(match.group(1))
                return {"action": "wait", "seconds": seconds}
            return {"action": "wait", "seconds": 1}
        
        # 检查点击
        if "点击" in response or "click" in response_lower:
            # 尝试提取目标
            import re
            target_match = re.search(r'["\']([^"\']+)["\']', response)
            if target_match:
                return {"action": "click", "target": target_match.group(1)}
            return {"action": "click", "target": "unknown"}
        
        # 检查输入
        if "输入" in response or "type" in response_lower or "填写" in response:
            return {"action": "type", "target": "input", "text": "test"}
        
        # 检查按键
        if "按键" in response or "key" in response_lower:
            keys = ["enter", "esc", "space", "tab"]
            for key in keys:
                if key in response_lower:
                    return {"action": "keypress", "key": key}
            return {"action": "keypress", "key": "enter"}
        
        return None
    
    def validate_action(self, action: Dict[str, Any]) -> bool:
        """验证动作格式是否正确"""
        if not isinstance(action, dict):
            logger.warning(f"动作类型错误: {type(action)}")
            return False
            
        if "action" not in action:
            logger.warning("动作缺少action字段")
            return False
            
        if action["action"] not in self.VALID_ACTIONS:
            logger.warning(f"未知动作类型: {action['action']}")
            return False
            
        # 验证各动作类型的必要参数
        action_type = action["action"]
        
        if action_type == "click":
            if "target" not in action:
                logger.warning("click动作缺少target")
                return False
                
        elif action_type == "type":
            if "target" not in action or "text" not in action:
                logger.warning("type动作缺少target或text")
                return False
                
        elif action_type == "keypress":
            if "key" not in action:
                logger.warning("keypress动作缺少key")
                return False
                
        elif action_type == "wait":
            if "seconds" not in action:
                # 提供默认值
                action["seconds"] = 1
                
        elif action_type == "assert":
            if "condition" not in action:
                logger.warning("assert动作缺少condition")
                return False
                
        elif action_type == "done":
            if "success" not in action:
                action["success"] = True
            
        return True
