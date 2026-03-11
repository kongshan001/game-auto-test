"""测试屏幕捕获模块 - 跳过需要mss的测试"""
import pytest


class TestScreenCapture:
    """ScreenCapture测试"""
    
    @pytest.mark.skip(reason="需要mss模块")
    def test_screen_capture_creation(self):
        """测试创建屏幕捕获器"""
        from src.vision.screen_capture import ScreenCapture
        
        capture = ScreenCapture(save_path="./test_screenshots")
        assert capture is not None
    
    @pytest.mark.skip(reason="需要mss模块")
    def test_capture_screen(self):
        """测试捕获屏幕"""
        from src.vision.screen_capture import ScreenCapture
        
        capture = ScreenCapture()
        img = capture.capture()
        assert img is not None
