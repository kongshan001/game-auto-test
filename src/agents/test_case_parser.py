"""
测试用例解析器模块
"""
import re
from typing import Dict, Any, List, Optional


class TestCaseParser:
    """测试用例解析器"""
    
    @staticmethod
    def parse(test_case: str) -> Dict[str, Any]:
        """
        解析测试用例
        
        Args:
            test_case: 自然语言测试用例
            
        Returns:
            解析后的结构化测试用例
        """
        # 提取测试目标
        goal = TestCaseParser._extract_goal(test_case)
        
        # 提取步骤
        steps = TestCaseParser._extract_steps(test_case)
        
        # 提取验证条件
        assertions = TestCaseParser._extract_assertions(test_case)
        
        # 提取关键数据
        data = TestCaseParser._extract_data(test_case)
        
        return {
            "goal": goal,
            "steps": steps,
            "assertions": assertions,
            "data": data,
            "raw": test_case
        }
    
    @staticmethod
    def _extract_goal(test_case: str) -> str:
        """提取测试目标"""
        # 尝试查找"验证"、"检查"、"确认"等关键词后的内容
        patterns = [
            r'验证([^，。]*)',
            r'检查([^，。]*)',
            r'确认([^，。]*)',
            r'测试([^，。]*)',
        ]
        
        for pattern in patterns:
            match = re.search(pattern, test_case)
            if match:
                return match.group(1).strip()
        
        # 如果没有找到，返回整个测试用例
        return test_case
    
    @staticmethod
    def _extract_steps(test_case: str) -> List[Dict[str, str]]:
        """提取测试步骤"""
        steps = []
        
        # 查找包含动作的句子
        action_patterns = [
            (r'点击[^\s，。,]+', 'click'),
            (r'输入[^\s，。,]+', 'type'),
            (r'按下[^\s，。,]+', 'keypress'),
            (r'等待[^\s，。,]+', 'wait'),
        ]
        
        sentences = re.split(r'[，。]', test_case)
        
        for sentence in sentences:
            sentence = sentence.strip()
            if not sentence:
                continue
                
            for pattern, action_type in action_patterns:
                if re.search(pattern, sentence):
                    # 提取目标
                    target_match = re.search(r'[^\s]+[^\s，。,](?:按钮|输入框|菜单|选项)?', sentence)
                    target = target_match.group() if target_match else ""
                    
                    # 提取文本（如果是输入动作）
                    text = ""
                    if action_type == "type":
                        text_match = re.search(r"['\"]([^'\"]+)['\"]", sentence)
                        if text_match:
                            text = text_match.group(1)
                    
                    steps.append({
                        "action": action_type,
                        "target": target,
                        "text": text,
                        "description": sentence
                    })
                    break
        
        return steps
    
    @staticmethod
    def _extract_assertions(test_case: str) -> List[str]:
        """提取验证条件"""
        assertions = []
        
        # 查找验证相关的内容
        patterns = [
            r'验证([^，。]*)',
            r'检查([^，。]*)',
            r'确认([^，。]*)',
            r'期望([^\s，。]*)',
        ]
        
        for pattern in patterns:
            matches = re.findall(pattern, test_case)
            assertions.extend(matches)
        
        return [a.strip() for a in assertions if a.strip()]
    
    @staticmethod
    def _extract_data(test_case: str) -> Dict[str, str]:
        """提取测试数据"""
        data = {}
        
        # 查找引号内的内容
        quoted_values = re.findall(r"['\"]([^'\"]+)['\"]", test_case)
        
        # 尝试识别常见字段
        field_patterns = [
            (r'用户名[^\s]*(?:是|为|[:：])?([^\s，。,]+)', 'username'),
            (r'密码[^\s]*(?:是|为|[:：])?([^\s，。,]+)', 'password'),
            (r'账号[^\s]*(?:是|为|[:：])?([^\s，。,]+)', 'account'),
        ]
        
        for pattern, field_name in field_patterns:
            match = re.search(pattern, test_case)
            if match:
                data[field_name] = match.group(1)
        
        return data
    
    @staticmethod
    def to_prompt(test_case_parsed: Dict[str, Any]) -> str:
        """将解析后的测试用例转换为Prompt"""
        parts = []
        
        parts.append(f"测试目标: {test_case_parsed['goal']}")
        
        if test_case_parsed['data']:
            parts.append("\n测试数据:")
            for key, value in test_case_parsed['data'].items():
                parts.append(f"  - {key}: {value}")
        
        if test_case_parsed['steps']:
            parts.append("\n预期步骤:")
            for i, step in enumerate(test_case_parsed['steps'], 1):
                parts.append(f"  {i}. {step['action']} {step['target']}")
        
        if test_case_parsed['assertions']:
            parts.append("\n验证条件:")
            for assertion in test_case_parsed['assertions']:
                parts.append(f"  - {assertion}")
        
        return "\n".join(parts)
