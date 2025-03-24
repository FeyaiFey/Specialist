from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy import Column, DateTime, func
from datetime import datetime

Base = declarative_base()

class BaseModel(Base):
    """所有模型的基类"""
    __abstract__ = True  # 声明这是一个抽象基类
    
    # 通用字段
    create_at = Column(DateTime, default=datetime.now, server_default=func.sysdatetime())
    modified_at = Column(DateTime, default=datetime.now, onupdate=datetime.now, server_default=func.sysdatetime()) 