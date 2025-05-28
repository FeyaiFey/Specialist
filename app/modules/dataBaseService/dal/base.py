from typing import TypeVar, Generic, List, Optional, Type, Any
from sqlalchemy.orm import Session
from sqlalchemy import select, update, delete
from app.modules.dataBaseService.models.base import BaseModel

# 定义泛型类型变量
T = TypeVar('T', bound=BaseModel)

class BaseDAL(Generic[T]):
    """基础数据访问层"""
    
    def __init__(self, model_class: Type[T]):
        """
        初始化
        Args:
            model_class: 模型类
        """
        self.model_class = model_class
    
    def get_by_id(self, session: Session, id_value: Any) -> Optional[T]:
        """
        通过ID获取记录
        Args:
            session: 数据库会话
            id_value: ID值
        Returns:
            记录对象或None
        """
        return session.get(self.model_class, id_value)
    
    def get_all(self, session: Session) -> List[T]:
        """
        获取所有记录
        Args:
            session: 数据库会话
        Returns:
            记录列表
        """
        stmt = select(self.model_class)
        return list(session.execute(stmt).scalars())
    
    def create(self, session: Session, **kwargs) -> T:
        """
        创建新记录
        Args:
            session: 数据库会话
            **kwargs: 模型字段值
        Returns:
            新创建的记录
        """
        instance = self.model_class(**kwargs)
        session.add(instance)
        session.flush()  # 刷新以获取数据库生成的值
        return instance
    
    def update(self, session: Session, id_value: Any, **kwargs) -> Optional[T]:
        """
        更新记录
        Args:
            session: 数据库会话
            id_value: ID值
            **kwargs: 要更新的字段值
        Returns:
            更新后的记录或None
        """
        instance = self.get_by_id(session, id_value)
        if instance:
            for key, value in kwargs.items():
                setattr(instance, key, value)
            session.flush()
        return instance
    
    def delete(self, session: Session, id_value: Any) -> bool:
        """
        删除记录
        Args:
            session: 数据库会话
            id_value: ID值
        Returns:
            是否删除成功
        """
        instance = self.get_by_id(session, id_value)
        if instance:
            session.delete(instance)
            session.flush()
            return True
        return False
    
    def exists(self, session: Session, id_value: Any) -> bool:
        """
        检查记录是否存在
        Args:
            session: 数据库会话
            id_value: ID值
        Returns:
            是否存在
        """
        return self.get_by_id(session, id_value) is not None 