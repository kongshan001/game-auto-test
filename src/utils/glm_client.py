"""
GLM API 客户端
"""
import base64
import io
from typing import Optional, List, Dict, Any
import requests
from PIL import Image


class GLMClient:
    """GLM多模态模型客户端"""

    def __init__(
        self,
        api_key: str,
        model: str = "glm-4v",
        base_url: str = "https://open.bigmodel.cn/api/paas/v4"
    ):
        self.api_key = api_key
        self.model = model
        self.base_url = base_url
        self.url = f"{base_url}/chat/completions"
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

        response = requests.post(
            self.url,
            headers=self.headers,
            json=payload,
            timeout=30
        )
        response.raise_for_status()
        return response.json()["choices"][0]["message"]["content"]

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
