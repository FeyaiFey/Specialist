import logging
import os
import yaml
from datetime import datetime
from pathlib import Path
from logging.handlers import RotatingFileHandler

# 添加颜色支持
class ColoredFormatter(logging.Formatter):
    """自定义彩色日志格式化器"""
    
    # 定义颜色代码
    COLORS = {
        'DEBUG': '\033[36m',    # 青色
        'INFO': '\033[32m',     # 绿色
        'WARNING': '\033[33m',  # 黄色
        'ERROR': '\033[31m',    # 红色
        'CRITICAL': '\033[35m', # 紫色
        'RESET': '\033[0m'      # 重置颜色
    }

    def format(self, record):
        # 添加颜色
        if record.levelname in self.COLORS:
            record.levelname = f"{self.COLORS[record.levelname]}{record.levelname}{self.COLORS['RESET']}"
        return super().format(record)

def load_config():
    """
    加载YAML配置文件
    :return: 配置字典
    """
    config_path = Path(__file__).parent.parent / 'config' / 'log_config.yaml'
    with open(config_path, 'r', encoding='utf-8') as f:
        return yaml.safe_load(f)

def get_log_file_path(date, config, module_name=None, log_type='all'):
    """
    获取日志文件路径
    :param date: 日期
    :param config: 配置字典
    :param module_name: 模块名称
    :param log_type: 日志类型（all/error）
    :return: 日志文件完整路径
    """
    log_dir = config['log_dir']
    
    # 创建基础日志目录
    if not os.path.exists(log_dir):
        os.makedirs(log_dir)
    
    # 按日期组织目录
    date_dir = os.path.join(log_dir, date)
    if not os.path.exists(date_dir):
        os.makedirs(date_dir)
    
    if log_type == 'error':
        # 错误日志单独存放在日期目录下的error子目录
        error_dir = os.path.join(date_dir, 'error')
        if not os.path.exists(error_dir):
            os.makedirs(error_dir)
        file_name = f'{date}.log'
        return os.path.join(error_dir, file_name)
    else:
        # 普通日志按模块名分类
        if module_name:
            module_dir = os.path.join(date_dir, module_name)
            if not os.path.exists(module_dir):
                os.makedirs(module_dir)
            file_name = f'{module_name}.log'
            return os.path.join(module_dir, file_name)
        else:
            # 全局日志
            file_name = f'all.log'
            return os.path.join(date_dir, file_name)

