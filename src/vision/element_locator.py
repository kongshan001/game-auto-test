"""
元素定位模块
"""
from typing import Optional, Tuple, List, Dict
import cv2
import numpy as np
from PIL import Image


class ElementLocator:
    """元素定位器"""
    
    def __init__(
        self,
        ocr_engine=None,
        glm_client=None,
        window_info=None
    ):
        self.ocr_engine = ocr_engine
        self.glm_client = glm_client
        self.window_info = window_info
        
    def locate_by_text(
        self,
        image: Image.Image,
        description: str,
        confidence_threshold: float = 0.5
    ) -> Optional[Tuple[int, int, int, int]]:
        """
        根据文本描述定位元素
        
        Args:
            image: 当前截图
            description: 元素描述（如"登录按钮"、"用户名输入框"）
            
        Returns:
            (x, y, width, height) 或 None
        """
        if self.ocr_engine:
            # 尝试使用OCR查找
            matches = self.ocr_engine.search_text(image, description, confidence_threshold)
            if matches:
                match = matches[0]
                bbox = match["bbox"]
                # 计算边界框
                xs = [p[0] for p in bbox]
                ys = [p[1] for p in bbox]
                x = int(min(xs))
                y = int(min(ys))
                w = int(max(xs) - x)
                h = int(max(ys) - y)
                return (x, y, w, h)
        
        # 如果OCR失败，尝试使用GLM
        if self.glm_client:
            coords = self._locate_by_glm(image, description)
            if coords:
                # 返回中心点和一个小区域
                cx, cy = coords
                return (cx - 25, cy - 25, 50, 50)
        
        return None
    
    def locate_by_template(
        self,
        image: Image.Image,
        template_path: str,
        threshold: float = 0.8
    ) -> Optional[Tuple[int, int, int, int]]:
        """
        使用模板匹配定位元素
        
        Args:
            image: 当前截图
            template_path: 模板图像路径
            threshold: 匹配阈值
            
        Returns:
            (x, y, width, height) 或 None
        """
        # 转换为numpy数组
        img_gray = cv2.cvtColor(np.array(image), cv2.COLOR_RGB2GRAY)
        
        # 加载模板
        template = cv2.imread(template_path, cv2.IMREAD_GRAYSCALE)
        if template is None:
            return None
        
        # 模板匹配
        result = cv2.matchTemplate(img_gray, template, cv2.TM_CCOEFF_NORMED)
        min_val, max_val, min_loc, max_loc = cv2.minMaxLoc(result)
        
        if max_val >= threshold:
            w, h = template.shape[::-1]
            return (max_loc[0], max_loc[1], w, h)
        
        return None
    
    def locate_by_color(
        self,
        image: Image.Image,
        color_range: Tuple[Tuple[int, int, int], Tuple[int, int, int]],
        min_area: int = 100
    ) -> List[Tuple[int, int, int, int]]:
        """
        根据颜色范围定位元素
        
        Args:
            image: 当前截图
            color_range: HSV颜色范围 ((h_min, s_min, v_min), (h_max, s_max, v_max))
            min_area: 最小区域面积
            
        Returns:
            边界框列表
        """
        img_hsv = cv2.cvtColor(np.array(image), cv2.COLOR_RGB2HSV)
        
        # 创建掩码
        lower = np.array(color_range[0])
        upper = np.array(color_range[1])
        mask = cv2.inRange(img_hsv, lower, upper)
        
        # 查找轮廓
        contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        
        bboxes = []
        for contour in contours:
            area = cv2.contourArea(contour)
            if area >= min_area:
                x, y, w, h = cv2.boundingRect(contour)
                bboxes.append((x, y, w, h))
        
        return bboxes
    
    def get_element_center(
        self,
        image: Image.Image,
        description: str
    ) -> Optional[Tuple[int, int]]:
        """
        获取元素的中心坐标（屏幕绝对坐标）
        
        Args:
            image: 当前截图
            description: 元素描述
            
        Returns:
            (x, y) 绝对坐标，或None
        """
        bbox = self.locate_by_text(image, description)
        
        if bbox:
            cx = bbox[0] + bbox[2] // 2
            cy = bbox[1] + bbox[3] // 2
            
            # 转换为屏幕绝对坐标
            if self.window_info:
                cx += self.window_info.left
                cy += self.window_info.top
            
            return (cx, cy)
        
        return None
    
    def _locate_by_glm(
        self,
        image: Image.Image,
        description: str
    ) -> Optional[Tuple[int, int]]:
        """使用GLM模型预测元素位置"""
        if not self.glm_client:
            return None
        
        prompt = f"""在当前游戏画面中，找到"{description}"的位置。
请以JSON格式输出，包含x和y坐标（画面中的相对位置）。
只输出JSON，不要有其他内容。
格式: {{"x": 数字, "y": 数字}}"""
        
        try:
            response = self.glm_client.chat_with_image(prompt, image)
            import json
            # 尝试解析JSON
            # 提取JSON部分
            start = response.find('{')
            end = response.rfind('}') + 1
            if start >= 0 and end > start:
                json_str = response[start:end]
                data = json.loads(json_str)
                return (data.get("x", 0), data.get("y", 0))
        except Exception as e:
            print(f"GLM定位失败: {e}")
        
        return None
