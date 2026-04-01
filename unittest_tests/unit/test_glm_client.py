"""Tests for src.utils.glm_client — unittest suite."""
import unittest
from unittest.mock import patch, Mock, MagicMock
import base64
import io

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', '..'))


def _create_client(**kwargs):
    """Create a GLMClient with mocked HTTP adapter to avoid Retry compat issues."""
    with patch('src.utils.glm_client.Retry'), \
         patch('src.utils.glm_client.HTTPAdapter'):
        from src.utils.glm_client import GLMClient
        defaults = {"api_key": "test_key"}
        defaults.update(kwargs)
        return GLMClient(**defaults)


def _make_mock_response(content="test response", status_code=200):
    """Helper to create a mock response object."""
    mock_resp = Mock()
    mock_resp.status_code = status_code
    mock_resp.json.return_value = {
        "choices": [{"message": {"content": content}}]
    }
    mock_resp.raise_for_status = Mock()
    if status_code >= 400:
        mock_resp.raise_for_status.side_effect = Exception(f"HTTP {status_code}")
    return mock_resp


class TestGLMAPIError(unittest.TestCase):
    """Tests for GLMAPIError exception."""

    def test_is_exception(self):
        with patch('src.utils.glm_client.Retry'), \
             patch('src.utils.glm_client.HTTPAdapter'):
            from src.utils.glm_client import GLMAPIError
            self.assertTrue(issubclass(GLMAPIError, Exception))

    def test_message(self):
        with patch('src.utils.glm_client.Retry'), \
             patch('src.utils.glm_client.HTTPAdapter'):
            from src.utils.glm_client import GLMAPIError
            err = GLMAPIError("test error")
            self.assertEqual(str(err), "test error")


class TestGLMClientInit(unittest.TestCase):
    """Tests for GLMClient initialization."""

    def test_init_valid_api_key(self):
        client = _create_client(api_key="test_key_123")
        self.assertEqual(client.api_key, "test_key_123")
        self.assertEqual(client.model, "glm-4v")
        self.assertEqual(client.timeout, 30)
        self.assertIn("Bearer test_key_123", client.headers["Authorization"])

    def test_init_empty_api_key_raises(self):
        with self.assertRaises(ValueError):
            _create_client(api_key="")

    def test_init_none_api_key_raises(self):
        with self.assertRaises(ValueError):
            _create_client(api_key=None)

    def test_init_custom_params(self):
        client = _create_client(
            api_key="test_key",
            model="glm-4v-plus",
            base_url="https://custom.api.com",
            max_retries=5,
            backoff_factor=1.0,
            timeout=60,
        )
        self.assertEqual(client.model, "glm-4v-plus")
        self.assertEqual(client.base_url, "https://custom.api.com")
        self.assertEqual(client.timeout, 60)
        self.assertIn("custom.api.com", client.url)

    def test_session_created(self):
        client = _create_client()
        self.assertIsNotNone(client.session)

    def test_headers_set(self):
        client = _create_client(api_key="my_key")
        self.assertEqual(client.headers["Content-Type"], "application/json")
        self.assertEqual(client.headers["Authorization"], "Bearer my_key")

    def test_url_constructed_from_base(self):
        client = _create_client(base_url="https://api.test.com/v1")
        self.assertEqual(client.url, "https://api.test.com/v1/chat/completions")


class TestEncodeImage(unittest.TestCase):
    """Tests for _encode_image method."""

    def setUp(self):
        self.client = _create_client()

    def test_encode_returns_base64_string(self):
        from PIL import Image
        img = Image.new("RGB", (10, 10), color="red")
        encoded = self.client._encode_image(img)
        self.assertIsInstance(encoded, str)
        self.assertTrue(len(encoded) > 0)

    def test_encoded_image_is_decodable(self):
        from PIL import Image
        img = Image.new("RGB", (10, 10), color="blue")
        encoded = self.client._encode_image(img)
        decoded = base64.b64decode(encoded)
        self.assertTrue(len(decoded) > 0)

    def test_encode_different_images_produce_different_output(self):
        from PIL import Image
        img1 = Image.new("RGB", (10, 10), color="red")
        img2 = Image.new("RGB", (10, 10), color="green")
        enc1 = self.client._encode_image(img1)
        enc2 = self.client._encode_image(img2)
        self.assertNotEqual(enc1, enc2)


