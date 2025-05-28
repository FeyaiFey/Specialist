from typing import List, Dict, Any, Optional
from datetime import date, datetime, timedelta
import pandas as pd

from app.utils.logger import get_logger
from app.modules.dataBaseService.dataBaseService import DatabaseSession
from app.modules.dataBaseService.dal.wip_assy import WipAssyDAL
from app.modules.dataBaseService.models.wip_assy import WipAssy
from app.modules.dataBaseService.bll.base import BaseBLL

class WipAssyBLL(BaseBLL[WipAssy]):
    """WIP 装配业务逻辑类"""
    
    def __init__(self):
        """初始化"""
        super().__init__(WipAssyDAL)
        self.logger = get_logger('wipAssyBLL')
        
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
                
                self.logger.info(f"供应商数据更新完成: 新增 {stats['inserted']}, "
                          f"更新 {stats['updated']}, 完成 {stats['completed']}")
                return stats
                
        except Exception as e:
            self.logger.error(f"更新供应商进度数据失败: {str(e)}", exc_info=True)
            raise
    
    def get_wip_summary(self) -> Dict[str, Any]:
        """
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
                
                return {
                    'total_count': total_count,
                    'in_progress_count': in_progress_count,
                    'completed_count': completed_count,
                    'statistics_time': datetime.now()
                }
                
        except Exception as e:
            self.logger.error(f"获取WIP汇总信息失败: {str(e)}", exc_info=True)
            raise
    
    def get_delayed_items(self, days_threshold: int = 7) -> List[WipAssy]:
        """
        获取延期项目
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
                    if record.预计交期 
                    and (record.预计交期 < today - timedelta(days=days_threshold))
                ]
                
                return delayed_items
                
        except Exception as e:
            self.logger.error(f"获取延期项目失败: {str(e)}", exc_info=True)
            raise
    
    def get_completion_forecast(self, days: int = 30) -> Dict[date, int]:
        """
        获取未来完成预测
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
                    if record.预计交期:
                        forecast[record.预计交期] = (
                            forecast.get(record.预计交期, 0) + 1
                        )
                
                return forecast
                
        except Exception as e:
            self.logger.error(f"获取完成预测失败: {str(e)}", exc_info=True)
            raise
    
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
            if not item.get('订单号'):
                self.logger.warning(f"跳过缺少订单号的数据: {item}")
                continue
                
            # 数据清洗和转换
            processed_item = {
                '订单号': item['订单号'],
                '封装厂': item.get('封装厂'),
                '当前工序': item.get('当前工序'),
                '预计交期': (
                    datetime.strptime(item['预计交期'], '%Y-%m-%d').date()
                    if isinstance(item['预计交期'], str)
                    else item['预计交期']
                    if item.get('预计交期') and pd.notna(item['预计交期'])
                    else None
                ),
                '次日预计': int(item['次日预计']) if item.get('次日预计') else 0,
                '三日预计': int(item['三日预计']) if item.get('三日预计') else 0,
                '七日预计': int(item['七日预计']) if item.get('七日预计') else 0,
                '仓库库存': int(item['仓库库存']) if item.get('仓库库存') else 0,
                '扣留信息': item.get('扣留信息') if pd.notna(item['扣留信息']) else None,
                '在线合计': int(item['在线合计']) if item.get('在线合计') else 0,
                '研磨': int(item['研磨']) if item.get('研磨') else 0,
                '切割': int(item['切割']) if item.get('切割') else 0,
                '待装片': int(item['待装片']) if item.get('待装片') else 0,
                '装片': int(item['装片']) if item.get('装片') else 0,
                '银胶固化': int(item['银胶固化']) if item.get('银胶固化') else 0,
                '等离子清洗1': int(item['等离子清洗1']) if item.get('等离子清洗1') else 0,
                '键合': int(item['键合']) if item.get('键合') else 0,
                '三目检': int(item['三目检']) if item.get('三目检') else 0,
                '等离子清洗2': int(item['等离子清洗2']) if item.get('等离子清洗2') else 0,
                '塑封': int(item['塑封']) if item.get('塑封') else 0,
                '后固化': int(item['后固化']) if item.get('后固化') else 0,
                '回流焊': int(item['回流焊']) if item.get('回流焊') else 0,
                '电镀': int(item['电镀']) if item.get('电镀') else 0,
                '打印': int(item['打印']) if item.get('打印') else 0,
                '后切割': int(item['后切割']) if item.get('后切割') else 0,
                '切筋成型': int(item['切筋成型']) if item.get('切筋成型') else 0,
                '测编打印': int(item['测编打印']) if item.get('测编打印') else 0,
                '外观检': int(item['外观检']) if item.get('外观检') else 0,
                '包装': int(item['包装']) if item.get('包装') else 0,
                '待入库': int(item['待入库']) if item.get('待入库') else 0,
                'finished_at': item.get('finished_at') if pd.notna(item['finished_at']) else None
            }
            
            validated_data.append(processed_item)
        
        return validated_data