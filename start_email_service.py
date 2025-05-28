#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
邮箱服务启动脚本
每隔1小时自动检查并处理邮件
"""

import sys
import signal
from app.email_poller import EmailPoller
from app.utils.logger import get_service_logger

# 创建服务专用日志记录器
SERVICE_NAME = 'email_service'
logger = get_service_logger(SERVICE_NAME)

def signal_handler(signum, frame):
    """信号处理函数，用于优雅地停止服务"""
    logger.info("正在停止邮箱服务...")
    sys.exit(0)

if __name__ == "__main__":
    # 注册信号处理
    signal.signal(signal.SIGINT, signal_handler)  # Ctrl+C
    signal.signal(signal.SIGTERM, signal_handler)  # 终止信号
    
    try:
        logger.info(f"启动{SERVICE_NAME}，每10分钟自动检查一次邮件...")
        poller = EmailPoller()
        poller.start(minutes=10)
    except Exception as e:
        logger.error(f"邮箱服务发生错误: {str(e)}")
        sys.exit(1) 