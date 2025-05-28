from typing import List, Optional, Dict, Any
from sqlalchemy.orm import Session
from sqlalchemy import select, and_, or_, update
from datetime import date, datetime

from app.modules.dataBaseService.dal.base import BaseDAL
from app.modules.dataBaseService.models.wip_assy import WipAssy

class WipAssyDAL(BaseDAL[WipAssy]):
    """WIP 装配数据访问层"""
    
    def __init__(self):
        """初始化，设置模型类"""
        super().__init__(WipAssy)
    
    def get_by_order_no(self, session: Session, order_no: str) -> Optional[WipAssy]:
        """
        通过订单号获取记录
        Args:
            session: 数据库会话
            order_no: 订单号
        Returns:
            WipAssy对象或None
        """
        return self.get_by_id(session, order_no)
    
    def get_by_supplier(self, session: Session, supplier: str) -> List[WipAssy]:
        """
        通过封装厂获取记录
        Args:
            session: 数据库会话
            supplier: 封装厂
        Returns:
            WipAssy对象列表
        """
        stmt = select(WipAssy).where(WipAssy.封装厂 == supplier)
        return list(session.execute(stmt).scalars())
    
    def get_by_process(self, session: Session, process: str) -> List[WipAssy]:
        """
        通过当前工序获取记录
        Args:
            session: 数据库会话
            process: 当前工序
        Returns:
            WipAssy对象列表
        """
        stmt = select(WipAssy).where(WipAssy.当前工序 == process)
        return list(session.execute(stmt).scalars())
    
    def get_incomplete(self, session: Session) -> List[WipAssy]:
        """
        获取未完成的记录
        Args:
            session: 数据库会话
        Returns:
            未完成的WipAssy对象列表
        """
        stmt = select(WipAssy).where(WipAssy.finished_at.is_(None))
        return list(session.execute(stmt).scalars())
    
    def get_by_forecast_date_range(
        self, 
        session: Session, 
        start_date: date, 
        end_date: date
    ) -> List[WipAssy]:
        """
        获取指定预计交期范围内的记录
        Args:
            session: 数据库会话
            start_date: 开始日期
            end_date: 结束日期
        Returns:
            WipAssy对象列表
        """
        stmt = select(WipAssy).where(
            and_(
                WipAssy.预计交期 >= start_date,
                WipAssy.预计交期 <= end_date
            )
        )
        return list(session.execute(stmt).scalars())
    
    def batch_update_supplier_data(
        self,
        session: Session,
        supplier_data: List[Dict[str, Any]]
    ) -> Dict[str, int]:
        """
        批量更新供应商数据
        Args:
            session: 数据库会话
            supplier_data: 供应商数据列表，每个字典包含订单号等信息
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
            
        # 获取当前数据的封装厂
        current_supplier = supplier_data[0].get('封装厂')
        if not current_supplier:
            return stats
            
        # 获取所有该封装厂的现有记录
        existing_orders = {
            record.订单号: record 
            for record in session.query(WipAssy).filter(WipAssy.封装厂 == current_supplier).all()
        }
        
        # 新数据的订单号集合
        new_order_set = {item['订单号'] for item in supplier_data}
        
        # 处理需要标记为完成的记录
        for order_no, record in existing_orders.items():
            # 如果记录不在新数据中，且未完成，则标记为完成
            if order_no not in new_order_set and not record.is_completed:
                record.mark_as_completed()
                stats['completed'] += 1
        
        # 处理新数据
        for item in supplier_data:
            order_no = item['订单号']
            if order_no in existing_orders:
                # 更新现有记录
                record = existing_orders[order_no]
                for key, value in item.items():
                    setattr(record, key, value)
                stats['updated'] += 1
            else:
                # 创建新记录
                new_record = WipAssy(**item)
                session.add(new_record)
                stats['inserted'] += 1
        
        # 刷新会话以应用更改
        session.flush()
        
        return stats 