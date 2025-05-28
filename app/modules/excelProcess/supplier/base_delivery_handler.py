"""
供应商Excel处理器基类
定义供应商Excel处理的基本接口
"""

from typing import Dict, Optional, Any
from abc import ABC, abstractmethod
from .utils import SupplierUtils
from app.utils.logger import get_logger

class BaseDeliveryExcelHandler(ABC):
    """供应商Excel处理器基类"""
    
    def __init__(self):
        """
        初始化处理器
        """
        self.logger = get_logger(__name__)
        self.utils = SupplierUtils()

    
    @abstractmethod
    def process(self, match_result: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        处理Excel文件
        
        Args:
            match_result: 规则引擎匹配结果
            
        Returns:
            Dict: 处理结果
        """
        pass 