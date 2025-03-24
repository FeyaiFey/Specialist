from typing import List, Dict, Any, Optional, Tuple
from datetime import date, datetime, timedelta
import pandas as pd

from utils.logger import Logger
from modules.dataBaseService.dataBaseService import DatabaseSession
from modules.dataBaseService.dal.wip_fab import WipFabDAL
from modules.dataBaseService.models.wip_fab import WipFab
from utils.cache import cache_5min, cache_1hour, TimedCache
from modules.dataBaseService.bll.base import BaseBLL
from modules.dataBaseService.models.validators.wip_validator import WipDataValidator, DataCleaner


class WipFabBLL(BaseBLL[WipFab]):
    """WIP FAB业务逻辑类"""
    
    def __init__(self):
        """初始化"""
        super().__init__(WipFabDAL)
        self.logger = Logger().get_logger('wipFabBLL')
        self.validator = WipDataValidator()
        self.cleaner = DataCleaner()
        # 创建实例级别的缓存
        self._summary_cache = TimedCache(seconds=300)  # 5分钟缓存
        self._forecast_cache = TimedCache(seconds=3600)  # 1小时缓存

    def process_wip_data(
        self, 
        data: List[Dict[str, Any]]
    ) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
        """
        处理WIP数据
        返回: (有效数据列表, 无效数据列表)
        """
        valid_data = []
        invalid_data = []
        
        for item in data:
            # 数据清洗
            cleaned_item = self.cleaner.clean(item)
            
            # 数据验证
            if self.validator.validate(cleaned_item):
                valid_data.append(cleaned_item)
            else:
                invalid_data.append({
                    'data': item,
                    'errors': [
                        {'field': err.field, 'message': err.message, 'value': err.value}
                        for err in self.validator.get_errors()
                    ]
                })
        
        return valid_data, invalid_data
        

    def update_supplier_progress(self, supplier_data: List[Dict[str, Any]]) -> Dict[str, int]:
        """
        更新供应商进度数据
        Args:
            supplier_data: 供应商提供的进度数据列表
        Returns:
            更新统计信息
        """
        try:
            with DatabaseSession() as session:
                # 数据预处理和验证
                validated_data = self._validate_supplier_data(supplier_data)
                
                # 执行批量更新
                stats = self.dal.batch_update_supplier_data(session, validated_data)
                
                # 提交事务
                session.commit()
                
                # 清除所有缓存
                self._clear_all_caches()
                
                self.logger.info(f"供应商数据更新完成: 新增 {stats['inserted']}, "
                          f"更新 {stats['updated']}, 完成 {stats['completed']}")
                return stats
                

        except Exception as e:
            self.logger.error(f"更新供应商进度数据失败: {str(e)}", exc_info=True)
            raise
    

    @cache_5min
    def get_wip_summary(self) -> Dict[str, Any]:
        """
        获取WIP汇总信息（缓存5分钟）
        Returns:
            汇总信息字典
        """
        try:
            with DatabaseSession() as session:
                # 获取所有记录
                all_records = self.dal.get_all(session)
                
                # 计算汇总信息
                total_count = len(all_records)
                in_progress_count = len([r for r in all_records if not r.is_completed])
                completed_count = len([r for r in all_records if r.is_completed])
                
                # 计算平均完成率
                completion_rates = [r.completion_rate for r in all_records if r.layerCount]
                avg_completion_rate = (
                    sum(completion_rates) / len(completion_rates)
                    if completion_rates else 0
                )
                
                return {
                    'total_count': total_count,
                    'in_progress_count': in_progress_count,
                    'completed_count': completed_count,
                    'avg_completion_rate': round(avg_completion_rate, 2),
                    'statistics_time': datetime.now()
                }
                
        except Exception as e:
            self.logger.error(f"获取WIP汇总信息失败: {str(e)}", exc_info=True)
            raise
    

    @cache_5min
    def get_delayed_items(self, days_threshold: int = 7) -> List[WipFab]:
        """
        获取延期项目（缓存5分钟）
        Args:
            days_threshold: 延期天数阈值
        Returns:
            延期项目列表
        """
        try:
            with DatabaseSession() as session:
                today = date.today()
                all_records = self.dal.get_incomplete(session)
                
                # 筛选延期项目
                delayed_items = [
                    record for record in all_records
                    if record.forecastDate 
                    and (record.forecastDate < today - timedelta(days=days_threshold))
                ]
                
                return delayed_items
                
        except Exception as e:
            self.logger.error(f"获取延期项目失败: {str(e)}", exc_info=True)
            raise
    

    @cache_1hour
    def get_completion_forecast(self, days: int = 30) -> Dict[date, int]:
        """
        获取未来完成预测（缓存1小时）
        Args:
            days: 预测天数
        Returns:
            日期到预计完成数量的映射
        """
        try:
            with DatabaseSession() as session:
                start_date = date.today()
                end_date = start_date + timedelta(days=days)
                
                # 获取预计在该日期范围内完成的记录
                records = self.dal.get_by_forecast_date_range(
                    session, start_date, end_date
                )
                
                # 按预计完成日期分组统计
                forecast = {}
                for record in records:
                    if record.forecastDate:
                        forecast[record.forecastDate] = (
                            forecast.get(record.forecastDate, 0) + 1
                        )
                
                return forecast
                
        except Exception as e:
            self.logger.error(f"获取完成预测失败: {str(e)}", exc_info=True)
            raise
    

    def get_cache_info(self) -> Dict[str, Dict[str, Any]]:
        """
        获取缓存状态信息
        Returns:
            各个缓存的状态信息
        """
        return {
            'wip_summary': self.get_wip_summary.cache_info(),  # type: ignore
            'delayed_items': self.get_delayed_items.cache_info(),  # type: ignore
            'completion_forecast': self.get_completion_forecast.cache_info()  # type: ignore
        }
    
    def _validate_supplier_data(self, data: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        验证和预处理供应商数据
        Args:
            data: 原始供应商数据
        Returns:
            处理后的数据
        """
        validated_data = []
        for item in data:
            # 确保必要字段存在
            if not item.get('lot'):
                self.logger.warning(f"跳过缺少lot的数据: {item}")
                continue
                
            # 数据清洗和转换
            processed_item = {
                'lot': item['lot'],
                'purchaseOrder': item.get('purchaseOrder'),
                'itemName': item.get('itemName'),
                'qty': int(item['qty']) if item.get('qty') and pd.notna(item['qty']) else None,
                'status': item.get('status', '在制'),
                'stage': item.get('stage'),
                'layerCount': int(item['layerCount']) if item.get('layerCount') and pd.notna(item['layerCount']) else None,
                'remainLayer': int(item['remainLayer']) if item.get('remainLayer') and pd.notna(item['remainLayer']) else None,
                'currentPosition': item.get('currentPosition') if item.get('currentPosition') and pd.notna(item.get('currentPosition')) else None,
                'forecastDate': (
                    datetime.strptime(item['forecastDate'], '%Y-%m-%d').date()
                    if isinstance(item['forecastDate'], str)
                    else item['forecastDate']
                    if item.get('forecastDate') and pd.notna(item['forecastDate'])
                    else None
                ),
                'supplier': item.get('supplier'),
                'finished_at': item.get('finished_at') if pd.notna(item.get('finished_at')) else None
            }
            
            # 验证数据合理性
            if (processed_item.get('layerCount') and processed_item.get('remainLayer') and
                processed_item['remainLayer'] > processed_item['layerCount']):
                self.logger.warning(
                    f"剩余层数大于总层数，数据可能有误: lot={processed_item['lot']}, "
                    f"layerCount={processed_item['layerCount']}, "
                    f"remainLayer={processed_item['remainLayer']}"
                )
                continue
            
            validated_data.append(processed_item)
        
        return validated_data
    
    def _clear_all_caches(self) -> None:
        """清除所有缓存"""
        try:
            # 清除方法级别的缓存
            self.get_wip_summary.cache_clear()  # type: ignore
            self.get_delayed_items.cache_clear()  # type: ignore
            self.get_completion_forecast.cache_clear()  # type: ignore
            
            self.logger.debug("所有缓存已清除")
            
        except Exception as e:
            self.logger.error(f"清除缓存失败: {str(e)}")

            # 不抛出异常，因为这是非关键操作 