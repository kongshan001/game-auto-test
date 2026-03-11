"""
窗口管理模块
"""
import subprocess
import time
from dataclasses import dataclass
from typing import Optional, Tuple
import win32gui
import win32con
import win32process
import pygetwindow as gw


@dataclass
class WindowInfo:
    """窗口信息"""
    hwnd: int
    title: str
    left: int
    top: int
    width: int
    height: int
    process_id: int
    
    @property
    def center(self) -> Tuple[int, int]:
        """窗口中心坐标"""
        return (
            self.left + self.width // 2,
            self.top + self.height // 2
        )
    
    @property
    def rect(self) -> Tuple[int, int, int, int]:
        """窗口矩形 (left, top, right, bottom)"""
        return (self.left, self.top, self.left + self.width, self.top + self.height)


class WindowManager:
    """窗口管理器"""
    
    def __init__(self):
        self._hwnd: Optional[int] = None
        
    def get_window_by_title(self, title: str) -> Optional[WindowInfo]:
        """根据窗口标题查找窗口"""
        windows = gw.getWindowsWithTitle(title)
        if not windows:
            return None
        
        window = windows[0]
        return self._get_window_info(window._hwnd)
    
    def get_window_by_process_name(self, process_name: str) -> Optional[WindowInfo]:
        """根据进程名查找窗口"""
        def enum_callback(hwnd, windows):
            if win32gui.IsWindowVisible(hwnd):
                title = win32gui.GetWindowText(hwnd)
                if title:
                    _, pid = win32process.GetWindowThreadProcessId(hwnd)
                    try:
                        proc = subprocess.Popen(
                            ["tasklist", "/FI", f"PID eq {pid}", "/FO", "CSV", "/NH"],
                            stdout=subprocess.PIPE,
                            stderr=subprocess.PIPE
                        )
                        output = proc.stdout.read().decode('gbk', errors='ignore')
                        if process_name.lower() in output.lower():
                            windows.append(hwnd)
                    except:
                        pass
            return True
        
        hwnds = []
        try:
            win32gui.EnumWindows(enum_callback, hwnds)
        except:
            pass
        
        if hwnds:
            return self._get_window_info(hwnds[0])
        return None
    
    def get_window_by_pid(self, pid: int) -> Optional[WindowInfo]:
        """根据进程ID查找窗口"""
        def enum_callback(hwnd, windows):
            if win32gui.IsWindowVisible(hwnd):
                try:
                    _, window_pid = win32process.GetWindowThreadProcessId(hwnd)
                    if window_pid == pid:
                        windows.append(hwnd)
                except:
                    pass
            return True
        
        hwnds = []
        try:
            win32gui.EnumWindows(enum_callback, hwnds)
        except:
            pass
        
        if hwnds:
            return self._get_window_info(hwnds[0])
        return None
    
    def _get_window_info(self, hwnd: int) -> WindowInfo:
        """获取窗口详细信息"""
        title = win32gui.GetWindowText(hwnd)
        left, top, right, bottom = win32gui.GetWindowRect(hwnd)
        _, pid = win32process.GetWindowThreadProcessId(hwnd)
        
        return WindowInfo(
            hwnd=hwnd,
            title=title,
            left=left,
            top=top,
            width=right - left,
            height=bottom - top,
            process_id=pid
        )
    
    def activate_window(self, hwnd: int) -> bool:
        """激活窗口"""
        try:
            win32gui.ShowWindow(hwnd, win32con.SW_RESTORE)
            win32gui.SetForegroundWindow(hwnd)
            return True
        except:
            return False
    
    def wait_for_window(
        self,
        process: subprocess.Popen,
        timeout: int = 30,
        title: Optional[str] = None
    ) -> Optional[WindowInfo]:
        """等待窗口出现"""
        start_time = time.time()
        
        while time.time() - start_time < timeout:
            try:
                # 尝试通过PID查找
                if process.poll() is None:  # 进程仍在运行
                    window_info = self.get_window_by_pid(process.pid)
                    if window_info:
                        return window_info
                    
                    # 如果指定了标题，也尝试通过标题查找
                    if title:
                        window_info = self.get_window_by_title(title)
                        if window_info:
                            return window_info
            except:
                pass
            
            time.sleep(0.5)
        
        return None
    
    def is_window_valid(self, hwnd: int) -> bool:
        """检查窗口是否有效"""
        try:
            return win32gui.IsWindow(hwnd) and win32gui.IsWindowVisible(hwnd)
        except:
            return False
