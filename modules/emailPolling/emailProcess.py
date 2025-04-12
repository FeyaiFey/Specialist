from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.interval import IntervalTrigger

from utils.logger import Logger
from modules.emailPolling.emailService import EmailService
from modules.dataBaseService.bll.wip_assy import WipAssyBLL
from modules.dataBaseService.bll.wip_fab import WipFabBLL
from modules.excelProcess.excelHandler import ExcelHandler


class EmailProcess:
    """邮件处理类"""
    
    def __init__(self):
        """初始化邮件处理类"""
        self.logger = Logger().get_logger('emailProcess')
        self.email_service = EmailService()
        self.excel_handler = ExcelHandler()
        self.wip_assy_bll = WipAssyBLL()
        self.wip_fab_bll = WipFabBLL()
        # 创建后台调度器
        self.scheduler = BackgroundScheduler()
        self.job = None
    
    def run_process(self) -> bool:
        """运行邮件处理"""
        stats = {
            'total': 0,
            'processed': 0,
            'failed': 0,
            'attachments': 0
        }
        try:
            # 连接邮箱服务器
            if not self.email_service.connect():
                return False
            
            # 获取未读邮件
            unread_emails = self.email_service.get_unread_emails()
            stats['total'] = len(unread_emails)
            if not unread_emails:
                return True
            
            # 处理未读邮件
            for email_id in unread_emails:
                try: 
                    match_result = self.email_service.process_email(email_id)
                    # 检查是否有匹配结果
                    if not match_result:
                        self.logger.debug("邮件不匹配任何规则，跳过处理")
                        continue
                    # 统计附件数
                    attachments = match_result.get('attachments', [])
                    if attachments:
                        stats['attachments'] += len(attachments)
                    
                    # 根据匹配结果，处理附件
                    category = match_result.get('category')

                    if category == '封装进度表' and attachments:
                        result = self.excel_handler.process_excel(match_result)
                        if result is None:
                            stats['failed'] += 1
                            self.logger.debug("该封装进度表内容可能为空或格式错误，跳过处理")
                            continue
                        stats['processed'] += 1
                        self.logger.debug(f"处理结果: {result}")
                        self.wip_assy_bll.update_supplier_progress(result.to_dict(orient="records"))
                        continue

                    if category == '晶圆进度表' and attachments:
                        result = self.excel_handler.process_excel(match_result)
                        if result is None:
                            stats['failed'] += 1
                            self.logger.debug("该晶圆进度表内容可能为空或格式错误，跳过处理")
                            continue
                        stats['processed'] += 1
                        self.logger.debug(f"处理结果: {result}")

                        self.wip_fab_bll.update_supplier_progress(result.to_dict(orient="records"))
                        continue
                except Exception as e:
                    stats['failed'] += 1
                    self.logger.error(f"处理邮件失败: {str(e)}", exc_info=True)
                    continue
                    
            self.logger.info(
                f"邮件处理完成: 总数 {stats['total']}, "
                f"成功 {stats['processed']}, "
                f"失败 {stats['failed']}, "
                f"附件 {stats['attachments']}"
            )
            return stats
            
        except Exception as e:
            self.logger.error(f"邮件处理过程发生错误: {str(e)}", exc_info=True)
            raise

        finally:
            self.email_service.disconnect()


    def start(self, minutes: int = 10) -> None:
        """
        启动邮件处理服务
        
        Args:
            minutes: 运行间隔分钟数，默认10分钟
        """
        if self.scheduler.running:
            self.logger.warning("邮件处理服务已在运行中")
            return
        
        try:
            # 添加定时任务
            self.job = self.scheduler.add_job(
                func=self.run_process,
                trigger=IntervalTrigger(minutes=minutes),
                id='email_process_job',
                name='邮件处理任务',
                replace_existing=True,
                max_instances=1,
                coalesce=True,
            )

            # 启动调度器
            self.scheduler.start()
            self.logger.info(f"邮件处理服务已启动，每{minutes}分钟运行一次")
            
            # 立即运行一次
            self.run_process()

        except Exception as e:
            self.logger.error(f"启动邮件处理服务失败: {str(e)}", exc_info=True)
            self.stop()
        
    def stop(self) -> None:
        """停止邮件处理服务"""
        if not self.scheduler.running:
            return
        
        try:
            # 关闭调度器
            self.scheduler.shutdown(wait=False)
            self.logger.info("邮件处理服务已停止")
            
        except Exception as e:
            self.logger.error(f"停止邮件处理服务失败: {str(e)}", exc_info=True)
            
            
