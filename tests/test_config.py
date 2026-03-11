"""测试配置模块"""
import pytest
import os
from pathlib import Path
from unittest.mock import patch, mock_open
from src.utils.config import Config


class TestConfig:
    """Config测试"""
    
    def test_init_defaults(self):
        """测试默认初始化"""
        config = Config()
        
        assert config.glm_api_key == ""
        assert config.glm_model == "glm-4v"
        assert config.game_exe_path == ""
        assert config.max_steps == 100
        assert config.log_level == "INFO"
        assert config.ocr_enabled is True
    
    def test_init_custom_values(self):
        """测试自定义值初始化"""
        config = Config(
            glm_api_key="test_key",
            glm_model="glm-4v-plus",
            game_exe_path="C:/game.exe",
            max_steps=50,
            log_level="DEBUG"
        )
        
        assert config.glm_api_key == "test_key"
        assert config.glm_model == "glm-4v-plus"
        assert config.game_exe_path == "C:/game.exe"
        assert config.max_steps == 50
        assert config.log_level == "DEBUG"
    
    @patch.dict(os.environ, {
        'GLM_API_KEY': 'env_key',
        'GLM_MODEL': 'glm-4v-plus',
        'GAME_EXE_PATH': 'C:/game.exe',
        'MAX_STEPS': '50',
        'LOG_LEVEL': 'DEBUG'
    })
    def test_from_env(self):
        """测试从环境变量加载"""
        with patch('src.utils.config.load_dotenv'):
            config = Config.from_env()
            
            assert config.glm_api_key == "env_key"
            assert config.glm_model == "glm-4v-plus"
            assert config.game_exe_path == "C:/game.exe"
            assert config.max_steps == 50
            assert config.log_level == "DEBUG"
    
    @patch.dict(os.environ, {'GLM_API_KEY': 'key'})
    def test_validate_success(self):
        """测试验证成功"""
        config = Config(
            glm_api_key="key",
            game_exe_path="C:/game.exe",
            test_case="测试"
        )
        
        assert config.validate() is True
    
    def test_validate_missing_api_key(self):
        """测试验证缺少API key"""
        config = Config(
            glm_api_key="",
            game_exe_path="C:/game.exe",
            test_case="测试"
        )
        
        with pytest.raises(ValueError, match="GLM_API_KEY"):
            config.validate()
    
    def test_validate_missing_exe_path(self):
        """测试验证缺少exe路径"""
        config = Config(
            glm_api_key="key",
            game_exe_path="",
            test_case="测试"
        )
        
        with pytest.raises(ValueError, match="GAME_EXE_PATH"):
            config.validate()
    
    def test_validate_missing_test_case(self):
        """测试验证缺少测试用例"""
        config = Config(
            glm_api_key="key",
            game_exe_path="C:/game.exe",
            test_case=""
        )
        
        with pytest.raises(ValueError, match="TEST_CASE"):
            config.validate()
    
    def test_ocr_languages_default(self):
        """测试OCR语言默认值"""
        config = Config()
        
        assert config.ocr_languages == ["ch_sim", "en"]
    
    @patch.dict(os.environ, {'OCR_LANGUAGES': 'ch_sim,en,jp'})
    def test_ocr_languages_from_env(self):
        """测试从环境变量加载OCR语言"""
        with patch('src.utils.config.load_dotenv'):
            config = Config.from_env()
            
            assert config.ocr_languages == ["ch_sim", "en", "jp"]
    
    @patch.dict(os.environ, {'OCR_ENABLED': 'false'})
    def test_ocr_disabled_from_env(self):
        """测试OCR禁用"""
        with patch('src.utils.config.load_dotenv'):
            config = Config.from_env()
            
            assert config.ocr_enabled is False
    
    @patch.dict(os.environ, {'SAVE_SCREENSHOTS': 'false'})
    def test_save_screenshots_from_env(self):
        """测试截图保存设置"""
        with patch('src.utils.config.load_dotenv'):
            config = Config.from_env()
            
            assert config.save_screenshots is False
    
    @patch.dict(os.environ, {'CLICK_DELAY': '1.0'})
    def test_delay_from_env(self):
        """测试延迟从环境变量加载"""
        with patch('src.utils.config.load_dotenv'):
            config = Config.from_env()
            
            assert config.click_delay == 1.0
            assert config.type_delay == 0.1
            assert config.keypress_delay == 0.3
    
    def test_all_config_fields(self):
        """测试所有配置字段"""
        config = Config(
            glm_api_key="key",
            glm_model="glm-4v",
            game_exe_path="C:/game.exe",
            game_window_title="Game",
            game_startup_delay=10,
            test_case="测试",
            max_steps=200,
            step_timeout=60,
            log_level="WARNING",
            screenshot_save_path="./screenshots",
            save_screenshots=False,
            ocr_enabled=False,
            ocr_languages=["en"],
            click_delay=1.0,
            type_delay=0.2,
            keypress_delay=0.5
        )
        
        assert config.glm_model == "glm-4v"
        assert config.game_window_title == "Game"
        assert config.game_startup_delay == 10
        assert config.step_timeout == 60
        assert config.screenshot_save_path == "./screenshots"
        assert config.save_screenshots is False
        assert config.ocr_enabled is False
        assert config.ocr_languages == ["en"]
        assert config.click_delay == 1.0
        assert config.type_delay == 0.2
        assert config.keypress_delay == 0.5
