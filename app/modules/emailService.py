import os
import imaplib
import email
import chardet
import shutil
from email.header import decode_header
from datetime import datetime
from typing import List, Dict, Any, Union, Optional
from pathlib import Path
from email.message import Message

from app.config import EMAIL_CONFIG
from app.config import EMAIL_RULES_FILE
from app.utils.logger import get_logger
from app.utils.ruleEgine import RuleEngine
from .excelProcess.excelHandler import ExcelHandler
from .dataBaseService.bll.wip_assy import WipAssyBLL
from .dataBaseService.bll.wip_fab import WipFabBLL


class EmailService:
    def __init__(self):
        self.logger = get_logger(__name__)
        self.imap = None
        self.rule_engine = RuleEngine(EMAIL_RULES_FILE)
        self.excel_handler = ExcelHandler()
        self.wip_assy_bll = WipAssyBLL()
        self.wip_fab_bll = WipFabBLL()
        self.imap_server = EMAIL_CONFIG['IMAP_SERVER']
        self.imap_port = EMAIL_CONFIG['IMAP_PORT']
        self.imap_username = EMAIL_CONFIG['IMAP_USERNAME']
        self.imap_password = EMAIL_CONFIG['IMAP_PASSWORD']


    async def connect(self)->bool:
        """连接到邮箱服务器"""
        try:
            self.logger.info(f"连接到邮箱服务器: {self.imap_server}:{self.imap_port}")
            self.imap = imaplib.IMAP4_SSL(self.imap_server, self.imap_port)
            self.imap.login(self.imap_username, self.imap_password)
            self.logger.info("连接成功")
            return True
        except Exception as e:
            self.logger.error(f"连接失败: {e}")
            return False
        
    async def disconnect(self):
        """断开邮箱连接"""
        try:
            self.imap.logout()
            self.logger.info("断开连接成功")
        except Exception as e:
            self.logger.error(f"断开连接失败: {e}")
            
    async def check_connection(self)->bool:
        """检查邮箱连接状态"""
        try:
            if not self.imap:
                raise ConnectionError("未连接到邮箱服务器")
            return True
        except Exception as e:
            self.logger.error(f"检查连接状态失败: {e}")
            return False

    async def get_all_unread_emails(self)->List[bytes]:
        """获取所有未读邮件的email_id列表
        
        Returns:
            List[bytes]: 邮件ID列表
        """
        email_ids = []
        try:
            # 检查连接状态
            if not await self.check_connection():
                await self.connect()
                if not await self.check_connection():
                    self.logger.error("无法连接到邮箱服务器")
                    return email_ids
            
            # 选择收件箱
            self.logger.info("选择收件箱")
            status, _ = self.imap.select('INBOX')
            if status != 'OK':
                self.logger.error(f"选择收件箱失败: {status}")
                return email_ids
            
            # 搜索所有未读邮件
            self.logger.info("搜索所有未读邮件")
            search_criteria = 'UNSEEN'
            status, data = self.imap.search(None, search_criteria)
            
            if status != 'OK':
                self.logger.error(f"搜索邮件失败: {status}")
                return email_ids
            
            # 获取所有邮件ID
            if data and data[0]:
                email_ids = data[0].split()
                self.logger.info(f"找到 {len(email_ids)} 封未读邮件")
            else:
                self.logger.info("未找到未读邮件")
            
            return email_ids
            
        except Exception as e:
            self.logger.exception(f"获取未读邮件失败: {e}")
            return email_ids

    async def get_today_unread_emails(self)->List[bytes]:
        """获取今天未读邮件的email_id列表
        
        Returns:
            List[bytes]: 邮件ID列表
        """
        email_ids = []
        try:
            # 检查连接状态
            if not await self.check_connection():
                await self.connect()
                if not await self.check_connection():
                    self.logger.error("无法连接到邮箱服务器")
                    return email_ids
            
            # 选择收件箱
            self.logger.info("选择收件箱")
            status, _ = self.imap.select('INBOX')
            if status != 'OK':
                self.logger.error(f"选择收件箱失败: {status}")
                return email_ids
            
            # 获取当前日期并格式化为IMAP搜索格式 (DD-MMM-YYYY)
            today = datetime.now().strftime("%d-%b-%Y")
            self.logger.info(f"搜索日期: {today} 的未读邮件")
            
            # 搜索当天的未读邮件
            search_criteria = f'(UNSEEN SINCE "{today}")'
            status, data = self.imap.search(None, search_criteria)
            
            if status != 'OK':
                self.logger.error(f"搜索邮件失败: {status}")
                return email_ids
            
            # 获取所有邮件ID
            if data and data[0]:
                email_ids = data[0].split()
                self.logger.info(f"找到 {len(email_ids)} 封未读邮件")
            else:
                self.logger.info("未找到未读邮件")
            
            return email_ids
            
        except Exception as e:
            self.logger.exception(f"获取未读邮件失败: {e}")
            return email_ids
        
    async def _decode_header_value(self, value: str) -> str:
        """解码邮件头信息
        
        Args:
            value (str): 邮件头原始值
            
        Returns:
            str: 解码后的值
        """
        if not value:
            return ''
        
        try:
            # 解码邮件头
            decoded_chunks = []
            chunks = decode_header(value)
            
            for chunk, encoding in chunks:
                if isinstance(chunk, bytes):
                    if encoding:
                        try:
                            decoded_chunk = chunk.decode(encoding)
                        except (LookupError, UnicodeDecodeError):
                            # 如果指定的编码有误，尝试用chardet检测
                            detected = chardet.detect(chunk)
                            detected_encoding = detected['encoding'] if detected['confidence'] > 0.7 else 'utf-8'
                            try:
                                decoded_chunk = chunk.decode(detected_encoding)
                            except UnicodeDecodeError:
                                # 最后尝试utf-8
                                decoded_chunk = chunk.decode('utf-8', errors='replace')
                    else:
                        # 如果没有指定编码，用chardet检测
                        detected = chardet.detect(chunk)
                        detected_encoding = detected['encoding'] if detected['confidence'] > 0.7 else 'utf-8'
                        try:
                            decoded_chunk = chunk.decode(detected_encoding)
                        except UnicodeDecodeError:
                            # 最后尝试utf-8
                            decoded_chunk = chunk.decode('utf-8', errors='replace')
                else:
                    # 如果已经是字符串，直接使用
                    decoded_chunk = chunk
                
                decoded_chunks.append(decoded_chunk)
            
            return ''.join(decoded_chunks)
            
        except Exception as e:
            self.logger.warning(f"解码邮件头失败: {e}, 原始值: {value}")
            # 如果解码失败，返回原始值
            return value
    
    async def _parse_email_data(self, email_id: bytes)->Dict[str, Any]:
        """解析邮件数据
        
        Args:
            email_id (bytes): 邮件ID
            
        Returns:
            Dict[str, Any]: 包含邮件信息的字典，包括id, from, to, cc, subject等字段
        """
        email_data = {
            'id': email_id.decode('utf-8'),
            'from': '',
            'to': '',
            'cc': '',
            'subject': '',
            'msg': None
        }
        
        try:
            # 存储原始邮件数据
            raw_email = None
            
            # 先尝试使用BODY.PEEK[]获取完整邮件（不会标记为已读）
            self.logger.debug(f"尝试使用BODY.PEEK[]获取邮件: {email_id}")
            status, data = self.imap.fetch(email_id, '(BODY.PEEK[])')
            
            # 检查返回的数据是否有效
            if status == 'OK' and data and data[0] and isinstance(data[0], tuple) and len(data[0]) > 1:
                # 确保获取到的数据是字节类型
                if isinstance(data[0][1], bytes):
                    raw_email = data[0][1]
                else:
                    self.logger.warning(f"使用BODY.PEEK[]获取的数据不是bytes类型，而是 {type(data[0][1])}")
            
            # 如果使用BODY.PEEK[]没有获取到有效数据，尝试使用BODY.PEEK[HEADER]
            if raw_email is None:
                self.logger.warning(f"使用BODY.PEEK[]获取邮件失败，尝试使用BODY.PEEK[HEADER]")
                status, data = self.imap.fetch(email_id, '(BODY.PEEK[HEADER])')
                
                # 检查返回的数据是否有效
                if status == 'OK' and data and data[0] and isinstance(data[0], tuple) and len(data[0]) > 1:
                    # 确保获取到的数据是字节类型
                    if isinstance(data[0][1], bytes):
                        raw_email = data[0][1]
                    else:
                        self.logger.warning(f"使用BODY.PEEK[HEADER]获取的数据不是bytes类型，而是 {type(data[0][1])}")
            
            # 如果两种方式都失败了，尝试最基本的获取方式
            if raw_email is None:
                self.logger.warning(f"使用BODY.PEEK[HEADER]也获取邮件失败，尝试使用最基本的BODY[]")
                status, data = self.imap.fetch(email_id, '(BODY[])')
                
                if status == 'OK' and data and data[0] and isinstance(data[0], tuple) and len(data[0]) > 1:
                    if isinstance(data[0][1], bytes):
                        raw_email = data[0][1]
                    else:
                        self.logger.error(f"所有获取邮件方式都失败，无法获取邮件内容")
                        return email_data
            
            # 如果所有方法都失败，返回空结果
            if raw_email is None:
                self.logger.error(f"无法获取邮件 {email_id} 的内容")
                return email_data
            
            # 使用chardet检测编码
            try:
                detected = chardet.detect(raw_email)
                encoding = detected['encoding'] if detected['confidence'] > 0.7 else 'utf-8'
                self.logger.debug(f"检测到邮件编码: {encoding}, 置信度: {detected['confidence']}")
            except TypeError as e:
                self.logger.error(f"编码检测失败: {e}, raw_email类型: {type(raw_email)}")
                return email_data
            
            # 解析邮件内容
            try:
                msg = email.message_from_bytes(raw_email)
                email_data['msg'] = msg
            except Exception as e:
                self.logger.error(f"解析邮件内容失败: {e}")
                return email_data
            
            # 解析邮件头
            try:
                # 解析发件人
                email_data['from'] = await self._decode_header_value(msg.get('From', ''))
                
                # 解析收件人
                email_data['to'] = await self._decode_header_value(msg.get('To', ''))
                
                # 解析抄送人
                email_data['cc'] = await self._decode_header_value(msg.get('Cc', ''))
                
                # 解析主题
                email_data['subject'] = await self._decode_header_value(msg.get('Subject', ''))
                
                self.logger.info(f"成功解析邮件: {email_id}, 主题: {email_data['subject']}")
            except Exception as e:
                self.logger.error(f"解析邮件头失败: {e}")
            
            return email_data
            
        except Exception as e:
            self.logger.exception(f"解析邮件失败: {e}")
            return email_data

    async def _save_attachments(self, msg: Message, folder_path: str, allowed_extensions: List[str])->List[str]:
        """保存邮件附件
        
        Args:
            msg (Message): 邮件消息对象
            folder_path (str): 保存附件的文件夹路径
            allowed_extensions (List[str]): 允许的文件扩展名列表
            
        Returns:
            List[str]: 保存的附件文件路径列表
        """
        saved_attachments = []
        
        if not msg:
            self.logger.warning("邮件对象为空，无法保存附件")
            return saved_attachments
        
        # 确保附件目录存在
        os.makedirs(folder_path, exist_ok=True)
        
        try:
            # 遍历邮件的所有部分
            for part in msg.walk():
                # 跳过非附件部分
                if part.get_content_maintype() == 'multipart' or part.get('Content-Disposition') is None:
                    continue
                
                # 获取文件名
                filename = part.get_filename()
                if not filename:
                    continue
                
                # 解码文件名
                try:
                    filename = await self._decode_header_value(filename)
                except Exception as e:
                    self.logger.warning(f"无法解码附件文件名: {e}")
                    continue
                
                if not filename:
                    continue
                
                # 检查文件扩展名
                file_ext = os.path.splitext(filename)[1].lower()
                if allowed_extensions and file_ext not in allowed_extensions:
                    self.logger.debug(f"跳过不允许的附件类型: {filename} ({file_ext})")
                    continue
                
                # 构建文件路径
                filepath = os.path.join(folder_path, filename)
                
                # 处理特殊情况: 如果是特定文件且已存在，则跳过
                if "苏州华芯微电子股份有限公司的封装产品进展表" in filename and os.path.exists(filepath):
                    self.logger.debug(f"跳过已存在的池州华宇进度表文件: {filename}")
                    continue
                
                # 保存附件
                try:
                    with open(filepath, 'wb') as f:
                        payload = part.get_payload(decode=True)
                        if payload:
                            f.write(payload)
                            saved_attachments.append(filepath)
                            self.logger.info(f"成功保存附件: {filename}")
                        else:
                            self.logger.warning(f"附件内容为空: {filename}")
                except Exception as e:
                    self.logger.error(f"保存附件 {filename} 失败: {e}")
            
            return saved_attachments
            
        except Exception as e:
            self.logger.exception(f"处理邮件附件时出错: {e}")
            return saved_attachments
    
    async def _process_single_email(self, email_id: bytes, stats: Dict[str, int]):
        """处理单封邮件
        
        Args:
            email_id (bytes): 邮件ID
            stats (Dict[str, int]): 统计信息字典
        """
        self.logger.info(f"开始处理邮件: {email_id}")
        
        # 解析邮件数据
        email_data = await self._parse_email_data(email_id)
        if not email_data or not email_data['subject']:
            self.logger.warning(f"邮件 {email_id} 解析失败或主题为空，跳过处理")
            stats['failed'] += 1
            return
        
        self.logger.info(f"邮件解析完成: {email_data['subject']}")
        
        # 检查邮件是否缺少必要信息
        if not email_data['from'] or not email_data['to']:
            self.logger.warning(f"邮件缺少发件人或收件人信息，跳过处理")
            stats['failed'] += 1
            return
        
        # 使用规则引擎匹配邮件
        try:
            match_result = self.rule_engine.apply_rules(email_data)
            category = match_result.get('category', '未分类')
            supplier = match_result.get('supplier', '未知供应商')
            
            self.logger.info(f"邮件匹配结果: 类别={category}, 供应商={supplier}")
            
            # 检查邮件是否匹配任何规则
            if category == '未分类':
                self.logger.warning(f"邮件不匹配任何规则，跳过处理")
                stats['failed'] += 1
                return
            
            # 保存附件
            attachments = []
            if 'actions' in match_result and 'attachment_folder' in match_result['actions']:
                allowed_extensions = match_result.get('allowed_extensions', [])
                attachments = await self._save_attachments(
                    email_data['msg'], 
                    match_result['actions']['attachment_folder'],
                    allowed_extensions
                )
                
                if attachments:
                    match_result['attachments'] = attachments
                    stats['attachments'] += len(attachments)
                    self.logger.info(f"成功保存 {len(attachments)} 个附件")
                else:
                    self.logger.warning(f"没有找到有效附件或附件保存失败")
            
            # 没有附件，无法继续处理
            if not attachments:
                self.logger.warning(f"邮件没有可处理的附件，跳过后续处理")
                stats['failed'] += 1
                return
            
            # 根据类别处理附件
            await self._process_attachments(category, supplier, match_result, attachments, stats)
            
            # 处理成功，将邮件标记为已读
            try:
                self.imap.store(email_id, '+FLAGS', '\\Seen')
                self.logger.info(f"邮件 {email_id} 已标记为已读")
            except Exception as e:
                self.logger.warning(f"标记邮件 {email_id} 为已读时出错: {e}")
            
        except Exception as e:
            stats['failed'] += 1
            self.logger.exception(f"处理邮件 {email_id} 的规则匹配或附件时出错: {e}")
            
            # 如果规则匹配成功且有附件，则移动到失败目录
            if 'match_result' in locals() and 'attachments' in locals() and attachments:
                for attachment in attachments:
                    await self._move_to_failed_folder(match_result, attachment)
    
    async def _process_attachments(self, category: str, supplier: str, match_result: Dict, attachments: List[str], stats: Dict[str, int]):
        """根据类别处理附件
        
        Args:
            category (str): 邮件类别
            supplier (str): 供应商
            match_result (Dict): 规则匹配结果
            attachments (List[str]): 附件路径列表
            stats (Dict[str, int]): 统计信息
        """
        try:
            # 只处理第一个附件
            attachment_path = attachments[0] if attachments else None
            if not attachment_path:
                return
            
            if category == '封装进度表':
                await self._process_assembly_wip(supplier, match_result, attachment_path, stats)
            elif category == '晶圆进度表':
                await self._process_wafer_wip(supplier, match_result, attachment_path, stats)
            else:
                self.logger.debug(f"不支持的分类: {category}, 跳过处理")
                stats['failed'] += 1
                await self._move_to_failed_folder(match_result, attachment_path)
        
        except Exception as e:
            stats['failed'] += 1
            self.logger.exception(f"处理{supplier}的{category}附件失败: {e}")
            await self._move_to_failed_folder(match_result, attachment_path)
    
    async def _move_to_processed_folder(self, match_result: Dict, attachment_path: str):
        """将成功处理的附件移动到processed文件夹
        
        Args:
            match_result (Dict): 规则匹配结果
            attachment_path (str): 附件路径
        """
        try:
            if not attachment_path or not match_result or 'actions' not in match_result or 'attachment_folder' not in match_result['actions']:
                return
            
            # 创建成功处理目录路径
            download_folder = match_result['actions']['attachment_folder']
            processed_folder = download_folder.replace("downloads/", "downloads/processed/")
            
            # 确保目录存在
            os.makedirs(processed_folder, exist_ok=True)
            
            # 构建目标文件路径
            target_file = os.path.join(processed_folder, os.path.basename(attachment_path))
            
            # 剪切文件到成功处理目录
            shutil.move(attachment_path, target_file)
            self.logger.info(f"已将成功处理的附件移动到: {target_file}")
            
        except Exception as e:
            self.logger.error(f"移动成功处理附件时出错: {e}")

    async def _move_to_failed_folder(self, match_result: Dict, attachment_path: str):
        """将失败的附件移动到failed文件夹
        
        Args:
            match_result (Dict): 规则匹配结果
            attachment_path (str): 附件路径
        """
        try:
            if not attachment_path or not match_result or 'actions' not in match_result or 'attachment_folder' not in match_result['actions']:
                return
            
            # 创建失败目录路径
            download_folder = match_result['actions']['attachment_folder']
                
            failed_folder = download_folder.replace("downloads/", "downloads/failed/")
            
            # 确保目录存在
            os.makedirs(failed_folder, exist_ok=True)
            
            # 构建目标文件路径
            target_file = os.path.join(failed_folder, os.path.basename(attachment_path))
            
            # 复制文件到失败目录
            shutil.copy2(attachment_path, target_file)
            self.logger.info(f"已将失败附件复制到: {target_file}")
            
        except Exception as e:
            self.logger.error(f"移动失败附件时出错: {e}")
    
    async def _process_assembly_wip(self, supplier: str, match_result: Dict, attachment_path: str, stats: Dict[str, int]):
        """处理封装进度表
        
        Args:
            supplier (str): 供应商名称
            match_result (Dict): 规则匹配结果
            attachment_path (str): 附件路径
            stats (Dict[str, int]): 统计信息
        """
        try:
            result = self.excel_handler.process_excel(match_result)
            if result is None:
                stats['failed'] += 1
                self.logger.warning(f"{supplier}封装进度表内容可能为空或格式错误")
                await self._move_to_failed_folder(match_result, attachment_path)
                return
            
            # 更新数据库
            self.wip_assy_bll.update_supplier_progress(result.to_dict(orient="records"))
            stats['processed'] += 1
            self.logger.info(f"成功处理{supplier}封装进度表")
            
            # 移动成功处理的附件
            await self._move_to_processed_folder(match_result, attachment_path)
        
        except Exception as e:
            stats['failed'] += 1
            self.logger.exception(f"处理{supplier}封装进度表失败: {e}")
            await self._move_to_failed_folder(match_result, attachment_path)
    
    async def _process_wafer_wip(self, supplier: str, match_result: Dict, attachment_path: str, stats: Dict[str, int]):
        """处理晶圆进度表
        
        Args:
            supplier (str): 供应商名称
            match_result (Dict): 规则匹配结果
            attachment_path (str): 附件路径
            stats (Dict[str, int]): 统计信息
        """
        try:
            result = self.excel_handler.process_excel(match_result)
            if result is None:
                stats['failed'] += 1
                self.logger.warning(f"{supplier}晶圆进度表内容可能为空或格式错误")
                await self._move_to_failed_folder(match_result, attachment_path)
                return
            
            # 更新数据库
            self.wip_fab_bll.update_supplier_progress(result.to_dict(orient="records"))
            stats['processed'] += 1
            self.logger.info(f"成功处理{supplier}晶圆进度表")
            
            # 移动成功处理的附件
            await self._move_to_processed_folder(match_result, attachment_path)
        
        except Exception as e:
            stats['failed'] += 1
            self.logger.exception(f"处理{supplier}晶圆进度表失败: {e}")
            await self._move_to_failed_folder(match_result, attachment_path)

    async def process_email(self):
        """处理邮件并提取相关信息"""
        stats = {
            'total': 0,
            'processed': 0,
            'failed': 0,
            'attachments': 0
        }
        
        try:
            # 获取今日未读邮件
            email_ids = await self.get_today_unread_emails()
            if not email_ids:
                self.logger.info("没有找到未读邮件")
                return
            
            stats['total'] = len(email_ids)
            self.logger.info(f"开始处理 {stats['total']} 封未读邮件")
            
            # 处理每封邮件
            for email_id in email_ids:
                try:
                    await self._process_single_email(email_id, stats)
                except Exception as e:
                    stats['failed'] += 1
                    self.logger.exception(f"处理邮件 {email_id} 时发生错误: {e}")
            
            # 处理完成后输出统计信息
            self.logger.info(
                f"邮件处理完成: 总数 {stats['total']}, "
                f"成功 {stats['processed']}, "
                f"失败 {stats['failed']}, "
                f"附件 {stats['attachments']}"
            )
            self.disconnect()

        except Exception as e:
            self.logger.exception(f"邮件处理过程中发生错误: {e}")