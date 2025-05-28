# models/validators.py
from typing import Any, Dict, List, Optional, Type
from dataclasses import dataclass
from datetime import datetime

@dataclass
class ValidationError:
    field: str
    message: str
    value: Any

class BaseValidator:
    """数据验证基类"""
    
    def __init__(self):
        self.errors: List[ValidationError] = []
    
    def validate(self, data: Dict[str, Any]) -> bool:
        """验证数据"""
        self.errors.clear()
        return len(self.errors) == 0
    
    def add_error(self, field: str, message: str, value: Any = None):
        """添加错误信息"""
        self.errors.append(ValidationError(field, message, value))
    
    def get_errors(self) -> List[ValidationError]:
        """获取所有错误"""
        return self.errors

class DataCleaner:
    """数据清洗基类"""
    
    @staticmethod
    def clean_string(value: Optional[str]) -> Optional[str]:
        """清理字符串"""
        if value is None:
            return None
        return value.strip()
    
    @staticmethod
    def clean_number(value: Any) -> Optional[float]:
        """清理数字"""
        if value is None:
            return None
        try:
            return float(str(value).strip())
        except (ValueError, TypeError):
            return None
            
    @staticmethod
    def clean_date(value: Any) -> Optional[datetime]:
        """清理日期"""
        if value is None:
            return None
        if isinstance(value, datetime):
            return value
        try:
            return datetime.strptime(str(value).strip(), '%Y-%m-%d')
        except (ValueError, TypeError):
            return None