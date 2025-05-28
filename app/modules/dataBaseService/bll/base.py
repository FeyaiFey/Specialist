from typing import TypeVar, Generic, Type
from app.modules.dataBaseService.dal.base import BaseDAL
from app.modules.dataBaseService.models.base import BaseModel

T = TypeVar('T', bound=BaseModel)

class BaseBLL(Generic[T]):
    """基础业务逻辑类"""
    
    def __init__(self, dal_class: Type[BaseDAL]):
        """
        初始化
        Args:
            dal_class: 数据访问层类
        """
        self.dal = dal_class() 