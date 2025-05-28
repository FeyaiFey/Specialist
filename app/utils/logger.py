import os
import sys
from pathlib import Path
from typing import Optional, Dict, Any, Union

from loguru import logger

from app.config import LOG_CONFIG

# 确保日志目录存在
os.makedirs(LOG_CONFIG['LOG_DIR'], exist_ok=True)


class LoggerManager:
    """
    日志管理器类，负责配置和管理loguru日志
    """

    def __init__(self):
        """初始化日志管理器"""
        # 移除默认的控制台处理器
        logger.remove()
        
        # 添加控制台输出处理器（仅在调试模式下显示INFO及以上级别）
        logger.add(
            sys.stdout,
            format=LOG_CONFIG['LOG_FORMAT'],
            level=LOG_CONFIG['LOG_LEVEL'],
            colorize=True,
        )
        
        # 添加文件处理器
        log_path = os.path.join(LOG_CONFIG['LOG_DIR'], LOG_CONFIG['LOG_FILENAME'])
        logger.add(
            log_path,
            format=LOG_CONFIG['LOG_FORMAT'],
            level=LOG_CONFIG['LOG_LEVEL'],
            rotation=LOG_CONFIG['LOG_ROTATION'],
            retention=LOG_CONFIG['LOG_RETENTION'],
            compression=LOG_CONFIG['LOG_COMPRESSION'],
        )
        
    def get_logger(self, name: str = "specialist"):
        """
        获取带有上下文的logger实例
        
        Args:
            name: 日志记录器名称，默认为specialist
            
        Returns:
            带有上下文的logger实例
        """
        return logger.bind(name=name)
    
    def get_service_logger(self, service_name: str):
        """
        获取特定服务的日志记录器，日志将分离到单独的文件中
        
        Args:
            service_name: 服务名称，用于标识日志记录器和日志文件
            
        Returns:
            服务专用的logger实例
        """
        # 创建服务专用日志目录
        service_log_dir = os.path.join(LOG_CONFIG['LOG_DIR'], service_name)
        os.makedirs(service_log_dir, exist_ok=True)
        
        # 创建服务主日志文件路径
        service_log_file = os.path.join(service_log_dir, f"{service_name}.log")
        
        # 创建服务错误日志文件路径
        error_log_file = os.path.join(service_log_dir, f"{service_name}_error.log")
        
        # 创建新的日志处理器ID
        main_id = f"{service_name}_main"
        error_id = f"{service_name}_error"
        
        # 检查处理器是否已存在，避免重复添加
        for handler_id in logger._core.handlers:
            if handler_id == main_id or handler_id == error_id:
                # 返回带有服务名称绑定的logger
                return logger.bind(name=service_name)
        
        # 添加服务主日志文件处理器
        logger.add(
            sink=service_log_file,
            format=LOG_CONFIG['LOG_FORMAT'],
            level=LOG_CONFIG['LOG_LEVEL'],
            rotation=LOG_CONFIG['LOG_ROTATION'],
            retention=LOG_CONFIG['LOG_RETENTION'],
            compression=LOG_CONFIG['LOG_COMPRESSION'],
            filter=lambda record: record["extra"].get("name") == service_name,
            enqueue=True,
            backtrace=True,
            diagnose=True,
            catch=True,
        )
        
        # 添加服务错误日志文件处理器
        logger.add(
            sink=error_log_file,
            format=LOG_CONFIG['LOG_FORMAT'],
            level="ERROR",
            rotation=LOG_CONFIG['LOG_ROTATION'],
            retention=LOG_CONFIG['LOG_RETENTION'],
            compression=LOG_CONFIG['LOG_COMPRESSION'],
            filter=lambda record: record["extra"].get("name") == service_name and record["level"].no >= logger.level("ERROR").no,
            enqueue=True,
            backtrace=True,
            diagnose=True,
            catch=True,
        )
        
        # 返回带有服务名称绑定的logger
        return logger.bind(name=service_name)


# 创建日志管理器单例
log_manager = LoggerManager()

# 默认日志记录器
default_logger = log_manager.get_logger()


# 便捷函数，用于在不同模块中获取特定名称的logger
def get_logger(name: Optional[str] = None):
    """
    获取指定名称的日志记录器
    
    Args:
        name: 模块名称，默认使用调用模块的名称
        
    Returns:
        logger: loguru日志记录器实例
    """
    if name is None:
        import inspect
        # 通过堆栈获取调用模块的名称
        frame = inspect.stack()[1]
        module = inspect.getmodule(frame[0])
        name = module.__name__ if module else "unknown"
    
    return log_manager.get_logger(name)


# 便捷函数，用于获取特定服务的独立日志记录器
def get_service_logger(service_name: str):
    """
    获取特定服务的日志记录器，日志将分离到独立的文件中
    
    Args:
        service_name: 服务名称
        
    Returns:
        logger: 服务专用的loguru日志记录器实例
    """
    return log_manager.get_service_logger(service_name)


# 便捷函数，用于装饰器记录函数调用
def log_function(func):
    """
    函数调用日志装饰器
    
    Args:
        func: 要装饰的函数
    
    Returns:
        装饰后的函数
    """
    import functools
    
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        func_logger = get_logger(func.__module__)
        func_name = f"{func.__module__}.{func.__name__}"
        
        func_logger.debug(f"调用函数 {func_name} - 参数: {args}, 关键字参数: {kwargs}")
        try:
            result = func(*args, **kwargs)
            func_logger.debug(f"函数 {func_name} 执行成功 - 返回: {result}")
            return result
        except Exception as e:
            func_logger.exception(f"函数 {func_name} 执行失败 - 异常: {str(e)}")
            raise
    
    return wrapper


# 导出常用日志函数，方便直接调用
def debug(message: str, **kwargs) -> None:
    """记录调试级别日志"""
    default_logger.debug(message, **kwargs)

def info(message: str, **kwargs) -> None:
    """记录信息级别日志"""
    default_logger.info(message, **kwargs)

def warning(message: str, **kwargs) -> None:
    """记录警告级别日志"""
    default_logger.warning(message, **kwargs)

def error(message: str, **kwargs) -> None:
    """记录错误级别日志"""
    default_logger.error(message, **kwargs)

def critical(message: str, **kwargs) -> None:
    """记录严重级别日志"""
    default_logger.critical(message, **kwargs)

def exception(message: str, **kwargs) -> None:
    """记录异常详情，包括堆栈信息"""
    default_logger.exception(message, **kwargs) 