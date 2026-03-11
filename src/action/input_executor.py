"""
动作执行模块
"""
import time
from typing import Optional, Tuple, Dict, Any, Union
import pydirectinput
from PIL import Image

# 尝试导入win32api作为备用
try:
    import win32api
    import win32con
    HAS_WIN32 = True
except ImportError:
    HAS_WIN32 = False


class ActionExecutor:
    """动作执行器"""
    
    def __init__(
        self,
        window_info=None,
        click_delay: float = 0.5,
        type_delay: float = 0.1,
        keypress_delay: float = 0.3
    ):
        self.window_info = window_info
        self.click_delay = click_delay
        self.type_delay = type_delay
        self.keypress_delay = keypress_delay
        
        # 设置pydirectinput失败安全
        pydirectinput.FAILSAFE = True
        
    def _to_absolute(self, x: int, y: int) -> Tuple[int, int]:
        """将窗口内相对坐标转换为屏幕绝对坐标"""
        if self.window_info:
            return (x + self.window_info.left, y + self.window_info.top)
        return (x, y)
    
    def _to_relative(self, x: int, y: int) -> Tuple[int, int]:
        """将屏幕绝对坐标转换为窗口内相对坐标"""
        if self.window_info:
            return (x - self.window_info.left, y - self.window_info.top)
        return (x, y)
    
    def click(
        self,
        target: Union[str, Tuple[int, int]],
        image: Optional[Image.Image] = None,
        locator: Optional[Any] = None,
        button: str = "left"
    ) -> bool:
        """
        点击目标
        
        Args:
            target: 目标描述（字符串）或坐标 (x, y)
            image: 当前截图（用于定位）
            locator: 元素定位器
            button: 鼠标按钮 ("left", "right", "middle")
            
        Returns:
            是否成功
        """
        try:
            # 获取坐标
            if isinstance(target, str):
                if locator is None:
                    raise ValueError("需要提供locator来定位文本目标")
                coords = locator.get_element_center(image, target)
                if coords is None:
                    print(f"未找到目标: {target}")
                    return False
                x, y = coords
            else:
                x, y = target
            
            # 移动鼠标并点击
            pydirectinput.moveTo(x, y)
            time.sleep(0.1)
            
            if button == "left":
                pydirectinput.click()
            elif button == "right":
                pydirectinput.rightClick()
            elif button == "middle":
                pydirectinput.middleClick()
            
            time.sleep(self.click_delay)
            return True
            
        except Exception as e:
            print(f"点击失败: {e}")
            return False
    
    def double_click(
        self,
        target: Union[str, Tuple[int, int]],
        image: Optional[Image.Image] = None,
        locator: Optional[Any] = None
    ) -> bool:
        """双击目标"""
        try:
            if isinstance(target, str):
                if locator is None:
                    raise ValueError("需要提供locator来定位文本目标")
                coords = locator.get_element_center(image, target)
                if coords is None:
                    return False
                x, y = coords
            else:
                x, y = target
            
            pydirectinput.moveTo(x, y)
            time.sleep(0.1)
            pydirectinput.doubleClick()
            time.sleep(self.click_delay)
            return True
            
        except Exception as e:
            print(f"双击失败: {e}")
            return False
    
    def right_click(
        self,
        target: Union[str, Tuple[int, int]],
        image: Optional[Image.Image] = None,
        locator: Optional[Any] = None
    ) -> bool:
        """右键点击目标"""
        return self.click(target, image, locator, button="right")
    
    def type_text(
        self,
        text: str,
        target: Union[str, Tuple[int, int], None] = None,
        image: Optional[Image.Image] = None,
        locator: Optional[Any] = None,
        clear_first: bool = False
    ) -> bool:
        """
        输入文本
        
        Args:
            text: 要输入的文本
            target: 输入目标（点击后再输入）
            image: 当前截图
            locator: 元素定位器
            clear_first: 是否先清除现有内容
        """
        try:
            # 如果有目标，先点击目标
            if target is not None:
                self.click(target, image, locator)
                time.sleep(0.3)
                
                if clear_first:
                    # 全选并删除
                    pydirectinput.hotkey("ctrl", "a")
                    time.sleep(0.1)
                    pydirectinput.press("backspace")
                    time.sleep(0.1)
            
            # 逐字符输入（更可靠）
            for char in text:
                pydirectinput.write(char)
                time.sleep(self.type_delay)
            
            return True
            
        except Exception as e:
            print(f"输入文本失败: {e}")
            return False
    
    def press_key(self, key: str) -> bool:
        """
        按键
        
        Args:
            key: 按键名称（如 "enter", "esc", "a" 等）
        """
        try:
            pydirectinput.press(key)
            time.sleep(self.keypress_delay)
            return True
        except Exception as e:
            print(f"按键失败: {e}")
            return False
    
    def press_keys(self, keys: list) -> bool:
        """
        组合按键
        
        Args:
            keys: 按键列表（如 ["ctrl", "c"]）
        """
        try:
            pydirectinput.hotkey(*keys)
            time.sleep(self.keypress_delay)
            return True
        except Exception as e:
            print(f"组合按键失败: {e}")
            return False
    
    def wait(self, seconds: float) -> bool:
        """等待指定秒数"""
        time.sleep(seconds)
        return True
    
    def scroll(self, clicks: int, x: Optional[int] = None, y: Optional[int] = None) -> bool:
        """
        滚动鼠标滚轮
        
        Args:
            clicks: 滚动量（正数向上，负数向下）
            x, y: 鼠标位置（可选）
        """
        try:
            if x is not None and y is not None:
                pydirectinput.moveTo(x, y)
                time.sleep(0.1)
            
            pydirectinput.scroll(clicks)
            time.sleep(0.3)
            return True
        except Exception as e:
            print(f"滚动失败: {e}")
            return False
    
    def drag(
        self,
        start: Tuple[int, int],
        end: Tuple[int, int],
        duration: float = 0.5
    ) -> bool:
        """
        拖拽
        
        Args:
            start: 起点坐标
            end: 终点坐标
            duration: 拖拽持续时间（秒）
        """
        try:
            # 移动到起点
            pydirectinput.moveTo(start[0], start[1])
            time.sleep(0.1)
            
            # 按下鼠标
            pydirectinput.mouseDown()
            
            # 移动到终点（分段移动使拖拽更平滑）
            steps = int(duration * 20)
            dx = (end[0] - start[0]) / steps
            dy = (end[1] - start[1]) / steps
            
            for _ in range(steps):
                pydirectinput.move(int(dx), int(dy))
                time.sleep(0.05)
            
            # 释放鼠标
            pydirectinput.mouseUp()
            time.sleep(0.2)
            
            return True
        except Exception as e:
            print(f"拖拽失败: {e}")
            return False
