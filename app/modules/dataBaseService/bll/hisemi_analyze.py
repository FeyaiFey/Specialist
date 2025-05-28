from typing import List, Dict, Any
from datetime import date
import pandas as pd

from app.utils.logger import get_logger
from app.modules.dataBaseService.dataBaseService import DatabaseSession
from app.modules.dataBaseService.dal.hisemi_analyze import HisemiAnalyzeDAL
from app.modules.dataBaseService.models.hisemi_analyze import HisemiAnalyze
from app.modules.dataBaseService.bll.base import BaseBLL

class HisemiAnalyzeBLL(BaseBLL[HisemiAnalyze]):
    """Hisemi 分析业务逻辑类"""
    
    def __init__(self):
        super().__init__(HisemiAnalyzeDAL)
        self.logger = get_logger('hisemiAnalyzeBLL')

    def update_hisemi_analyze(self, data: List[Dict[date, int]]) -> Dict[str, int]:
        """
        更新Hisemi分析数据
        Args:
            data: 需要更新的数据列表
        Returns:
            更新结果
        """
        try:
            with DatabaseSession() as session:
                stats = self.dal.batch_update_hisemi_analyze(session, data)
                # 提交事务
                session.commit()
                
                self.logger.info(f"Hisemi分析数据更新完成: 新增 {stats['inserted']}, "
                          f"更新 {stats['updated']}, 完成 {stats['completed']}")
                return stats
        except Exception as e:
            self.logger.error(f"更新Hisemi分析数据失败: {e}")
            raise


