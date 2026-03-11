"""
游戏启动器模块
"""
import os
import subprocess
import time
from typing import Optional, Tuple
from pathlib import Path


class GameLauncher:
    """游戏启动器"""
    
    def __init__(
        self,
        exe_path: str,
        window_title: Optional[str] = None,
        startup_delay: int = 5
    ):
        """
        初始化游戏启动器
        
        Args:
            exe_path: 游戏可执行文件路径
            window_title: 窗口标题（用于查找窗口）
            startup_delay: 启动后等待秒数
        """
        self.exe_path = Path(exe_path)
        self.window_title = window_title
        self.startup_delay = startup_delay
        self.process: Optional[subprocess.Popen] = None
        
    def launch(self, args: list = None, cwd: Optional[str] = None) -> subprocess.Popen:
        """
        启动游戏
        
        Args:
            args: 启动参数
            cwd: 工作目录
            
        Returns:
            subprocess.Popen对象
        """
        if not self.exe_path.exists():
            raise FileNotFoundError(f"游戏可执行文件不存在: {self.exe_path}")
        
        # 构建命令
        cmd = [str(self.exe_path)]
        if args:
            cmd.extend(args)
        
        # 启动进程
        self.process = subprocess.Popen(
            cmd,
            cwd=str(cwd) if cwd else str(self.exe_path.parent),
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            creationflags=subprocess.CREATE_NEW_CONSOLE if os.name == 'nt' else 0
        )
        
        # 等待启动
        if self.startup_delay > 0:
            time.sleep(self.startup_delay)
        
        return self.process
    
    def is_running(self) -> bool:
        """检查游戏是否在运行"""
        if self.process is None:
            return False
        return self.process.poll() is None
    
    def close(self, force: bool = False) -> bool:
        """
        关闭游戏
        
        Args:
            force: 是否强制关闭
            
        Returns:
            是否成功
        """
        if self.process is None:
            return True
            
        try:
            if force:
                self.process.kill()
            else:
                # 尝试正常关闭
                self.process.terminate()
                # 等待进程结束
                try:
                    self.process.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    # 超时则强制关闭
                    self.process.kill()
            return True
        except Exception as e:
            print(f"关闭游戏失败: {e}")
            return False
    
    def restart(self) -> subprocess.Popen:
        """重启游戏"""
        self.close(force=True)
        time.sleep(2)
        return self.launch()
    
    def get_pid(self) -> Optional[int]:
        """获取进程ID"""
        if self.process:
            return self.process.pid
        return None
    
    def get_process_info(self) -> dict:
        """获取进程信息"""
        if self.process is None:
            return {}
        
        return {
            "pid": self.process.pid,
            "running": self.is_running(),
            "returncode": self.process.returncode
        }
