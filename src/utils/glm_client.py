"""
GLM API 客户端 - 带重试机制
"""
import base64
import io
import time
import logging
from typing import Optional, List, Dict, Any
from urllib3.util.retry import Retry
from requests.adapters import HTTPAdapter
import requests
from PIL import Image


logger = logging.getLogger(__name__)


class GLMAPIError(Exception):
    """GLM API 错误"""
    pass


class GLMClient:
    """GLM多模态模型客户端"""

    def __init__(
        self,
        api_key: str,
        model: str = "glm-4v",
        base_url: str = "https://open.bigmodel.cn/api/paas/v4",
        max_retries: int = 3,
        backoff_factor: float = 0.5,
        timeout: int = 30
    ):
        if not api_key:
            raise ValueError("API key is required")
        
        self.api_key = api_key
        self.model = model
        self.base_url = base_url
        self.timeout = timeout
        self.url = f"{base_url}/chat/completions"
        
        # 配置请求会话和重试
        self.session = requests.Session()
        retry_strategy = Retry(
            total=max_retries,
            backoff_factor=backoff_factor,
            status_forcelist=[429, 500, 502, 503, 504],
            allowed_methods=["POST"]
        )
        adapter = HTTPAdapter(max_retries=retry_strategy)
        self.session.mount("http://", adapter)
        self.session.mount("https://", adapter)
        
        self.headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json"
        }

    def _encode_image(self, image: Image.Image) -> str:
        """将PIL图像转换为base64"""
        buffered = io.BytesIO()
        image.save(buffered, format="PNG")
        return base64.b64encode(buffered.getvalue()).decode()

    def chat(
        self,
        messages: List[Dict[str, Any]],
        temperature: float = 0.2,
        max_tokens: int = 500
    ) -> str:
        """发送聊天请求"""
        payload = {
            "model": self.model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens
        }

        try:
            response = self.session.post(
                self.url,
                headers=self.headers,
                json=payload,
                timeout=self.timeout
            )
            response.raise_for_status()
            result = response.json()
            return result["choices"][0]["message"]["content"]
        except requests.exceptions.Timeout:
            logger.error("API请求超时")
            raise GLMAPIError("Request timeout")
        except requests.exceptions.RequestException as e:
            logger.error(f"API请求失败: {e}")
            raise GLMAPIError(f"Request failed: {e}")

    def chat_with_image(
        self,
        prompt: str,
        image: Image.Image,
        history: Optional[List[Dict[str, Any]]] = None,
        system_prompt: Optional[str] = None
    ) -> str:
        """发送带图像的聊天请求"""
        img_base64 = self._encode_image(image)

        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        if history:
            messages.extend(history)

        messages.append({
            "role": "user",
            "content": [
                {"type": "text", "text": prompt},
                {
                    "type": "image_url",
                    "image_url": {"url": f"data:image/png;base64,{img_base64}"}
                }
            ]
        })

        return self.chat(messages)

    def describe_scene(self, image: Image.Image, context: str = "") -> str:
        """描述场景画面"""
        prompt = f"""请描述当前游戏画面中的主要内容，包括：
1. 画面整体布局
2. 可交互的元素（按钮、输入框等）
3. 重要的文本信息
4. 当前界面状态

{context}"""
        return self.chat_with_image(prompt, image)
    
    def close(self):
        """关闭会话"""
        self.session.close()
    
    def __enter__(self):
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()
