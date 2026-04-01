"""测试GLM客户端"""
import pytest
from unittest.mock import Mock, patch, MagicMock
from PIL import Image
import base64
import requests


def _create_client(**kwargs):
    """创建 GLMClient，mock Retry 和 HTTPAdapter 避免 urllib3 版本兼容问题。"""
    with patch('src.utils.glm_client.Retry'), \
         patch('src.utils.glm_client.HTTPAdapter'):
        from src.utils.glm_client import GLMClient
        defaults = {"api_key": "test_key"}
        defaults.update(kwargs)
        return GLMClient(**defaults)


def _make_mock_response(content="test response", status_code=200):
    """创建 mock HTTP 响应。"""
    mock_resp = Mock()
    mock_resp.status_code = status_code
    mock_resp.json.return_value = {
        "choices": [{"message": {"content": content}}]
    }
    mock_resp.raise_for_status = Mock()
    if status_code >= 400:
        mock_resp.raise_for_status.side_effect = Exception(f"HTTP {status_code}")
    return mock_resp


class TestGLMClient:
    """GLMClient测试"""

    def test_init_with_valid_api_key(self):
        """测试有效API key初始化"""
        client = _create_client(api_key="test_key_123")
        assert client.api_key == "test_key_123"
        assert client.model == "glm-4v"
        assert client.timeout == 30

    def test_init_with_invalid_api_key(self):
        """测试无效API key初始化"""
        with patch('src.utils.glm_client.Retry'), \
             patch('src.utils.glm_client.HTTPAdapter'):
            from src.utils.glm_client import GLMClient
            with pytest.raises(ValueError):
                GLMClient(api_key="")

    def test_init_with_custom_params(self):
        """测试自定义参数"""
        client = _create_client(
            api_key="test_key",
            model="glm-4v-plus",
            base_url="https://custom.api.com",
            max_retries=5,
            timeout=60
        )
        assert client.model == "glm-4v-plus"
        assert client.timeout == 60

    def test_init_headers(self):
        """测试请求头设置"""
        client = _create_client(api_key="my_key")
        assert client.headers["Content-Type"] == "application/json"
        assert "Bearer my_key" in client.headers["Authorization"]

    def test_init_url_constructed(self):
        """测试URL构建"""
        client = _create_client(base_url="https://api.test.com/v1")
        assert client.url == "https://api.test.com/v1/chat/completions"

    def test_encode_image(self):
        """测试图像编码——使用真实PIL图像和真实base64编码"""
        client = _create_client()
        img = Image.new('RGB', (10, 10), color='red')

        encoded = client._encode_image(img)
        assert isinstance(encoded, str)
        assert len(encoded) > 0

        # 真实的base64解码验证
        decoded = base64.b64decode(encoded)
        assert len(decoded) > 0

    def test_encode_image_different_colors(self):
        """测试不同颜色图像编码结果不同"""
        client = _create_client()
        img1 = Image.new('RGB', (10, 10), color='red')
        img2 = Image.new('RGB', (10, 10), color='blue')
        assert client._encode_image(img1) != client._encode_image(img2)

    def test_chat_success(self):
        """测试聊天成功"""
        client = _create_client()
        client.session = Mock()
        client.session.post.return_value = _make_mock_response("hello world")

        result = client.chat([{"role": "user", "content": "hi"}])
        assert result == "hello world"
        client.session.post.assert_called_once()

    def test_chat_timeout_raises_glmapieerror(self):
        """测试请求超时抛出GLMAPIError"""
        from src.utils.glm_client import GLMAPIError
        client = _create_client()
        client.session = Mock()
        client.session.post.side_effect = requests.exceptions.Timeout()

        with pytest.raises(GLMAPIError):
            client.chat([{"role": "user", "content": "hi"}])

    def test_chat_connection_error_raises_glmapieerror(self):
        """测试连接错误抛出GLMAPIError"""
        from src.utils.glm_client import GLMAPIError
        client = _create_client()
        client.session = Mock()
        client.session.post.side_effect = requests.exceptions.ConnectionError()

        with pytest.raises(GLMAPIError):
            client.chat([{"role": "user", "content": "hi"}])

    def test_chat_generic_request_exception(self):
        """测试通用请求异常抛出GLMAPIError"""
        from src.utils.glm_client import GLMAPIError
        client = _create_client()
        client.session = Mock()
        client.session.post.side_effect = requests.exceptions.RequestException("err")

        with pytest.raises(GLMAPIError):
            client.chat([{"role": "user", "content": "hi"}])

    def test_chat_passes_correct_payload(self):
        """测试chat传递正确的请求参数"""
        client = _create_client()
        client.session = Mock()
        client.session.post.return_value = _make_mock_response("ok")

        messages = [{"role": "user", "content": "hello"}]
        client.chat(messages, temperature=0.5, max_tokens=100)

        call_kwargs = client.session.post.call_args
        payload = call_kwargs.kwargs.get("json") or call_kwargs[1].get("json")
        assert payload["temperature"] == 0.5
        assert payload["max_tokens"] == 100
        assert payload["model"] == "glm-4v"
        assert payload["messages"] == messages

    def test_chat_uses_timeout(self):
        """测试chat使用正确的超时设置"""
        client = _create_client()
        client.session = Mock()
        client.session.post.return_value = _make_mock_response("ok")

        client.chat([{"role": "user", "content": "hi"}])
        call_kwargs = client.session.post.call_args
        timeout = call_kwargs.kwargs.get("timeout") or call_kwargs[1].get("timeout")
        assert timeout == 30

    def test_chat_with_image_basic(self):
        """测试带图像的聊天"""
        client = _create_client()
        with patch.object(client, 'chat', return_value="image response"):
            img = Image.new('RGB', (10, 10), color='red')
            result = client.chat_with_image("describe this", img)
            assert result == "image response"

    def test_chat_with_image_with_history_and_system(self):
        """测试带历史和系统提示的图像聊天"""
        client = _create_client()
        with patch.object(client, 'chat', return_value="response") as mock_chat:
            img = Image.new('RGB', (10, 10), color='red')
            client.chat_with_image("prompt", img,
                                   history=[{"role": "assistant", "content": "prev"}],
                                   system_prompt="you are a helper")
            messages = mock_chat.call_args[0][0]
            assert messages[0]["role"] == "system"
            assert messages[1]["role"] == "assistant"
            assert messages[2]["role"] == "user"

    def test_describe_scene(self):
        """测试场景描述"""
        client = _create_client()
        with patch.object(client, 'chat_with_image', return_value="a scene"):
            img = Image.new('RGB', (10, 10), color='red')
            result = client.describe_scene(img, context="state: menu")
            assert result == "a scene"
            prompt_arg = client.chat_with_image.call_args[0][0]
            assert "游戏画面" in prompt_arg
            assert "state: menu" in prompt_arg

    def test_context_manager_enter_returns_self(self):
        """测试上下文管理器enter返回自身"""
        client = _create_client()
        with client as c:
            assert c is client

    def test_context_manager_exit_closes_session(self):
        """测试上下文管理器exit关闭session"""
        client = _create_client()
        client.session = Mock()
        with client:
            pass
        client.session.close.assert_called_once()

    def test_close_closes_session(self):
        """测试close方法关闭session"""
        client = _create_client()
        client.session = Mock()
        client.close()
        client.session.close.assert_called_once()

    def test_close_no_error_when_no_session(self):
        """测试close在没有session时不报错"""
        client = _create_client()
        client.close()  # 不应抛出异常
