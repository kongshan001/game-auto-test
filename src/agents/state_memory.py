"""
状态记忆模块
"""
import json
import time
from dataclasses import dataclass, field, asdict
from typing import List, Dict, Any, Optional
from datetime import datetime


@dataclass
class ActionRecord:
    """动作记录"""
    step: int
    action: str
    target: str
    description: str
    timestamp: float = field(default_factory=time.time)
    success: bool = True
    error: Optional[str] = None
    screenshot_path: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)
    
    def to_prompt_text(self) -> str:
        """转换为用于Prompt的文本"""
        return f"步骤{self.step}: {self.action} {self.target} - {self.description}"


class StateMemory:
    """状态记忆"""
    
    def __init__(self, max_history: int = 20):
        self.max_history = max_history
        self.actions: List[ActionRecord] = []
        self.test_case: str = ""
        self.test_goal: str = ""
        self.start_time: Optional[float] = None
        self.end_time: Optional[float] = None
        
    def set_test_case(self, test_case: str):
        """设置测试用例"""
        self.test_case = test_case
        # 提取测试目标
        self.test_goal = self._extract_goal(test_case)
        
    def _extract_goal(self, test_case: str) -> str:
        """从测试用例中提取目标"""
        # 简单实现：取最后一个"验证"或"测试"之后的内容
        keywords = ["验证", "检查", "确认", "测试"]
        for keyword in keywords:
            idx = test_case.find(keyword)
            if idx != -1:
                return test_case[idx + len(keyword):].strip().rstrip("。")
        
        # 如果没有关键词，返回整个用例
        return test_case
        
    def add_action(self, action: str, target: str, description: str = "", success: bool = True, error: Optional[str] = None):
        """添加动作记录"""
        record = ActionRecord(
            step=len(self.actions) + 1,
            action=action,
            target=target,
            description=description,
            success=success,
            error=error
        )
        self.actions.append(record)
        
        # 限制历史记录长度
        if len(self.actions) > self.max_history:
            self.actions = self.actions[-self.max_history:]
    
    def get_recent_actions(self, n: int = 5) -> List[ActionRecord]:
        """获取最近N条动作"""
        return self.actions[-n:]
    
    def get_history_prompt(self, n: int = 5) -> str:
        """获取历史动作的Prompt文本"""
        recent = self.get_recent_actions(n)
        if not recent:
            return "（暂无历史动作）"
        
        lines = [action.to_prompt_text() for action in recent]
        return "\n".join(lines)
    
    def start_test(self):
        """开始测试"""
        self.start_time = time.time()
        
    def end_test(self, success: bool = True):
        """结束测试"""
        self.end_time = time.time()
        
    def get_duration(self) -> Optional[float]:
        """获取测试持续时间（秒）"""
        if self.start_time is None:
            return None
        end = self.end_time or time.time()
        return end - self.start_time
    
    def is_completed(self) -> bool:
        """检查是否完成测试"""
        return self.end_time is not None
    
    def get_summary(self) -> Dict[str, Any]:
        """获取测试摘要"""
        total_steps = len(self.actions)
        success_steps = sum(1 for a in self.actions if a.success)
        failed_steps = total_steps - success_steps
        
        return {
            "test_case": self.test_case,
            "test_goal": self.test_goal,
            "total_steps": total_steps,
            "success_steps": success_steps,
            "failed_steps": failed_steps,
            "duration": self.get_duration(),
            "completed": self.is_completed()
        }
    
    def to_json(self) -> str:
        """序列化为JSON"""
        return json.dumps({
            "test_case": self.test_case,
            "test_goal": self.test_goal,
            "actions": [a.to_dict() for a in self.actions],
            "start_time": self.start_time,
            "end_time": self.end_time
        }, ensure_ascii=False, indent=2)
    
    def save_to_file(self, filepath: str):
        """保存到文件"""
        with open(filepath, "w", encoding="utf-8") as f:
            f.write(self.to_json())
