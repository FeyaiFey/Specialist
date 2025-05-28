import signal
import sys
import time

from app.utils.logger import Logger
from app.modules.dataBaseService.batchUploadDataBase import HisemiWipAnalyzeService

logger = Logger().get_logger('hisemi_wip_analyze')

service = HisemiWipAnalyzeService() 

def signal_handler(signum, frame):
    """信号处理函数，用于优雅地停止服务"""
    logger.info("\n正在停止服务...")
    service.stop()
    sys.exit(0)

if __name__ == "__main__":
    # 注册信号处理
    signal.signal(signal.SIGINT, signal_handler)  # Ctrl+C
    signal.signal(signal.SIGTERM, signal_handler)  # 终止信号

    try:
        # 启动服务
        service.start(hour=8, minute=37)

        # 保持程序运行
        while True:
            time.sleep(1)
            
    except KeyboardInterrupt:
        # 优雅地停止服务
        logger.info("\n正在停止服务...")
        service.stop()

