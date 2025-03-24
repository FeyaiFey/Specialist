import signal
import sys
import time

from modules.crawler.crawlerService import CrawlerService
from utils.logger import Logger

logger = Logger().get_logger('crawler')

def signal_handler(signum, frame):
    """信号处理函数，用于优雅地停止服务"""
    print("\n正在停止爬虫服务...")
    service.stop()
    sys.exit(0)

if __name__ == "__main__":
    # 注册信号处理
    signal.signal(signal.SIGINT, signal_handler)  # Ctrl+C
    signal.signal(signal.SIGTERM, signal_handler)  # 终止信号

    # 创建爬虫服务
    service = CrawlerService()
    
    try:
        # 启动服务
        service.start(hours=1)
        
        # 保持程序运行
        while True:
            time.sleep(1)
            
    except KeyboardInterrupt:
        # 优雅地停止服务
        logger.info("\n正在停止爬虫服务...")
        service.stop()
    except Exception as e:
        logger.error(f"发生错误: {str(e)}")
        service.stop()

