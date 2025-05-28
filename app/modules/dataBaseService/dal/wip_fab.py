from typing import List, Optional, Dict, Any
from sqlalchemy.orm import Session
from sqlalchemy import select, and_, or_, update
from datetime import date, datetime

from app.modules.dataBaseService.dal.base import BaseDAL
from app.modules.dataBaseService.models.wip_fab import WipFab

class WipFabDAL(BaseDAL[WipFab]):
    """WIP FAB数据访问层"""
    
    def __init__(self):
        """初始化，设置模型类"""
        super().__init__(WipFab)
    
    def get_by_lot(self, session: Session, lot: str) -> Optional[WipFab]:
        """
        通过批次号获取记录
        Args:
            session: 数据库会话
            lot: 批次号
        Returns:
            WipFab对象或None
        """
        return self.get_by_id(session, lot)
    
    def get_by_purchase_order(self, session: Session, purchase_order: str) -> List[WipFab]:
        """
        通过采购订单号获取记录
        Args:
            session: 数据库会话
            purchase_order: 采购订单号
        Returns:
            WipFab对象列表
        """
        stmt = select(WipFab).where(WipFab.purchaseOrder == purchase_order)
        return list(session.execute(stmt).scalars())
    
    def get_by_status(self, session: Session, status: str) -> List[WipFab]:
        """
        通过状态获取记录
        Args:
            session: 数据库会话
            status: 状态
        Returns:
            WipFab对象列表
        """
        stmt = select(WipFab).where(WipFab.status == status)
        return list(session.execute(stmt).scalars())
    
    def get_incomplete(self, session: Session) -> List[WipFab]:
        """
        获取未完成的记录
        Args:
            session: 数据库会话
        Returns:
            未完成的WipFab对象列表
        """
        stmt = select(WipFab).where(
            or_(
                WipFab.remainLayer > 0,
                WipFab.remainLayer.is_(None),
                WipFab.status != "已完结"
            )
        )
        return list(session.execute(stmt).scalars())
    
    def get_by_forecast_date_range(
        self, 
        session: Session, 
        start_date: date, 
        end_date: date
    ) -> List[WipFab]:
        """
        获取指定预计完成日期范围内的记录
        Args:
            session: 数据库会话
            start_date: 开始日期
            end_date: 结束日期
        Returns:
            WipFab对象列表
        """
        stmt = select(WipFab).where(
            and_(
                WipFab.forecastDate >= start_date,
                WipFab.forecastDate <= end_date
            )
        )
        return list(session.execute(stmt).scalars())
    
    def get_by_completion_rate_range(
        self, 
        session: Session, 
        min_rate: float, 
        max_rate: float
    ) -> List[WipFab]:
        """
        获取指定完成率范围内的记录
        Args:
            session: 数据库会话
            min_rate: 最小完成率
            max_rate: 最大完成率
        Returns:
            WipFab对象列表
        """
        stmt = select(WipFab).where(
            and_(
                WipFab.layerCount > 0,  # 确保有总层数
                WipFab.remainLayer.isnot(None),  # 确保有剩余层数
                # 计算完成率并筛选
                (1 - WipFab.remainLayer / WipFab.layerCount) * 100 >= min_rate,
                (1 - WipFab.remainLayer / WipFab.layerCount) * 100 <= max_rate
            )
        )
        return list(session.execute(stmt).scalars())
    
    def update_status(
        self, 
        session: Session, 
        lot: str, 
        new_status: str, 
        new_stage: Optional[str] = None
    ) -> Optional[WipFab]:
        """
        更新状态
        Args:
            session: 数据库会话
            lot: 批次号
            new_status: 新状态
            new_stage: 新阶段（可选）
        Returns:
            更新后的WipFab对象或None
        """
        update_data = {'status': new_status}
        if new_stage is not None:
            update_data['stage'] = new_stage
        return self.update(session, lot, **update_data)
    
    def update_progress(
        self, 
        session: Session, 
        lot: str, 
        remain_layer: int, 
        current_position: Optional[str] = None
    ) -> Optional[WipFab]:
        """
        更新进度
        Args:
            session: 数据库会话
            lot: 批次号
            remain_layer: 剩余层数
            current_position: 当前位置（可选）
        Returns:
            更新后的WipFab对象或None
        """
        update_data = {'remainLayer': remain_layer}
        if current_position is not None:
            update_data['currentPosition'] = current_position
        return self.update(session, lot, **update_data)
    
    def batch_update_supplier_data(
        self,
        session: Session,
        supplier_data: List[Dict[str, Any]]
    ) -> Dict[str, int]:
        """
        批量更新供应商数据
        Args:
            session: 数据库会话
            supplier_data: 供应商数据列表，每个字典包含lot等信息
        Returns:
            更新统计信息
        """
        stats = {
            'inserted': 0,
            'updated': 0,
            'completed': 0
        }
        
        if not supplier_data:
            return stats
            
        # 获取当前数据的供应商
        current_supplier = supplier_data[0].get('supplier')
        if not current_supplier:
            return stats
            
        # 获取所有该供应商的现有记录
        existing_lots = {
            record.lot: record 
            for record in session.query(WipFab).filter(WipFab.supplier == current_supplier).all()
        }
        
        # 新数据的lot集合
        new_lot_set = {item['lot'] for item in supplier_data}
        
        # 处理需要标记为完成的记录
        for lot, record in existing_lots.items():
            # 如果记录不在新数据中，且未完成，且没有完工日期，则标记为完成
            if lot not in new_lot_set and not record.is_completed and not record.finished_at:
                record.mark_as_completed()
                stats['completed'] += 1
        
        # 处理新数据
        for item in supplier_data:
            lot = item['lot']
            if lot in existing_lots:
                # 更新现有记录
                record = existing_lots[lot]
                for key, value in item.items():
                    # 跳过purchaseOrder字段的更新
                    if key != 'purchaseOrder':
                        setattr(record, key, value)
                stats['updated'] += 1
            else:
                # 创建新记录
                new_record = WipFab(**item)
                session.add(new_record)
                stats['inserted'] += 1
        
        # 刷新会话以应用更改
        session.flush()
        
        return stats 