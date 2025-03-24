from sqlalchemy import Column, String, Integer, Date, DateTime
from modules.dataBaseService.models.base import BaseModel
from datetime import date, datetime

class WipFab(BaseModel):
    """WIP FAB数据模型"""
    __tablename__ = 'huaxinAdmin_wip_fab'
    
    # 主键
    lot = Column(String(255), primary_key=True, nullable=False, comment='批次号')
    
    # 基本信息
    purchaseOrder = Column(String(255), nullable=True, comment='采购订单号')
    itemName = Column(String(255), nullable=True, comment='产品名称')
    qty = Column(Integer, nullable=True, comment='数量')
    supplier = Column(String(255), nullable=True, comment='供应商')
    
    # 状态信息
    status = Column(String(255), nullable=True, comment='状态')
    stage = Column(String(255), nullable=True, comment='阶段')
    
    # 层数信息
    layerCount = Column(Integer, nullable=True, comment='总层数')
    remainLayer = Column(Integer, nullable=True, comment='剩余层数')
    
    # 位置和时间
    currentPosition = Column(Integer, nullable=True, comment='当前位置')
    forecastDate = Column(Date, nullable=True, comment='预计完成日期')
    finished_at = Column(Date, nullable=True, comment='完工日期')
    
    def __repr__(self):
        """返回模型的字符串表示"""
        return f"<WipFab(lot='{self.lot}', itemName='{self.itemName}', status='{self.status}')>"
    
    @property
    def completion_rate(self):
        """计算完成率"""
        if not self.layerCount or self.layerCount == 0:
            return 0
        completed_layers = self.layerCount - (self.remainLayer or 0)
        return round((completed_layers / self.layerCount) * 100, 2)
    
    @property
    def is_completed(self):
        """判断是否完成"""
        return self.status == "已完结" or (self.remainLayer == 0 if self.remainLayer is not None else False)
    
    def mark_as_completed(self, completion_date: date = None):
        """标记为已完成"""
        self.status = "已完结"
        self.remainLayer = 0
        self.forecastDate = None
        self.finished_at = datetime.now()
        self.currentPosition = None
        self.stage = None
    
    def to_dict(self):
        """转换为字典格式"""
        return {
            'lot': self.lot,
            'purchaseOrder': self.purchaseOrder,
            'itemName': self.itemName,
            'qty': self.qty,
            'status': self.status,
            'stage': self.stage,
            'layerCount': self.layerCount,
            'remainLayer': self.remainLayer,
            'currentPosition': self.currentPosition,
            'forecastDate': self.forecastDate.isoformat() if self.forecastDate else None,
            'supplier': self.supplier,
            'finished_at': self.finished_at.isoformat() if self.finished_at else None,
            'completion_rate': self.completion_rate,
            'create_at': self.create_at.isoformat() if self.create_at else None,
            'modified_at': self.modified_at.isoformat() if self.modified_at else None
        } 