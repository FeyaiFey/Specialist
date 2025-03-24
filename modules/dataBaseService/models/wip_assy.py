from sqlalchemy import Column, String, Integer, Date, DateTime
from service.dataBaseService.models.base import BaseModel
from datetime import date, datetime

class WipAssy(BaseModel):
    """WIP 装配数据模型"""
    __tablename__ = 'huaxinAdmin_wip_assy'
    
    # 主键
    订单号 = Column(String(255), primary_key=True, nullable=False, comment='订单号')
    封装厂 = Column(String(255), nullable=False, comment='封装厂')
    
    # 状态信息
    当前工序 = Column(String(255), nullable=True, comment='当前工序')
    预计交期 = Column(Date, nullable=True, comment='预计交期')
    
    # 预计数量
    次日预计 = Column(Integer, nullable=True, comment='次日预计')
    三日预计 = Column(Integer, nullable=True, comment='三日预计')
    七日预计 = Column(Integer, nullable=True, comment='七日预计')
    
    # 库存信息
    仓库库存 = Column(Integer, nullable=True, comment='仓库库存')
    扣留信息 = Column(String(255), nullable=True, comment='扣留信息')
    在线合计 = Column(Integer, nullable=True, comment='在线合计')
    
    # 工序数量
    研磨 = Column(Integer, nullable=True, comment='研磨')
    切割 = Column(Integer, nullable=True, comment='切割')
    待装片 = Column(Integer, nullable=True, comment='待装片')
    装片 = Column(Integer, nullable=True, comment='装片')
    银胶固化 = Column(Integer, nullable=True, comment='银胶固化')
    等离子清洗1 = Column(Integer, nullable=True, comment='等离子清洗1')
    键合 = Column(Integer, nullable=True, comment='键合')
    三目检 = Column(Integer, nullable=True, comment='三目检')
    等离子清洗2 = Column(Integer, nullable=True, comment='等离子清洗2')
    塑封 = Column(Integer, nullable=True, comment='塑封')
    后固化 = Column(Integer, nullable=True, comment='后固化')
    回流焊 = Column(Integer, nullable=True, comment='回流焊')
    电镀 = Column(Integer, nullable=True, comment='电镀')
    打印 = Column(Integer, nullable=True, comment='打印')
    后切割 = Column(Integer, nullable=True, comment='后切割')
    切筋成型 = Column(Integer, nullable=True, comment='切筋成型')
    测编打印 = Column(Integer, nullable=True, comment='测编打印')
    外观检 = Column(Integer, nullable=True, comment='外观检')
    包装 = Column(Integer, nullable=True, comment='包装')
    待入库 = Column(Integer, nullable=True, comment='待入库')
    
    # 时间信息
    finished_at = Column(Date, nullable=True, comment='完成时间')
    
    def __repr__(self):
        """返回模型的字符串表示"""
        return f"<WipAssy(订单号='{self.订单号}', 封装厂='{self.封装厂}', 当前工序='{self.当前工序}')>"
    
    @property
    def is_completed(self):
        """判断是否完成"""
        return bool(self.finished_at)
    
    def mark_as_completed(self, completion_date: date = None):
        """标记为已完成"""
        self.finished_at = completion_date or date.today()
        self.当前工序 = '已完成'
        self.预计交期 = None
        self.次日预计 = None
        self.三日预计 = None
        self.七日预计 = None
        self.仓库库存 = None
        self.扣留信息 = None
        self.在线合计 = None
        self.研磨 = None
        self.切割 = None
        self.待装片 = None
        self.装片 = None
        self.银胶固化 = None
        self.等离子清洗1 = None
        self.键合 = None
        self.三目检 = None
        self.等离子清洗2 = None
        self.塑封 = None
        self.后固化 = None
        self.回流焊 = None
        self.电镀 = None
        self.打印 = None
        self.后切割 = None
        self.切筋成型 = None
        self.测编打印 = None
        self.外观检 = None
        self.包装 = None
        self.待入库 = None
    
    def to_dict(self):
        """转换为字典格式"""
        return {
            '订单号': self.订单号,
            '封装厂': self.封装厂,
            '当前工序': self.当前工序,
            '预计交期': self.预计交期.isoformat() if self.预计交期 else None,
            '次日预计': self.次日预计,
            '三日预计': self.三日预计,
            '七日预计': self.七日预计,
            '仓库库存': self.仓库库存,
            '扣留信息': self.扣留信息,
            '在线合计': self.在线合计,
            '研磨': self.研磨,
            '切割': self.切割,
            '待装片': self.待装片,
            '装片': self.装片,
            '银胶固化': self.银胶固化,
            '等离子清洗1': self.等离子清洗1,
            '键合': self.键合,
            '三目检': self.三目检,
            '等离子清洗2': self.等离子清洗2,
            '塑封': self.塑封,
            '后固化': self.后固化,
            '回流焊': self.回流焊,
            '电镀': self.电镀,
            '打印': self.打印,
            '后切割': self.后切割,
            '切筋成型': self.切筋成型,
            '测编打印': self.测编打印,
            '外观检': self.外观检,
            '包装': self.包装,
            '待入库': self.待入库,
            'finished_at': self.finished_at.isoformat() if self.finished_at else None,
            'create_at': self.create_at.isoformat() if self.create_at else None,
            'modified_at': self.modified_at.isoformat() if self.modified_at else None
        }
