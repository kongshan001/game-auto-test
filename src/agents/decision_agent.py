"""
决策Agent模块 - 支持ReAct推理模式
"""
import json
import re
import logging
from typing import Dict, Any, Optional, List
from PIL import Image


logger = logging.getLogger(__name__)


# ReAct系统Prompt - 包含推理和行动
REACT_SYSTEM_PROMPT = """你是一个游戏测试自动化AI助手，采用推理+行动(ReAct)模式。

## 任务目标
{test_goal}

## 当前状态
- 步骤: {step}
- 测试开始时间: {start_time}
- 已执行动作数: {action_count}

## 历史动作与结果
{history}

## 当前画面
{screen_description}

## 推理过程
请先分析当前情况：
1. 上一步做了什么？结果如何？
2. 当前画面显示什么？
3. 距离测试目标还有多远？
4. 接下来应该怎么做？

## 决策
基于以上分析，选择下一步动作：
{available_actions}

## 输出格式
请输出JSON格式，包含reasoning（推理过程）和action（动作）：
{{
  "reasoning": "你的推理过程（1-2句话）",
  "action": {{"action": "动作类型", ...}}
}}

只输出JSON，不要有其他内容。
"""

# 简化的决策Prompt
DECISION_PROMPT = """你是一个游戏测试自动化AI助手。

## 任务目标
{test_goal}

## 历史动作（最近{history_count}条）
{history}

## 当前画面
请分析当前截图中的内容。

## 可用动作
- click: 点击目标 (target: 目标名称或坐标)
- type: 输入文本 (target: 输入框, text: 内容)
- keypress: 按键 (key: 按键名)
- wait: 等待 (seconds: 秒数)
- assert: 验证 (condition: 验证条件)
- done: 完成 (success: true/false, reason: 原因)

## 重要约束
1. 不要重复已经失败的动作
2. 如果多次尝试同一动作失败，考虑其他方案
3. 等待画面加载完成后再执行下一步

## 输出
只输出JSON: {{"action": "...", "target": "...", "reasoning": "..."}}
"""