class TestChat(unittest.TestCase):
    """Tests for chat method."""

    def _make_client_with_mock_session(self):
        """Create a client bypassing __init__ with a mock session."""
        with patch('src.utils.glm_client.Retry'), \
             patch('src.utils.glm_client.HTTPAdapter'):
            from src.utils.glm_client import GLMClient
            client = GLMClient.__new__(GLMClient)
        client.api_key = "test_key"
        client.model = "glm-4v"
        client.base_url = "https://test.api.com"
        client.url = "https://test.api.com/chat/completions"
        client.timeout = 30
        client.headers = {"Authorization": "Bearer test_key", "Content-Type": "application/json"}
        client.session = Mock()
        return client

    def test_chat_success(self):
        client = self._make_client_with_mock_session()
        mock_resp = _make_mock_response("hello world")
        client.session.post.return_value = mock_resp

        result = client.chat([{"role": "user", "content": "hi"}])
        self.assertEqual(result, "hello world")
        client.session.post.assert_called_once()

    def test_chat_timeout_raises_glmapieerror(self):
        import requests
        client = self._make_client_with_mock_session()
        client.session.post.side_effect = requests.exceptions.Timeout("timeout")

        from src.utils.glm_client import GLMAPIError
        with self.assertRaises(GLMAPIError):
            client.chat([{"role": "user", "content": "hi"}])

    def test_chat_connection_error_raises_glmapieerror(self):
        import requests
        client = self._make_client_with_mock_session()
        client.session.post.side_effect = requests.exceptions.ConnectionError("conn err")

        from src.utils.glm_client import GLMAPIError
        with self.assertRaises(GLMAPIError):
            client.chat([{"role": "user", "content": "hi"}])

    def test_chat_generic_request_exception(self):
        import requests
        client = self._make_client_with_mock_session()
        client.session.post.side_effect = requests.exceptions.RequestException("generic err")

        from src.utils.glm_client import GLMAPIError
        with self.assertRaises(GLMAPIError):
            client.chat([{"role": "user", "content": "hi"}])

    def test_chat_passes_correct_payload(self):
        client = self._make_client_with_mock_session()
        mock_resp = _make_mock_response("ok")
        client.session.post.return_value = mock_resp

        messages = [{"role": "user", "content": "hello"}]
        client.chat(messages, temperature=0.5, max_tokens=100)

        call_kwargs = client.session.post.call_args
        payload = call_kwargs.kwargs.get("json") or call_kwargs[1].get("json")
        self.assertEqual(payload["temperature"], 0.5)
        self.assertEqual(payload["max_tokens"], 100)
        self.assertEqual(payload["model"], "glm-4v")
        self.assertEqual(payload["messages"], messages)

    def test_chat_calls_raise_for_status(self):
        client = self._make_client_with_mock_session()
        mock_resp = _make_mock_response("ok")
        client.session.post.return_value = mock_resp

        client.chat([{"role": "user", "content": "hi"}])
        mock_resp.raise_for_status.assert_called_once()

    def test_chat_uses_timeout(self):
        client = self._make_client_with_mock_session()
        mock_resp = _make_mock_response("ok")
        client.session.post.return_value = mock_resp

        client.chat([{"role": "user", "content": "hi"}])
        call_kwargs = client.session.post.call_args
        timeout = call_kwargs.kwargs.get("timeout") or call_kwargs[1].get("timeout")
        self.assertEqual(timeout, 30)


