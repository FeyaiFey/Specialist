from typing import Any, Callable, Dict, Optional, TypeVar
from datetime import datetime, timedelta
import functools
import threading

from utils.logger import Logger

logger = Logger().get_logger('cache')

T = TypeVar('T')

class TimedCache:
    """带有时间过期的缓存装饰器"""
    
    def __init__(self, seconds: int = 300):
        """
        初始化缓存
        Args:
            seconds: 缓存过期时间（秒）
        """
        self.seconds = seconds
        self.cache: Dict[str, Dict[str, Any]] = {}
        self.lock = threading.Lock()
    
    def __call__(self, func: Callable[..., T]) -> Callable[..., T]:
        """
        装饰器实现
        Args:
            func: 被装饰的函数
        Returns:
            装饰后的函数
        """
        @functools.wraps(func)
        def wrapper(*args, **kwargs) -> T:
            # 生成缓存键
            cache_key = self._generate_key(func, *args, **kwargs)
            
            with self.lock:
                # 检查缓存是否存在且未过期
                if cache_key in self.cache:
                    cache_data = self.cache[cache_key]
                    if datetime.now() < cache_data['expire_time']:
                        logger.debug(f"Cache hit for {func.__name__}")
                        return cache_data['value']
                
                # 缓存不存在或已过期，执行函数
                result = func(*args, **kwargs)
                
                # 更新缓存
                self.cache[cache_key] = {
                    'value': result,
                    'expire_time': datetime.now() + timedelta(seconds=self.seconds)
                }
                logger.debug(f"Cache updated for {func.__name__}")
                return result
        
        # 添加缓存控制方法到包装函数
        wrapper.cache_clear = self.clear  # type: ignore
        wrapper.cache_remove = self.remove  # type: ignore
        wrapper.cache_info = self.get_info  # type: ignore
        
        return wrapper
    
    def _generate_key(self, func: Callable, *args, **kwargs) -> str:
        """
        生成缓存键
        Args:
            func: 函数
            *args: 位置参数
            **kwargs: 关键字参数
        Returns:
            缓存键
        """
        # 将参数转换为字符串
        args_str = ','.join(str(arg) for arg in args)
        kwargs_str = ','.join(f"{k}={v}" for k, v in sorted(kwargs.items()))
        return f"{func.__name__}:{args_str}:{kwargs_str}"
    
    def clear(self) -> None:
        """清除所有缓存"""
        with self.lock:
            self.cache.clear()
            logger.debug("Cache cleared")
    
    def remove(self, func: Callable, *args, **kwargs) -> None:
        """
        移除特定的缓存项
        Args:
            func: 函数
            *args: 位置参数
            **kwargs: 关键字参数
        """
        cache_key = self._generate_key(func, *args, **kwargs)
        with self.lock:
            if cache_key in self.cache:
                del self.cache[cache_key]
                logger.debug(f"Cache removed for {func.__name__}")
    
    def get_info(self) -> Dict[str, Any]:
        """
        获取缓存信息
        Returns:
            缓存统计信息
        """
        with self.lock:
            now = datetime.now()
            active_items = sum(
                1 for item in self.cache.values()
                if item['expire_time'] > now
            )
            return {
                'total_items': len(self.cache),
                'active_items': active_items,
                'expired_items': len(self.cache) - active_items
            }

# 创建一些预定义的缓存装饰器
cache_5min = TimedCache(seconds=300)  # 5分钟缓存
cache_1hour = TimedCache(seconds=3600)  # 1小时缓存
cache_1day = TimedCache(seconds=86400)  # 1天缓存

# 使用Python内置的LRU缓存
cache_lru = functools.lru_cache(maxsize=128, typed=False) 