class DecisionAgent:
    """决策Agent - 支持ReAct推理模式"""
    
    VALID_ACTIONS = ["click", "type", "keypress", "wait", "assert", "done"]
    
    def __init__(
        self,
        glm_client,
        test_case: str,
        state_memory,
        temperature: float = 0.2,
        use_react: bool = True,
        max_retry_same_action: int = 3
    ):
        self.glm_client = glm_client
        self.test_case = test_case
        self.state_memory = state_memory
        self.temperature = temperature
        self.use_react = use_react
        self.max_retry_same_action = max_retry_same_action
        
        # 跟踪连续重复动作
        self._action_counts: Dict[str, int] = {}
        
    def _reset_action_counts(self):
        """重置动作计数"""
        self._action_counts = {}
    
    def _increment_action(self, action_type: str, target: str):
        """增加动作计数"""
        key = f"{action_type}:{target}"
        self._action_counts[key] = self._action_counts.get(key, 0) + 1
        
    def _get_action_count(self, action_type: str, target: str) -> int:
        """获取动作执行次数"""
        key = f"{action_type}:{target}"
        return self._action_counts.get(key, 0)
    
    def _should_retry(self, action: Dict[str, Any]) -> bool:
        """判断是否应该重试该动作"""
        action_type = action.get("action", "")
        target = str(action.get("target", ""))
        
        count = self._get_action_count(action_type, target)
        return count < self.max_retry_same_action
    
    def _build_history_context(self, recent_only: bool = True) -> str:
        """构建历史上下文"""
        if recent_only:
            history = self.state_memory.get_recent_actions(10)
        else:
            history = self.state_memory.actions
        
        if not history:
            return "（暂无历史动作）"
        
        lines = []
        for record in history:
            status = "✓" if record.success else "✗"
            result = f", 结果: 成功" if record.success else f", 结果: 失败({record.error or '未知'})"
            lines.append(f"步骤{record.step}: {record.action} {record.target} - {record.description}{result}")
        
        return "\n".join(lines)
    
    def _build_screen_description(self, screenshot: Image.Image, ocr_engine=None) -> str:
        """构建画面描述"""
        # 可以使用OCR提取文本
        if ocr_engine:
            try:
                texts = ocr_engine.get_all_text_with_positions(screenshot)
                if texts:
                    text_list = [t["text"] for t in texts[:20]]  # 限制数量
                    return "画面中可见文本: " + ", ".join(text_list)
            except Exception as e:
                logger.debug(f"OCR识别失败: {e}")
        
        return "（请基于截图分析画面内容）"
    
    def _analyze_repetition(self, action: Dict[str, Any]) -> Optional[str]:
        """分析动作是否重复，给出警告"""
        action_type = action.get("action", "")
        target = str(action.get("target", ""))
        
        count = self._get_action_count(action_type, target)
        
        if count >= self.max_retry_same_action:
            return f"警告: 动作 '{action_type} {target}' 已连续执行{count}次，建议更换策略"
        
        if count >= 2:
            return f"注意: 即将第{count+1}次执行 '{action_type} {target}'"
        
        return None
    
    def decide(
        self,
        image: Image.Image,
        scene_description: Optional[str] = None,
        ocr_engine=None
    ) -> Dict[str, Any]:
        """
        根据当前画面决定下一步动作（ReAct模式）
        
        Args:
            image: 当前截图
            scene_description: 可选的场景描述
            ocr_engine: OCR引擎用于提取画面文本
            
        Returns:
            包含reasoning和action的字典
        """
        # 构建上下文
        history_context = self._build_history_context()
        screen_description = scene_description or self._build_screen_description(image, ocr_engine)
        
        # 分析重复动作
        recent_actions = self.state_memory.get_recent_actions(3)
        if recent_actions:
            last_action = recent_actions[-1]
            repetition_warning = self._analyze_repetition({
                "action": last_action.action,
                "target": last_action.target
            })
            if repetition_warning:
                logger.warning(repetition_warning)
        
        # 构造Prompt
        if self.use_react:
            prompt = self._build_react_prompt(
                history_context=history_context,
                screen_description=screen_description
            )
        else:
            prompt = self._build_decision_prompt(history_context)
        
        # 调用GLM
        try:
            response = self.glm_client.chat_with_image(
                prompt=prompt,
                image=image,
                system_prompt="你是一个游戏测试自动化助手。"
            )
            
            # 解析响应
            result = self._parse_response_with_reasoning(response)
            
            # 检查是否应该重试
            if not self._should_retry(result.get("action", {})):
                logger.warning("动作重复次数过多，强制等待")
                result["action"] = {"action": "wait", "seconds": 3, "reason": "避免重复"}
                result["warning"] = "已达到最大重试次数"
            
            # 记录本次动作决策
            if "action" in result:
                action = result["action"]
                self._increment_action(
                    action.get("action", ""),
                    str(action.get("target", ""))
                )
            
            return result
            
        except Exception as e:
            logger.error(f"决策失败: {e}")
            return {
                "reasoning": f"决策出错: {e}",
                "action": {"action": "wait", "seconds": 2, "error": str(e)}
            }
    
    def _build_react_prompt(
        self,
        history_context: str,
        screen_description: str
    ) -> str:
        """构建ReAct Prompt"""
        # 计算统计数据
        all_actions = self.state_memory.actions
        action_count = len(all_actions)
        success_count = sum(1 for a in all_actions if a.success)
        
        # 获取开始时间
        start_time = "未知"
        if self.state_memory.start_time:
            import time
            elapsed = time.time() - self.state_memory.start_time
            start_time = f"{int(elapsed)}秒前"
        
        return REACT_SYSTEM_PROMPT.format(
            test_goal=self.state_memory.test_goal,
            step=action_count + 1,
            start_time=start_time,
            action_count=action_count,
            history=history_context,
            screen_description=screen_description,
            available_actions=self._get_available_actions_text()
        )
    
    def _build_decision_prompt(self, history_context: str) -> str:
        """构建决策Prompt"""
        return DECISION_PROMPT.format(
            test_goal=self.state_memory.test_goal,
            history_count=5,
            history=history_context,
            available_actions=self._get_available_actions_text()
        )
    
    def _get_available_actions_text(self) -> str:
        """获取可用动作说明"""
        return """- click: 点击目标 {"action": "click", "target": "按钮名"}
- type: 输入文本 {"action": "type", "target": "输入框", "text": "内容"}
- keypress: 按键 {"action": "keypress", "key": "enter"}
- wait: 等待 {"action": "wait", "seconds": 2}
- assert: 验证 {"action": "assert", "condition": "验证内容"}
- done: 完成 {"action": "done", "success": true, "reason": "原因"}"""
    
    def _parse_response_with_reasoning(self, response: str) -> Dict[str, Any]:
        """解析带推理的响应"""
        if not response or not response.strip():
            return {
                "reasoning": "空响应",
                "action": {"action": "wait", "seconds": 1}
            }
        
        # 尝试提取JSON
        result = self._extract_json(response)
        
        if result:
            # 确保包含reasoning
            if "reasoning" not in result:
                result["reasoning"] = "基于响应解析"
            if "action" not in result:
                # 兼容旧格式
                result = {"reasoning": "解析动作", "action": result}
            return result
        
        # 尝试简单解析
        action = self._parse_action_only(response)
        return {
            "reasoning": "通过文本解析",
            "action": action
        }
    
    def _extract_json(self, text: str) -> Optional[Dict[str, Any]]:
        """从文本中提取JSON"""
        # 方法1: 查找 { ... } 块
        patterns = [
            r'\{[^{}]*\}',  # 简单块
            r'\{[^{}]*\{[^{}]*\}[^{}]*\}',  # 嵌套块
        ]
        
        for pattern in patterns:
            matches = re.findall(pattern, text)
            for match in matches:
                try:
                    data = json.loads(match)
                    if isinstance(data, dict) and "action" in data:
                        return data
                except json.JSONDecodeError:
                    continue
        
        # 方法2: 查找包含action的JSON
        try:
            start = text.find('{')
            end = text.rfind('}')
            if start != -1 and end > start:
                json_str = text[start:end+1]
                data = json.loads(json_str)
                if isinstance(data, dict):
                    return data
        except (json.JSONDecodeError, ValueError):
            pass
        
        return None
    
    def _parse_action_only(self, text: str) -> Dict[str, Any]:
        """仅解析动作（无推理）"""
        text_lower = text.lower()
        
        # 检测完成
        if any(k in text_lower for k in ["完成", "成功", "done", "success"]):
            return {"action": "done", "success": True, "reason": "任务完成"}
        
        # 检测等待
        if any(k in text_lower for k in ["等待", "wait"]):
            match = re.search(r'(\d+)\s*(秒|s)', text)
            seconds = int(match.group(1)) if match else 2
            return {"action": "wait", "seconds": seconds}
        
        # 检测点击
        if any(k in text_lower for k in ["点击", "click"]):
            target_match = re.search(r'["\']([^"\']+)["\']', text)
            target = target_match.group(1) if target_match else "unknown"
            return {"action": "click", "target": target}
        
        # 检测输入
        if any(k in text_lower for k in ["输入", "type", "填写"]):
            return {"action": "type", "target": "input", "text": ""}
        
        # 检测按键
        if any(k in text_lower for k in ["按键", "key"]):
            keys = ["enter", "esc", "space"]
            for key in keys:
                if key in text_lower:
                    return {"action": "keypress", "key": key}
            return {"action": "keypress", "key": "enter"}
        
        # 默认等待
        return {"action": "wait", "seconds": 1}
    
    def validate_action(self, action: Dict[str, Any]) -> bool:
        """验证动作格式是否正确"""
        if not isinstance(action, dict):
            return False
        
        action_type = action.get("action")
        if action_type not in self.VALID_ACTIONS:
            return False
        
        # 验证各动作的必要参数
        if action_type == "click" and "target" not in action:
            return False
        if action_type == "type" and ("target" not in action or "text" not in action):
            return False
        if action_type == "keypress" and "key" not in action:
            return False
        if action_type == "assert" and "condition" not in action:
            return False
            
        return True
