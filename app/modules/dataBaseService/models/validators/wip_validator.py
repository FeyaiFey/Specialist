# models/wip_validator.py
from typing import Dict, Any, Optional
from datetime import datetime
import re

from .validators import BaseValidator, DataCleaner

class WipDataValidator(BaseValidator):
    """WIP数据验证器"""
    
    def __init__(self):
        super().__init__()
        self.cleaner = DataCleaner()
    
    def validate(self, data: Dict[str, Any]) -> bool:
        """验证WIP数据"""
        self.errors.clear()
        
        # 必填字段验证
        required_fields = ['lot', 'supplier', 'product']
        for field in required_fields:
            if not data.get(field):
                self.add_error(field, f"{field}不能为空", data.get(field))
        
        # Lot号格式验证
        # lot = data.get('lot')
        # if lot and not re.match(r'^[A-Z0-9]{10,12}$', str(lot)):
        #     self.add_error('lot', 'Lot号格式不正确', lot)
        
        # 数值字段验证
        self._validate_numeric_fields(data)
        
        # 日期字段验证
        self._validate_date_fields(data)
        
        # 状态字段验证
        self._validate_status_fields(data)
        
        return len(self.errors) == 0
    
    def _validate_numeric_fields(self, data: Dict[str, Any]):
        """验证数值字段"""
        numeric_fields = {
            'layerCount': '总层数',
            'remainLayer': '剩余层数',
            'completionRate': '完成率'
        }
        
        for field, name in numeric_fields.items():
            value = data.get(field)
            if value is not None:
                try:
                    num_value = float(value)
                    if field in ['layerCount', 'remainLayer']:
                        if num_value < 0:
                            self.add_error(field, f"{name}不能为负数", value)
                    elif field == 'completionRate':
                        if not 0 <= num_value <= 100:
                            self.add_error(field, f"{name}必须在0-100之间", value)
                except (ValueError, TypeError):
                    self.add_error(field, f"{name}必须是数字", value)
    
    def _validate_date_fields(self, data: Dict[str, Any]):
        """验证日期字段"""
        date_fields = {
            'startDate': '开始日期',
            'forecastDate': '预计完成日期',
            'finishDate': '实际完成日期'
        }
        
        for field, name in date_fields.items():
            value = data.get(field)
            if value is not None:
                cleaned_date = self.cleaner.clean_date(value)
                if cleaned_date is None:
                    self.add_error(field, f"{name}格式不正确", value)
                elif field == 'finishDate' and cleaned_date > datetime.now():
                    self.add_error(field, f"{name}不能晚于当前时间", value)
    
    def _validate_status_fields(self, data: Dict[str, Any]):
        """验证状态字段"""
        valid_statuses = {'待处理', '处理中', '已完成', '异常'}
        status = data.get('status')
        if status and status not in valid_statuses:
            self.add_error('status', f"状态值无效，必须是: {', '.join(valid_statuses)}", status)

class WipDataCleaner(DataCleaner):
    """WIP数据清洗器"""
    
    def clean(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """清洗WIP数据"""
        cleaned_data = {}
        
        # 清理字符串字段
        string_fields = ['lot', 'supplier', 'product', 'status', 'stage', 'currentPosition']
        for field in string_fields:
            if field in data:
                cleaned_data[field] = self.clean_string(data[field])
        
        # 清理数值字段
        numeric_fields = ['layerCount', 'remainLayer', 'completionRate']
        for field in numeric_fields:
            if field in data:
                cleaned_data[field] = self.clean_number(data[field])
        
        # 清理日期字段
        date_fields = ['startDate', 'forecastDate', 'finishDate']
        for field in date_fields:
            if field in data:
                cleaned_data[field] = self.clean_date(data[field])
        
        return cleaned_data