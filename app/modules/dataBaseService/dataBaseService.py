import os
from typing import Optional
from sqlalchemy import create_engine, Engine
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.pool import QueuePool
from sqlalchemy.exc import SQLAlchemyError
from threading import Lock

from app.utils.logger import get_logger
from app.config import DB_CONFIG

class DataBaseService:
    """数据库服务类"""
    _engine: Optional[Engine] = None
    _session_maker: Optional[sessionmaker] = None
    _lock = Lock()
    
    def __init__(self):
        """初始化数据库服务"""
        self.logger = get_logger(__name__)
        if self._engine is None:
            with self._lock:
                if self._engine is None:
                    self._initialize()

    def _initialize(self):
        """初始化数据库连接"""
        try:
            # 构建连接字符串
            server = DB_CONFIG["DB_HOST"]
            database = DB_CONFIG["DB_DATABASE"]
            driver = DB_CONFIG["DB_DRIVER"]
            username = DB_CONFIG["DB_USER"]
            password = DB_CONFIG["DB_PASSWORD"]
            
            # 构建ODBC连接字符串
            conn_str = (
                f"DRIVER={{{driver}}};"
                f"SERVER={server};"
                f"DATABASE={database};"
                f"UID={username};"
                f"PWD={password};"
                f"TrustServerCertificate=yes"
            )
            
            # URL编码连接字符串
            # encoded_conn_str = quote_plus(conn_str)
            
            # 创建引擎（使用正确的SQLAlchemy URL格式）
            self._engine = create_engine(
                f"mssql+pyodbc:///?odbc_connect={conn_str}",
                poolclass=QueuePool,
                pool_size=int(DB_CONFIG["DB_POOL_SIZE"]),
                max_overflow=int(DB_CONFIG["DB_MAX_OVERFLOW"]),
                pool_timeout=int(DB_CONFIG["DB_POOL_TIMEOUT"]),
                pool_recycle=int(DB_CONFIG["DB_POOL_RECYCLE"]),
                echo=DB_CONFIG["DB_ECHO"]
            )
            
            # 创建会话工厂
            self._session_maker = sessionmaker(
                bind=self._engine,
                autocommit=False,
                autoflush=False
            )
            
            self.logger.info(f"数据库连接池初始化成功: {server}/{database}")

        except Exception as e:
            self.logger.error(f"数据库连接池初始化失败: {str(e)}")
            raise

    def get_session(self) -> Session:
        """获取数据库会话"""
        if self._session_maker is None:
            raise RuntimeError("数据库服务未正确初始化")
        return self._session_maker()

class DatabaseSession:
    """数据库会话上下文管理器"""
    
    def __init__(self):
        self.logger = get_logger(__name__)
        self.db = DataBaseService()
        self.session: Optional[Session] = None
    
    def __enter__(self) -> Session:
        """进入上下文，返回会话对象"""
        self.session = self.db.get_session()
        return self.session
    
    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        """退出上下文，处理会话清理"""
        if self.session:
            try:
                if exc_type is None:
                    # 如果没有异常发生，提交事务
                    self.session.commit()
                else:
                    # 如果有异常发生，回滚事务
                    self.session.rollback()
                    self.logger.error(f"数据库操作失败: {str(exc_val)}")
            except SQLAlchemyError as e:
                self.session.rollback()
                self.logger.error(f"数据库事务处理失败: {str(e)}")
            finally:
                self.session.close()