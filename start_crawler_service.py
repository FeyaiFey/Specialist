#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
爬虫服务启动脚本
定时爬取网站数据
"""

import signal
import sys
import time
from app.utils.logger import get_service_logger
from app.modules.crawler.crawlerService import CrawlerService

# 创建服务专用日志记录器
SERVICE_NAME = 'crawler_service'
logger = get_service_logger(SERVICE_NAME)

def signal_handler(signum, frame):
    """信号处理函数，用于优雅地停止服务"""
    logger.info("正在停止爬虫服务...")
    service.stop()
    sys.exit(0)

if __name__ == "__main__":
    # 注册信号处理
    signal.signal(signal.SIGINT, signal_handler)  # Ctrl+C
    signal.signal(signal.SIGTERM, signal_handler)  # 终止信号

    # 创建爬虫服务
    service = CrawlerService()
    
    try:
        # 启动服务，每小时执行一次
        logger.info(f"启动{SERVICE_NAME}，每1小时执行一次...")
        service.start(hours=1)
        
        # 保持程序运行
        while True:
            time.sleep(1)
            
    except KeyboardInterrupt:
        # 优雅地停止服务
        logger.info("正在停止爬虫服务...")
        service.stop()
    except Exception as e:
        logger.error(f"爬虫服务发生错误: {str(e)}")
        service.stop()
        sys.exit(1) 