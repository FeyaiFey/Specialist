import signal
import sys
import time
import threading
from concurrent.futures import ThreadPoolExecutor

from modules.crawler.crawlerService import CrawlerService
from modules.emailPolling.emailProcess import EmailProcess
from modules.dataBaseService.batchUploadDataBase import HisemiWipAnalyzeService
from utils.logger import Logger

# 初始化日志
logger = Logger().get_logger('main')

# 服务实例
services = {
    'crawler': CrawlerService(),
    'email_polling': EmailProcess(),
    'hisemi_wip': HisemiWipAnalyzeService()
}

def start_service(service_name, service_instance):
    """启动单个服务"""
    try:
        logger.info(f"正在启动 {service_name} 服务...")
        if service_name == 'crawler':
            service_instance.start(hours=1)
        elif service_name == 'email_polling':
            service_instance.start(minutes=10)
        elif service_name == 'hisemi_wip':
            service_instance.start(hour=8, minute=37)
    except Exception as e:
        logger.error(f"{service_name} 服务启动失败: {str(e)}")

def stop_services():
    """停止所有服务"""
    logger.info("正在停止所有服务...")
    for name, service in services.items():
        try:
            logger.info(f"正在停止 {name} 服务...")
            service.stop()
        except Exception as e:
            logger.error(f"停止 {name} 服务时发生错误: {str(e)}")

def signal_handler(signum, frame):
    """信号处理函数，用于优雅地停止所有服务"""
    logger.info("\n收到终止信号，正在停止所有服务...")
    stop_services()
    sys.exit(0)

def main():
    # 注册信号处理
    signal.signal(signal.SIGINT, signal_handler)  # Ctrl+C
    signal.signal(signal.SIGTERM, signal_handler)  # 终止信号

    try:
        # 使用线程池启动所有服务
        with ThreadPoolExecutor(max_workers=len(services)) as executor:
            futures = []
            for name, service in services.items():
                future = executor.submit(start_service, name, service)
                futures.append(future)

            # 等待所有服务启动完成
            for future in futures:
                future.result()

        # 保持主线程运行
        while True:
            time.sleep(1)

    except KeyboardInterrupt:
        logger.info("\n收到键盘中断信号，正在停止所有服务...")
        stop_services()
    except Exception as e:
        logger.error(f"发生错误: {str(e)}")
        stop_services()

if __name__ == "__main__":
    main() 