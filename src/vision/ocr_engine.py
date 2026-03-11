"""
OCR识别模块
"""
from typing import List, Tuple, Optional, Dict
import numpy as np
from PIL import Image


class OCREngine:
    """OCR识别引擎"""
    
    def __init__(self, languages: List[str] = None, use_gpu: bool = False):
        """
        初始化OCR引擎
        
        Args:
            languages: 语言列表，如 ["ch_sim", "en"]
            use_gpu: 是否使用GPU加速
        """
        self.languages = languages or ["ch_sim", "en"]
        self.use_gpu = use_gpu
        self._reader = None
        
    @property
    def reader(self):
        """懒加载OCR reader"""
        if self._reader is None:
            try:
                import easyocr
                self._reader = easyocr.Reader(
                    self.languages,
                    gpu=self.use_gpu,
                    verbose=False
                )
            except ImportError:
                raise ImportError("请安装 easyocr: pip install easyocr")
        return self._reader
    
    def recognize(
        self,
        image: Image.Image,
        detail: int = 1
    ) -> List[Tuple[str, List[List[int]]]]:
        """
        识别图像中的文字
        
        Args:
            image: PIL Image对象
            detail: 详细程度，0=简单结果，1=详细结果（包含位置）
            
        Returns:
            识别结果列表
        """
        img_array = np.array(image)
        
        # 转换为RGB（如果需要）
        if len(img_array.shape) == 2:
            img_array = np.stack([img_array] * 3, axis=-1)
        elif img_array.shape[2] == 4:
            # RGBA to RGB
            img_array = img_array[:, :, :3]
        
        results = self.reader.readtext(img_array)
        
        if detail == 0:
            return [text for text, _, _ in results]
        
        # 返回详细结果: (text, bbox, confidence)
        return [(text, bbox, confidence) for text, bbox, confidence in results]
    
    def search_text(
        self,
        image: Image.Image,
        search_term: str,
        confidence_threshold: float = 0.5
    ) -> List[Dict]:
        """
        在图像中搜索指定文本
        
        Args:
            image: PIL Image对象
            search_term: 要搜索的文本
            confidence_threshold: 置信度阈值
            
        Returns:
            匹配结果列表，每项包含 text, bbox, confidence, center
        """
        results = self.recognize(image, detail=1)
        
        matches = []
        search_lower = search_term.lower()
        
        for text, bbox, confidence in results:
            text_lower = text.lower()
            
            # 检查是否匹配（完全匹配或包含）
            if search_lower == text_lower or search_lower in text_lower:
                if confidence >= confidence_threshold:
                    # 计算中心点
                    xs = [p[0] for p in bbox]
                    ys = [p[1] for p in bbox]
                    center_x = int(sum(xs) / 4)
                    center_y = int(sum(ys) / 4)
                    
                    matches.append({
                        "text": text,
                        "bbox": bbox,
                        "confidence": confidence,
                        "center": (center_x, center_y)
                    })
        
        return matches
    
    def find_text_position(
        self,
        image: Image.Image,
        search_term: str,
        confidence_threshold: float = 0.5
    ) -> Optional[Tuple[int, int]]:
        """
        查找文本在图像中的位置（中心坐标）
        
        Returns:
            (x, y) 坐标，未找到返回None
        """
        matches = self.search_text(image, search_term, confidence_threshold)
        
        if matches:
            # 返回置信度最高的匹配
            best_match = max(matches, key=lambda m: m["confidence"])
            return best_match["center"]
        
        return None
    
    def get_all_text_with_positions(
        self,
        image: Image.Image,
        confidence_threshold: float = 0.3
    ) -> List[Dict]:
        """
        获取图像中所有文本及其位置
        
        Returns:
            文本列表，每项包含 text, bbox, center
        """
        results = self.recognize(image, detail=1)
        
        text_items = []
        for text, bbox, confidence in results:
            if confidence >= confidence_threshold:
                xs = [p[0] for p in bbox]
                ys = [p[1] for p in bbox]
                center_x = int(sum(xs) / 4)
                center_y = int(sum(ys) / 4)
                
                text_items.append({
                    "text": text,
                    "bbox": bbox,
                    "center": (center_x, center_y),
                    "confidence": confidence
                })
        
        return text_items
