from typing import List, Dict, Any
from datetime import date
import pandas as pd

from utils.logger import Logger
from modules.dataBaseService.dataBaseService import DatabaseSession
from modules.dataBaseService.dal.hisemi_analyze import HisemiAnalyzeDAL
from modules.dataBaseService.models.hisemi_analyze import HisemiAnalyze
from modules.dataBaseService.bll.base import BaseBLL

class HisemiAnalyzeBLL(BaseBLL[HisemiAnalyze]):
    """Hisemi 分析业务逻辑类"""
    
    def __init__(self):
        super().__init__(HisemiAnalyzeDAL)
        self.logger = Logger().get_logger('hisemiAnalyzeBLL')

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
                
                # 清除所有缓存
                self._clear_all_caches()
                
                self.logger.info(f"Hisemi分析数据更新完成: 新增 {stats['inserted']}, "
                          f"更新 {stats['updated']}, 完成 {stats['completed']}")
                return stats
        except Exception as e:
            self.logger.error(f"更新Hisemi分析数据失败: {e}")
            raise
    
    def get_cache_info(self) -> Dict[str, Dict[str, Any]]:
        """
        获取缓存状态信息
        Returns:
            各个缓存的状态信息
        """
        return {
            'update_hisemi_analyze': self.update_hisemi_analyze.cache_info()  # type: ignore
        }
    
    def clear_all_caches(self) -> None:
        """
        清除所有缓存
        """
        try:
            self.update_hisemi_analyze.cache_clear()
            self.logger.debug("所有缓存已清除")
            
        except Exception as e:
            self.logger.error(f"清除缓存失败: {str(e)}")
