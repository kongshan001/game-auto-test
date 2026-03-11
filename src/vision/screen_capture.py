"""
屏幕捕获模块
"""
import os
import time
from pathlib import Path
from typing import Optional, Tuple
import mss
import numpy as np
from PIL import Image


class ScreenCapture:
    """屏幕捕获器"""
    
    def __init__(self, window_info=None, save_path: str = "./logs/screenshots"):
        self.window_info = window_info
        self.save_path = Path(save_path)
        self.save_path.mkdir(parents=True, exist_ok=True)
        self._sct = mss.mss()
        
    def set_window(self, window_info):
        """设置目标窗口"""
        self.window_info = window_info
    
    def capture(self, region: Optional[Tuple[int, int, int, int]] = None) -> Image.Image:
        """
        捕获屏幕截图
        
        Args:
            region: (x, y, width, height) 区域，None则捕获整个窗口
            
        Returns:
            PIL Image对象
        """
        if self.window_info is None:
            # 捕获整个屏幕
            monitor = self._sct.monitors[0]
        else:
            if region:
                # 捕获指定区域（相对于窗口）
                x = self.window_info.left + region[0]
                y = self.window_info.top + region[1]
                w, h = region[2], region[3]
            else:
                # 捕获整个窗口
                x = self.window_info.left
                y = self.window_info.top
                w = self.window_info.width
                h = self.window_info.height
            
            monitor = {
                "left": x,
                "top": y,
                "width": w,
                "height": h
            }
        
        screenshot = self._sct.grab(monitor)
        
        # 转换为PIL Image
        img = Image.frombytes("RGB", screenshot.size, screenshot.rgb)
        
        # 翻转因为mss使用BGRA
        img = img.convert("RGB")
        
        return img
    
    def capture_to_numpy(self, region: Optional[Tuple[int, int, int, int]] = None) -> np.ndarray:
        """捕获屏幕并返回numpy数组"""
        img = self.capture(region)
        return np.array(img)
    
    def save_screenshot(
        self,
        filename: Optional[str] = None,
        region: Optional[Tuple[int, int, int, int]] = None
    ) -> str:
        """
        保存截图到文件
        
        Returns:
            保存的文件路径
        """
        if filename is None:
            timestamp = time.strftime("%Y%m%d_%H%M%S")
            filename = f"screenshot_{timestamp}.png"
        
        filepath = self.save_path / filename
        img = self.capture(region)
        img.save(filepath)
        
        return str(filepath)
    
    def capture_and_save(
        self,
        step: int,
        action: str = "",
        region: Optional[Tuple[int, int, int, int]] = None
    ) -> str:
        """捕获并保存截图（带步骤和动作信息）"""
        timestamp = time.strftime("%Y%m%d_%H%M%S")
        filename = f"step{step:03d}_{action}_{timestamp}.png"
        return self.save_screenshot(filename, region)
    
    def __del__(self):
        """清理资源"""
        try:
            self._sct.close()
        except:
            pass