class TestChatWithImage(unittest.TestCase):
    """Tests for chat_with_image method."""

    def setUp(self):
        self.client = _create_client()

    def test_chat_with_image_basic(self):
        with patch.object(self.client, 'chat', return_value="image response") as mock_chat:
            from PIL import Image
            img = Image.new("RGB", (10, 10), color="red")

            result = self.client.chat_with_image("describe this", img)
            self.assertEqual(result, "image response")
            mock_chat.assert_called_once()
            messages = mock_chat.call_args[0][0]
            last_msg = messages[-1]
            self.assertEqual(last_msg["role"], "user")
            self.assertTrue(len(last_msg["content"]) >= 2)

    def test_chat_with_image_with_history(self):
        with patch.object(self.client, 'chat', return_value="response") as mock_chat:
            from PIL import Image
            img = Image.new("RGB", (10, 10), color="red")
            history = [{"role": "assistant", "content": "prev"}]

            self.client.chat_with_image("next", img, history=history)
            messages = mock_chat.call_args[0][0]
            self.assertEqual(len(messages), 2)
            self.assertEqual(messages[0]["role"], "assistant")

    def test_chat_with_image_with_system_prompt(self):
        with patch.object(self.client, 'chat', return_value="response") as mock_chat:
            from PIL import Image
            img = Image.new("RGB", (10, 10), color="red")

            self.client.chat_with_image("prompt", img, system_prompt="you are a helper")
            messages = mock_chat.call_args[0][0]
            self.assertEqual(messages[0]["role"], "system")
            self.assertEqual(messages[0]["content"], "you are a helper")

    def test_chat_with_image_all_options(self):
        with patch.object(self.client, 'chat', return_value="response") as mock_chat:
            from PIL import Image
            img = Image.new("RGB", (10, 10), color="red")
            history = [{"role": "assistant", "content": "prev"}]

            self.client.chat_with_image("prompt", img, history=history, system_prompt="sys")
            messages = mock_chat.call_args[0][0]
            self.assertEqual(len(messages), 3)
            self.assertEqual(messages[0]["role"], "system")
            self.assertEqual(messages[1]["role"], "assistant")
            self.assertEqual(messages[2]["role"], "user")

    def test_chat_with_image_no_optional_params(self):
        with patch.object(self.client, 'chat', return_value="response") as mock_chat:
            from PIL import Image
            img = Image.new("RGB", (10, 10), color="red")

            self.client.chat_with_image("test", img)
            messages = mock_chat.call_args[0][0]
            self.assertEqual(len(messages), 1)  # Only the user message
            self.assertEqual(messages[0]["role"], "user")


class TestDescribeScene(unittest.TestCase):
    """Tests for describe_scene method."""

    def setUp(self):
        self.client = _create_client()

    def test_describe_scene_basic(self):
        with patch.object(self.client, 'chat_with_image', return_value="a game scene") as mock_chat:
            from PIL import Image
            img = Image.new("RGB", (10, 10), color="red")

            result = self.client.describe_scene(img)
            self.assertEqual(result, "a game scene")
            prompt_arg = mock_chat.call_args[0][0]
            self.assertIn("游戏画面", prompt_arg)

    def test_describe_scene_with_context(self):
        with patch.object(self.client, 'chat_with_image', return_value="scene with context") as mock_chat:
            from PIL import Image
            img = Image.new("RGB", (10, 10), color="red")

            result = self.client.describe_scene(img, context="current state: menu")
            self.assertEqual(result, "scene with context")
            prompt_arg = mock_chat.call_args[0][0]
            self.assertIn("current state: menu", prompt_arg)


class TestContextManager(unittest.TestCase):
    """Tests for context manager protocol."""

    def test_enter_returns_self(self):
        client = _create_client()
        with client as c:
            self.assertIs(c, client)

    def test_exit_calls_close(self):
        client = _create_client()
        client.session = Mock()
        with client:
            pass
        client.session.close.assert_called_once()

    def test_exit_calls_close_on_exception(self):
        client = _create_client()
        client.session = Mock()
        try:
            with client:
                raise RuntimeError("test")
        except RuntimeError:
            pass
        client.session.close.assert_called_once()


class TestClose(unittest.TestCase):
    """Tests for close method."""

    def test_close_closes_session(self):
        client = _create_client()
        client.session = Mock()
        client.close()
        client.session.close.assert_called_once()

    def test_close_no_error(self):
        client = _create_client()
        client.close()  # Should not raise


if __name__ == '__main__':
    unittest.main()
