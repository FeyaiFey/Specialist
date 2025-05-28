import asyncio
from datetime import datetime
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.interval import IntervalTrigger

from app.modules.emailService import EmailService
from app.utils.logger import get_service_logger

class EmailPoller:
    def __init__(self):
        """初始化邮箱轮询器"""
        self.logger = get_service_logger('email_service')
        self.email_service = EmailService()
        self.scheduler = AsyncIOScheduler()
        
    async def poll_email(self):
        """轮询邮箱并处理邮件"""
        try:
            self.logger.info(f"开始邮箱轮询，时间：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
            
            # 连接到邮箱服务器
            connected = await self.email_service.connect()
            if not connected:
                self.logger.error("无法连接到邮箱服务器，跳过本次轮询")
                return
                
            # 处理邮件
            await self.email_service.process_email()
            
            self.logger.info(f"邮箱轮询完成，时间：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
            
        except Exception as e:
            self.logger.exception(f"邮箱轮询过程中发生错误: {e}")
            
    def start(self, minutes = 10):
        """启动邮箱轮询服务"""
        try:
            # 设置定时任务，每小时执行一次
            self.logger.info(f"启动邮箱轮询服务，每{minutes}分钟执行一次")
            self.scheduler.add_job(
                self.poll_email,
                trigger=IntervalTrigger(minutes=minutes),
                id='poll_email_job',
                replace_existing=True
            )
            
            # 立即执行一次
            self.scheduler.add_job(
                self.poll_email,
                id='poll_email_initial_job',
                next_run_time=datetime.now()
            )
            
            # 启动调度器
            self.scheduler.start()
            
            # 保持程序运行
            loop = asyncio.get_event_loop()
            try:
                self.logger.info(f"邮箱轮询服务已启动，每{minutes}分钟执行一次")
                loop.run_forever()
            except (KeyboardInterrupt, SystemExit):
                self.logger.info("接收到退出信号，正在停止服务...")
            finally:
                self.scheduler.shutdown()
                self.logger.info("邮箱轮询服务已停止")
                
        except Exception as e:
            self.logger.exception(f"启动邮箱轮询服务时发生错误: {e}")
            
if __name__ == "__main__":
    # 创建并启动邮箱轮询服务
    poller = EmailPoller()
    poller.start() 