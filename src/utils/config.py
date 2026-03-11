"""
配置管理模块
"""
import os
from dataclasses import dataclass, field
from typing import Optional
from dotenv import load_dotenv


@dataclass
class Config:
    """测试框架配置"""
    
    # GLM API配置
    glm_api_key: str = ""
    glm_model: str = "glm-4v"
    
    # 游戏配置
    game_exe_path: str = ""
    game_window_title: Optional[str] = None
    game_startup_delay: int = 5
    
    # 测试配置
    test_case: str = ""
    max_steps: int = 100
    step_timeout: int = 30
    
    # 日志配置
    log_level: str = "INFO"
    screenshot_save_path: str = "./logs/screenshots"
    save_screenshots: bool = True
    
    # 视觉配置
    ocr_enabled: bool = True
    ocr_languages: list = field(default_factory=lambda: ["ch_sim", "en"])
    
    # 动作配置
    click_delay: float = 0.5
    type_delay: float = 0.1
    keypress_delay: float = 0.3
    
    @classmethod
    def from_env(cls, env_path: str = ".env") -> "Config":
        """从环境变量加载配置"""
        load_dotenv(env_path)
        
        return cls(
            glm_api_key=os.getenv("GLM_API_KEY", ""),
            glm_model=os.getenv("GLM_MODEL", "glm-4v"),
            game_exe_path=os.getenv("GAME_EXE_PATH", ""),
            game_window_title=os.getenv("GAME_WINDOW_TITLE"),
            game_startup_delay=int(os.getenv("GAME_STARTUP_DELAY", "5")),
            test_case=os.getenv("TEST_CASE", ""),
            max_steps=int(os.getenv("MAX_STEPS", "100")),
            step_timeout=int(os.getenv("STEP_TIMEOUT", "30")),
            log_level=os.getenv("LOG_LEVEL", "INFO"),
            screenshot_save_path=os.getenv("SCREENSHOT_SAVE_PATH", "./logs/screenshots"),
            save_screenshots=os.getenv("SAVE_SCREENSHOTS", "true").lower() == "true",
            ocr_enabled=os.getenv("OCR_ENABLED", "true").lower() == "true",
            ocr_languages=os.getenv("OCR_LANGUAGES", "ch_sim,en").split(","),
            click_delay=float(os.getenv("CLICK_DELAY", "0.5")),
            type_delay=float(os.getenv("TYPE_DELAY", "0.1")),
            keypress_delay=float(os.getenv("KEYPRESS_DELAY", "0.3")),
        )
    
    def validate(self) -> bool:
        """验证配置是否有效"""
        if not self.glm_api_key:
            raise ValueError("GLM_API_KEY is required")
        if not self.game_exe_path:
            raise ValueError("GAME_EXE_PATH is required")
        if not self.test_case:
            raise ValueError("TEST_CASE is required")
        return True
