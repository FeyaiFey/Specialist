"""
爬虫任务服务模块
用于管理和调度各种爬虫任务
"""

import time
from datetime import datetime
from typing import Dict, Type, Optional
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.interval import IntervalTrigger

from utils.logger import Logger
from modules.crawler.base import BaseCrawler
from modules.crawler.xinfCrawler import XinfCrawler
from modules.crawler.hjtcCrawler import HJTCCrawler
from modules.crawler.jcetCrawler import JcetCrawler

class CrawlerService:
    """爬虫任务服务类"""
    
    def __init__(self):
        """初始化爬虫服务"""
        self.logger = Logger().get_logger('crawlerService')
        self.crawlers: Dict[str, Type[BaseCrawler]] = {
            'xinf': XinfCrawler,
            'hjtc': HJTCCrawler,
            'jcet': JcetCrawler
        }
        # 创建后台调度器
        self.scheduler = BackgroundScheduler()
        self.job = None
        
    def run_crawler(self, crawler_name: str) -> bool:
        """运行指定的爬虫任务"""
        try:
            if crawler_name not in self.crawlers:
                self.logger.error(f"未找到爬虫: {crawler_name}")
                return False
                
            self.logger.info(f"开始运行爬虫任务: {crawler_name}")
            crawler = self.crawlers[crawler_name]()
            success = crawler.run()
            
            if success:
                self.logger.info(f"爬虫任务完成: {crawler_name}")
            else:
                self.logger.error(f"爬虫任务失败: {crawler_name}")
                
            return success
            
        except Exception as e:
            self.logger.error(f"运行爬虫任务出错 {crawler_name}: {str(e)}")
            return False
            
    def run_all_crawlers(self) -> None:
        """运行所有爬虫任务"""
        current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        self.logger.info(f"开始运行所有爬虫任务 - {current_time}")
        
        for crawler_name in self.crawlers:
            self.run_crawler(crawler_name)
            
        # 打印下次运行时间
        if self.job:
            next_run_time = self.job.next_run_time
            self.logger.info(f"下次运行时间: {next_run_time}")
            
    def start(self, hours: int = 1) -> None:
        """
        启动爬虫服务
        
        Args:
            minutes: 运行间隔分钟数，默认1分钟
        """
        if self.scheduler.running:
            self.logger.warning("爬虫服务已在运行中")
            return
            
        try:
            # 添加定时任务
            self.job = self.scheduler.add_job(
                func=self.run_all_crawlers,
                trigger=IntervalTrigger(minutes=hours),
                id='crawler_job',
                name='定时爬虫任务',
                replace_existing=True,
                max_instances=1,  # 确保同一时间只运行一个实例
                coalesce=True,    # 错过的任务只运行一次
            )
            
            # 启动调度器
            self.scheduler.start()
            self.logger.info(f"爬虫服务已启动，每{hours}小时运行一次")
            
            # 立即运行一次
            self.run_all_crawlers()
            
        except Exception as e:
            self.logger.error(f"启动爬虫服务失败: {str(e)}")
            self.stop()
        
    def stop(self) -> None:
        """停止爬虫服务"""
        if not self.scheduler.running:
            return
            
        try:
            # 关闭调度器
            self.scheduler.shutdown(wait=False)
            self.logger.info("爬虫服务已停止")
            
        except Exception as e:
            self.logger.error(f"停止爬虫服务失败: {str(e)}")
        
    def run_now(self, crawler_name: Optional[str] = None) -> None:
        """
        立即运行爬虫任务
        
        Args:
            crawler_name: 指定爬虫名称，为None时运行所有爬虫
        """
        if crawler_name:
            self.run_crawler(crawler_name)
        else:
            self.run_all_crawlers()
            
    def get_job_status(self) -> dict:
        """获取任务状态"""
        if not self.job:
            return {"status": "未启动"}
            
        return {
            "status": "运行中" if self.scheduler.running else "已停止",
            "next_run_time": self.job.next_run_time,
            "last_run_time": getattr(self.job, "last_run_time", None)
        }
