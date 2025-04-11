import os
import imaplib
from typing import List, Dict, Any, Union

from utils.logger import Logger
from utils.emailHelper import EmailHelper
from modules.emailPolling.ruleEgine import RuleEngine

class EmailService:
    def __init__(self):
        # 从.env获取邮箱配置
        self.logger = Logger().get_logger('emailService')
        self.rule_engine = RuleEngine(os.getenv('EMAIL_RULES_FILE'))
        self.imap = None
        self.email_address = os.getenv('EMAIL_ADDRESS')
        self.email_password = os.getenv('EMAIL_PASSWORD')
        self.imap_server = os.getenv('EMAIL_IMAP_SERVER')
        self.imap_port = int(os.getenv('EMAIL_IMAP_PORT'))
        self.use_ssl = os.getenv('EMAIL_USE_SSL').lower() == 'true'

    def connect(self) -> bool:
        """连接到邮箱服务器"""
        try:
            self.imap = imaplib.IMAP4_SSL(self.imap_server, self.imap_port)
            self.imap.login(self.email_address, self.email_password)
            self.logger.debug(f"成功连接到邮箱服务器: {self.imap_server}")
            return True
        except Exception as e:
            self.logger.error(f"连接到邮箱服务器失败: {e}")
            return False

    def disconnect(self) -> bool:
        """断开邮箱服务器连接"""
        try:
            self.imap.logout()
            self.logger.debug("成功断开邮箱服务器连接")
            return True
        except Exception as e:
            self.logger.error(f"断开邮箱服务器连接失败: {e}")
            return False
        
    def check_connection(self) -> None:
        """检查IMAP连接状态"""
        if not self.imap:
            self.logger.error("未连接到邮件服务器")
            raise ConnectionError("未连接到邮件服务器")
        
    def get_unread_emails(self) -> List[bytes]:
        """
        获取未读邮件列表
        
        返回:
            list: 未读邮件ID列表
            
        异常:
            ConnectionError: 未连接到服务器时抛出
        """

        self.check_connection()

        self.logger.debug("开始获取未读邮件...")
        try:
            status, _ = self.imap.select('INBOX')
            if status != 'OK':
                raise Exception(f"无法选择收件箱，状态: {status}")
            status, messages = self.imap.search(None, 'UNSEEN')
            if status != 'OK':
                raise Exception(f"无法搜索未读邮件，状态: {status}")
            email_ids = messages[0].split()
            self.logger.debug(f"找到 {len(email_ids)} 封未读邮件")
            return email_ids
        except Exception as e:
            self.logger.error(f"获取未读邮件失败: {str(e)}")
            raise

    def process_email(self, email_id: Union[str, bytes]) -> Dict[str, Any]:
        """
        处理单个邮件
        
        获取邮件内容，应用规则，处理附件，设置已读状态
        
        参数:
            email_id: 邮件ID
            
        返回:
            Dict[str, Any]: 匹配结果
            枚举：
            {
                'actions': {'save_attachment': True, 'mark_as_read': True, 'attachment_folder': 'attachments/temp/封装送货单/池州华宇'},
                'name': '封装送货单-池州华宇',
                'category': '封装送货单',
                'supplier': '池州华宇',
                'attachments': ['attachments/temp/封装送货单/池州华宇/1.pdf', 'attachments/temp/封装送货单/池州华宇/2.pdf']
            }
            
        异常:
            RuntimeError: 处理失败时抛出

        email_data: 邮件数据字典
        {
            'from': 发件人
            'to': 收件人
            'cc': 抄送人
            'subject': 主题
        }
        """
        self.check_connection()

        email_helper = EmailHelper(self.imap)

        email_id = email_helper._normalize_email_id(email_id)
        msg = email_helper.fetch_email(email_id)

        if not msg:
            self.logger.error(f"邮件内容为空,跳过处理: {email_id}")
            return {}
        try:
            # 解析邮件信息
            email_data = email_helper.parse_email_data(msg, email_id)
            
            # 使用规则引擎匹配邮件
            match_result = self.rule_engine.apply_rules(email_data)

            category = match_result['category']

            # 如果未匹配到任何规则，则保持未读状态
            if category == '未分类':
                self.logger.debug(f"邮件不匹配任何规则，保持未读状态: {email_data['subject']}")
                return {}
            
            # 保存附件
            try:
                # 获取允许的附件类型
                allowed_extensions = match_result.get('allowed_extensions', [])
                attachments = email_helper.save_attachments(
                    msg, 
                    email_id, 
                    match_result['actions']['attachment_folder'],
                    allowed_extensions
                )
                match_result['attachments'] = attachments
            except Exception as e:
                self.logger.error(f"保存附件失败: {str(e)}")

            # 标记为已读
            if match_result['actions'].get('mark_as_read', True):
                email_helper.mark_email_as_read(email_id)

            self.logger.info(f"邮件处理完成: [{match_result['supplier']}-{category}] {email_data['subject']}")
            return match_result
            
        except Exception as e:
            self.logger.error(f"处理邮件失败: {str(e)}")
            return {}
            
