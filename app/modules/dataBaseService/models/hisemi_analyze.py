from sqlalchemy import Column, String, Integer, Date, DateTime
from app.modules.dataBaseService.models.base import BaseModel
from datetime import date, datetime

class HisemiAnalyze(BaseModel):
    """Hisemi 分析数据模型"""
    __tablename__ = 'huaxinAdmin_hisemi_loading_analyze'
    __table_args__ = {'extend_existing': True}

    # 主键
    Date = Column(Date, primary_key=True, comment='日期')
    SOP8_12R = Column(Integer, nullable=False, name='SOP8(12R)', comment='SOP8(12R)')
    SOP8 = Column(Integer, nullable=False, comment='SOP8')
    DFN8 = Column(Integer, nullable=False, name='DFN8L(2X2X0.5-P0.5)', comment='DFN8')
    SOP16_12R = Column(Integer, nullable=False, name='SOP16(12R)', comment='SOP16(12R)')
    SOP16 = Column(Integer, nullable=False, comment='SOP16')
    SOP14_12R = Column(Integer, nullable=False, name='SOP14(12R)', comment='SOP14(12R)')
    SOP14 = Column(Integer, nullable=False, comment='SOP14')
    TSSOP20L = Column(Integer, nullable=False, name='TSSOP20L', comment='TSSOP20L')
    SOT26_14R = Column(Integer, nullable=False, name='SOT26(14R)', comment='SOT26(14R)')
    SOT25_20R = Column(Integer, nullable=False, name='SOT25(20R)', comment='SOT25(20R)')
    SOT25_14R = Column(Integer, nullable=False, name='SOT25(14R)', comment='SOT25(14R)')
    SSOP24 = Column(Integer, nullable=False, comment='SSOP24')
    ESSOP10 = Column(Integer, nullable=False, comment='ESSOP10')
    QFN20 = Column(Integer, nullable=False, name='QFN20L(3X3X0.5-P0.4)', comment='QFN20L(3X3X0.5-P0.4)')
    LQFP32 = Column(Integer, nullable=False, name='LQFP32L(7X7)', comment='LQFP32L(7X7)')