class Logger:
    _instance = None
    _loggers = {}
    _config = None
    _all_logger = None
    _error_logger = None
    _current_date = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(Logger, cls).__new__(cls)
        return cls._instance

    def __init__(self):
        if not hasattr(self, 'initialized'):
            self._config = load_config()
            self.log_dir = self._config['log_dir']
            self._current_date = datetime.now().strftime(self._config['date_format'])
            self._setup_global_loggers()
            self.initialized = True

    def _setup_global_loggers(self):
        """设置全局日志记录器（汇总日志和错误日志）"""
        
        # 设置汇总日志记录器
        self._all_logger = logging.getLogger('all')
        self._all_logger.setLevel(self._config['log_levels']['DEBUG'])
        self._all_logger.handlers = []  # 清除已有的处理器
        
        all_log_file = get_log_file_path(self._current_date, self._config)
        all_handler = RotatingFileHandler(
            all_log_file,
            maxBytes=self._config['file_config']['max_bytes'],
            backupCount=self._config['file_config']['backup_count'],
            encoding=self._config['file_config']['encoding']
        )
        all_handler.setLevel(self._config['log_levels'][self._config['levels']['file']])
        all_formatter = logging.Formatter(
            self._config['format']['default'],
            datefmt=self._config['time_format']
        )
        all_handler.setFormatter(all_formatter)
        self._all_logger.addHandler(all_handler)

        # 设置错误日志记录器
        self._error_logger = logging.getLogger('error')
        self._error_logger.setLevel(self._config['log_levels']['ERROR'])
        self._error_logger.handlers = []  # 清除已有的处理器
        
        error_log_file = get_log_file_path(self._current_date, self._config, log_type='error')
        error_handler = RotatingFileHandler(
            error_log_file,
            maxBytes=self._config['file_config']['max_bytes'],
            backupCount=self._config['file_config']['backup_count'],
            encoding=self._config['file_config']['encoding']
        )
        error_handler.setLevel(self._config['log_levels']['ERROR'])
        error_formatter = logging.Formatter(
            self._config['format']['default'],
            datefmt=self._config['time_format']
        )
        error_handler.setFormatter(error_formatter)
        self._error_logger.addHandler(error_handler)

    def _check_date_change(self):
        """检查日期是否变化，如果变化则更新日志文件路径"""
        current_date = datetime.now().strftime(self._config['date_format'])
        if current_date != self._current_date:
            self._current_date = current_date
            self._setup_global_loggers()
            # 更新所有已创建的模块日志记录器
            for module_name, logger in self._loggers.items():
                self._update_module_logger(module_name, logger)

    def _update_module_logger(self, module_name, logger):
        """更新模块日志记录器的文件处理器"""
        # 移除旧的文件处理器
        for handler in logger.handlers[:]:
            if isinstance(handler, RotatingFileHandler):
                logger.removeHandler(handler)
        
        # 添加新的文件处理器
        module_log_file = get_log_file_path(self._current_date, self._config, module_name)
        file_handler = RotatingFileHandler(
            module_log_file,
            maxBytes=self._config['file_config']['max_bytes'],
            backupCount=self._config['file_config']['backup_count'],
            encoding=self._config['file_config']['encoding']
        )
        file_handler.setLevel(self._config['log_levels'][self._config['levels']['file']])
        formatter = logging.Formatter(
            self._config['format']['default'],
            datefmt=self._config['time_format']
        )
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)

    def get_logger(self, module_name):
        """
        获取指定模块的日志记录器
        :param module_name: 模块名称
        :return: 日志记录器
        """
        # 检查日期是否变化
        self._check_date_change()
        
        if module_name not in self._loggers:
            logger = logging.getLogger(module_name)
            logger.setLevel(self._config['log_levels']['DEBUG'])
            logger.handlers = []  # 清除已有的处理器

            # 控制台处理器
            console_handler = logging.StreamHandler()
            console_handler.setLevel(self._config['log_levels'][self._config['levels']['console']])

            # 模块专用文件处理器
            module_log_file = get_log_file_path(self._current_date, self._config, module_name)
            file_handler = RotatingFileHandler(
                module_log_file,
                maxBytes=self._config['file_config']['max_bytes'],
                backupCount=self._config['file_config']['backup_count'],
                encoding=self._config['file_config']['encoding']
            )
            file_handler.setLevel(self._config['log_levels'][self._config['levels']['file']])

            # 设置日志格式
            formatter = logging.Formatter(
                self._config['format']['default'],
                datefmt=self._config['time_format']
            )
            console_formatter = ColoredFormatter(
                self._config['format']['default'],
                datefmt=self._config['time_format']
            )

            # 添加处理器
            console_handler.setFormatter(console_formatter)
            file_handler.setFormatter(formatter)
            logger.addHandler(console_handler)
            logger.addHandler(file_handler)

            # 添加全局日志处理器
            class GlobalLogHandler(logging.Handler):
                def __init__(self, all_logger, error_logger):
                    super().__init__()
                    self.all_logger = all_logger
                    self.error_logger = error_logger

                def emit(self, record):
                    # 记录到汇总日志
                    self.all_logger.handle(record)
                    # 如果是错误级别，记录到错误日志
                    if record.levelno >= logging.ERROR:
                        self.error_logger.handle(record)

            global_handler = GlobalLogHandler(self._all_logger, self._error_logger)
            global_handler.setFormatter(formatter)
            logger.addHandler(global_handler)

            self._loggers[module_name] = logger

        return self._loggers[module_name]

# 使用示例
if __name__ == '__main__':
    # 获取不同模块的日志记录器
    logger = Logger()
    user_logger = logger.get_logger('user_module')
    order_logger = logger.get_logger('order_module')

    # 测试日志记录
    user_logger.debug('用户模块调试日志')
    user_logger.info('用户模块信息日志')
    user_logger.warning('用户模块警告日志')
    user_logger.error('用户模块错误日志')
    user_logger.critical('用户模块严重错误日志')
    
    order_logger.info('订单模块信息日志')
    order_logger.error('订单模块错误日志') 