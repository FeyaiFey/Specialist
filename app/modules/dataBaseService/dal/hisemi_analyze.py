from typing import List, Optional, Dict, Any
from sqlalchemy.orm import Session
from sqlalchemy import select, and_, or_, update
from datetime import date, datetime

from app.modules.dataBaseService.dal.base import BaseDAL
from app.modules.dataBaseService.models.hisemi_analyze import HisemiAnalyze

class HisemiAnalyzeDAL(BaseDAL[HisemiAnalyze]):
    """Hisemi 分析数据访问层"""
    
    def __init__(self):
        super().__init__(HisemiAnalyze)
    
    def get_last_date(self, session: Session) -> Optional[date]:
        """
        获取数据库中最后一行的日期
        Args:
            session: 数据库会话
        Returns:
            最后一行的日期或None
        """
        stmt = select(HisemiAnalyze.Date).order_by(HisemiAnalyze.Date.desc()).limit(1)
        result = session.execute(stmt).scalar()
        return result
    
    def batch_update_hisemi_analyze(self, session: Session, data: List[Dict[str, Any]]) -> Dict[str, int]:
        """
        批量插入Hisemi分析数据
        Args:
            session: 数据库会话
            data: 需要插入的数据列表
        Returns:
            统计信息字典
        """
        stats = {
            'inserted': 0,
            'completed': 0
        }
        
        try:
            if not data:
                return stats
                
            # 批量插入新数据
            for item in data:
                new_record = HisemiAnalyze(**item)
                session.add(new_record)
                stats['inserted'] += 1
                    
            session.flush()
            stats['completed'] = stats['inserted']
            
            return stats
            
        except Exception as e:
            session.rollback()
            raise e
        
            
            
            
            
        
