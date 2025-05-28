#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Hisemi WIP分析服务启动脚本
定时分析并上传数据库
"""

import signal
import sys
import time
from app.utils.logger import get_service_logger
from app.modules.dataBaseService.batchUploadDataBase import HisemiWipAnalyzeService

# 创建服务专用日志记录器
SERVICE_NAME = 'hisemi_service'
logger = get_service_logger(SERVICE_NAME)

def signal_handler(signum, frame):
    """信号处理函数，用于优雅地停止服务"""
    logger.info("正在停止Hisemi WIP分析服务...")
    service.stop()
    sys.exit(0)

if __name__ == "__main__":
    # 注册信号处理
    signal.signal(signal.SIGINT, signal_handler)  # Ctrl+C
    signal.signal(signal.SIGTERM, signal_handler)  # 终止信号

    # 创建服务实例
    service = HisemiWipAnalyzeService() 

    try:
        # 启动服务，设置定时运行时间
        logger.info(f"启动{SERVICE_NAME}...")
        service.start(hour=8, minute=30)

        # 保持程序运行
        while True:
            time.sleep(1)
            
    except KeyboardInterrupt:
        # 优雅地停止服务
        logger.info("正在停止Hisemi WIP分析服务...")
        service.stop()
    except Exception as e:
        logger.error(f"Hisemi WIP分析服务发生错误: {str(e)}")
        service.stop()
        sys.exit(1) 