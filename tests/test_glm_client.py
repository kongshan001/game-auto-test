"""测试GLM客户端"""
import pytest
from unittest.mock import Mock, patch, MagicMock
from PIL import Image
import io
import base64


class TestGLMClient:
    """GLMClient测试"""
    
    def test_init_with_valid_api_key(self):
        """测试有效API key初始化"""
        from src.utils.glm_client import GLMClient
        
        client = GLMClient(api_key="test_key_123")
        assert client.api_key == "test_key_123"
        assert client.model == "glm-4v"
        assert client.timeout == 30
    
    def test_init_with_invalid_api_key(self):
        """测试无效API key初始化"""
        from src.utils.glm_client import GLMClient
        
        with pytest.raises(ValueError):
            GLMClient(api_key="")
    
    def test_init_with_custom_params(self):
        """测试自定义参数"""
        from src.utils.glm_client import GLMClient
        
        client = GLMClient(
            api_key="test_key",
            model="glm-4v-plus",
            base_url="https://custom.api.com",
            max_retries=5,
            timeout=60
        )
        assert client.model == "glm-4v-plus"
        assert client.timeout == 60
    
    def test_encode_image(self):
        """测试图像编码"""
        from src.utils.glm_client import GLMClient
        
        client = GLMClient(api_key="test_key")
        img = Image.new('RGB', (100, 100), color='red')
        
        encoded = client._encode_image(img)
        assert isinstance(encoded, str)
        assert len(encoded) > 0
        
        # 验证可以解码
        decoded = base64.b64decode(encoded)
        assert len(decoded) > 0
    
    @patch('src.utils.glm_client.requests.Session')
    def test_chat_success(self, mock_session):
        """测试聊天成功"""
        from src.utils.glm_client import GLMClient
        
        # Mock响应
        mock_response = Mock()
        mock_response.json.return_value = {
            "choices": [{"message": {"content": "test response"}}]
        }
        mock_response.raise_for_status = Mock()
        
        mock_session_instance = Mock()
        mock_session_instance.post.return_value = mock_response
        mock_session.return_value = mock_session_instance
        
        client = GLMClient(api_key="test_key")
        result = client.chat([{"role": "user", "content": "hello"}])
        
        assert result == "test response"
        mock_session_instance.post.assert_called_once()
    
    @patch('src.utils.glm_client.requests.Session')
    def test_chat_timeout(self, mock_session):
        """测试请求超时"""
        from src.utils.glm_client import GLMClient, GLMAPIError
        import requests
        
        mock_session_instance = Mock()
        mock_session_instance.post.side_effect = requests.exceptions.Timeout()
        mock_session.return_value = mock_session_instance
        
        client = GLMClient(api_key="test_key")
        
        with pytest.raises(GLMAPIError):
            client.chat([{"role": "user", "content": "hello"}])
    
    @patch('src.utils.glm_client.requests.Session')
    def test_chat_request_exception(self, mock_session):
        """测试请求异常"""
        from src.utils.glm_client import GLMClient, GLMAPIError
        import requests
        
        mock_session_instance = Mock()
        mock_session_instance.post.side_effect = requests.exceptions.ConnectionError()
        mock_session.return_value = mock_session_instance
        
        client = GLMClient(api_key="test_key")
        
        with pytest.raises(GLMAPIError):
            client.chat([{"role": "user", "content": "hello"}])
    
    def test_context_manager(self):
        """测试上下文管理器"""
        from src.utils.glm_client import GLMClient
        
        with GLMClient(api_key="test_key") as client:
            assert client.api_key == "test_key"
        
        # 验证session已关闭
        # (实际测试时需要mock)
    
    def test_close(self):
        """测试close方法"""
        from src.utils.glm_client import GLMClient
        
        client = GLMClient(api_key="test_key")
        client.close()  # 不应抛出异常
