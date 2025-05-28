import os
from pathlib import Path

# 项目基本路径
BASE_DIR = Path(__file__).resolve().parent.parent

# 日志配置
LOG_CONFIG = {
    # 日志文件路径
    'LOG_DIR': os.path.join(BASE_DIR, 'logs'),
    # 日志文件名格式
    'LOG_FILENAME': 'Agent_{time}.log',
    # 日志级别
    'LOG_LEVEL': 'DEBUG',
    # 日志格式
    'LOG_FORMAT': '<green>{time:YYYY-MM-DD HH:mm:ss.SSS}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - <level>{message}</level>',
    # 日志轮转设置
    'LOG_ROTATION': '10 MB',
    # 保留日志文件数量
    'LOG_RETENTION': '1 week',
    # 是否压缩归档的日志文件
    'LOG_COMPRESSION': 'zip',
}

# 邮件服务配置
EMAIL_CONFIG = {
    'IMAP_SERVER': 'p220s.chinaemail.cn',
    'IMAP_PORT': 993,
    'IMAP_USERNAME': 'wxb1@h-sun.com',
    'IMAP_PASSWORD': '496795ef2tsWaJol'
}

# 数据库配置
DB_CONFIG = {
    'DB_USER': 'sa',
    'DB_PASSWORD': 'P@ssw0rd',
    'DB_HOST': '192.168.200.21',
    'DB_DATABASE': 'E10',
    'DB_DRIVER': 'ODBC Driver 18 for SQL Server',
    'DB_POOL_SIZE': 5,
    'DB_MAX_OVERFLOW': 10,
    'DB_POOL_TIMEOUT': 30,
    'DB_POOL_RECYCLE': 3600,
    'DB_ECHO': False
}

# 其他应用程序配置
APP_CONFIG = {
    'DEBUG': True,
    'TIMEOUT': 30,
    'MAX_RETRIES': 3,
} 

# 邮件规则配置
EMAIL_RULES_FILE = "app/config/email_rules.yaml"

# 爬虫网站信息
# 和舰科技
HJTC_USERNAME="HUX_LEIHJ"
HJTC_PASSWORD="UNBfg-241113"
HJTC_OUTPUT_DIR="downloads/晶圆进度表/和舰科技"

# 江苏芯丰
XINF_USERNAME="314"
XINF_PASSWORD="68241373"
XINF_OUTPUT_DIR="downloads/封装进度表/江苏芯丰"

# 长电科技
JCET_USERNAME="A2-099"
JCET_PASSWORD="Tel68241373$"
JCET_OUTPUT_DIR="downloads/封装进度表/长电科技"