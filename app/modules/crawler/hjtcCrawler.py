"""
和舰科技爬虫模块
"""

import os
import pathlib
import shutil
from datetime import datetime
from typing import Optional, Dict, Any

from app.config import HJTC_USERNAME, HJTC_PASSWORD, HJTC_OUTPUT_DIR
from app.utils.logger import get_logger
from app.modules.dataBaseService.bll.wip_fab import WipFabBLL
from app.modules.crawler.base import BaseCrawler
from app.modules.excelProcess.supplier.hjtc_wip_handler import process_hjtc_excel

class HJTCCrawler(BaseCrawler):
    """
    和舰科技爬虫类,用于爬取和舰科技的WIP数据
    主要功能:
    1. 登录和舰科技系统
    2. 爬取WIP数据
    3. 处理并保存数据
    
    属性:
        BASE_URL: 和舰科技系统的基础URL
        headers: 请求头信息
        session: 会话对象,用于维持登录状态
        config: 配置信息,包含用户名密码等
        logger: 日志记录器
        
    方法:
        login(): 登录系统
        get_wip_data(): 获取WIP数据
        process_data(): 处理爬取的数据
        run(): 执行爬虫任务
        
    使用示例:
        crawler = HJTCCrawler(config)
        crawler.run()
    """
    
    # 基础URL
    BASE_URL = "https://my2.hjtc.com.cn"
    
    def __init__(self):
        """
        初始化和舰科技爬虫
        
        Args:
            config: 配置参数
        """
        super().__init__()
        
        # 更新请求头
        self.headers.update({
            "Content-Type": "application/x-www-form-urlencoded; charset=UTF-8", 
            "X-Requested-With": "XMLHttpRequest",
            "Referer": f"{self.BASE_URL}/myhj_web/Production/WIP/summary_drill"
        })
        
        self.session.trust_env = False
        self.logger = get_logger(__name__)

    def login(self) -> bool:
        """
        登录系统
        
        Returns:
            bool: 登录是否成功
        """
        try:
            self.logger.debug("开始登录和舰科技系统...")
            login_url = f"{self.BASE_URL}/secure/login_hjtc.fcc?TYPE=33554433&REALMOID=06-af713708-e650-4979-afd0-d504ff745fd2&GUID=0&SMAUTHREASON=0&METHOD=GET&SMAGENTNAME=-SM-oEHd7jdu1MRiPlIRQQWzhpTe%2bzCsgXutiNAm67JlRwA9yMKTNX1H5EwwnharNAiE&TARGET=-SM-https%3a%2f%2fmy2%2ehjtc%2ecom%2ecn%2f"
            
            login_data = {
                "username": HJTC_USERNAME,
                "password": HJTC_PASSWORD
            }
            
            response = self.post(login_url, data=login_data)
            response.raise_for_status()
            
            self.logger.debug("登录成功")
            return True
            
        except Exception as e:
            self.logger.error(f"登录失败: {str(e)}")
            return False

    def download_wip_excel(self) -> Optional[str]:
        """
        下载WIP Excel报表
        
        Returns:
            Optional[str]: 下载的文件路径，失败返回None
        """
        try:
            self.logger.debug("开始下载WIP Excel报表...")
            
            # 下载Excel
            download_url = f"{self.BASE_URL}/myhj_web/Production/WIP/summary_drill_export"
            download_data = {
                "Fab": "FAB8N",
                "Stage": "ALL",
                "ReportCategory": "ALL",
                "CustomerPartType": "1",
                "CustomerParts": "ALL",
                "ShippingProductType": "1",
                "ShippingProducts": "ALL",
                "UmcProductType": "1",
                "UmcProducts": "ALL"
            }
            
            # 修改headers添加Excel相关的Accept
            self.headers["Accept"] = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            
            response = self.post(download_url, data=download_data)
            response.raise_for_status()
            
            # 保存文件
            date = datetime.now().strftime("%Y%m%d")
            filename = f"和舰科技_{date}.csv"
            filepath = self.save_file(response.content, filename, HJTC_OUTPUT_DIR)
            self.logger.debug(f"Excel文件已保存到: {filepath}")
            return filepath
            
        except Exception as e:
            self.logger.error(f"下载Excel失败: {str(e)}")
            return None

    def _ensure_directory_exists(self, directory):
        """确保目录存在，如果不存在则创建"""
        os.makedirs(directory, exist_ok=True)
    
    def run(self) -> bool:
        """运行爬虫任务"""
        if not self.login():
            return False
        
        # 下载Excel
        filepath = self.download_wip_excel()
        if not filepath:
            self.logger.error("下载文件失败，无法继续处理")
            return False
            
        self.logger.debug(f"下载的文件路径: {filepath}")

        # 处理Excel
        try:
            df = process_hjtc_excel(filepath)
            if not (df is not None and not df.empty):
                self.logger.error(f"处理Excel失败")
                self._move_to_failed(filepath)
                return False
                
            # 将数据记录到sqlserver
            wip_fab_bll = WipFabBLL()
            wip_fab_bll.update_supplier_progress(df.to_dict(orient="records"))
            self.logger.info(f"和舰科技数据更新完成")
            self.close()
            
            # 移动文件到processed目录
            self._move_to_processed(filepath)
            return True
            
        except Exception as e:
            self.logger.error(f"和舰科技数据更新失败: {str(e)}")
            self._move_to_failed(filepath)
            return False

    def _move_to_processed(self, filepath):
        """移动文件到processed目录"""
        try:
            # 构建目标目录路径
            processed_dir = HJTC_OUTPUT_DIR.replace("downloads/", "downloads/processed/")
            
            # 确保目标目录存在
            self._ensure_directory_exists(processed_dir)
            
            # 构建目标文件路径
            target_path = os.path.join(processed_dir,os.path.basename(filepath))
            
            # 如果目标文件已存在，先删除
            if os.path.exists(target_path):
                os.remove(target_path)
                
            # 移动文件
            shutil.move(filepath, target_path)
            self.logger.info(f"文件已移动到: {target_path}")
        except Exception as e:
            self.logger.error(f"移动文件到processed目录失败: {e}")
            # 如果移动失败，尝试移动到failed目录
            self._move_to_failed(filepath)
    
    def _move_to_failed(self, filepath):
        """移动文件到failed目录"""
        try:
            if not filepath or not os.path.exists(filepath):
                self.logger.warning(f"文件不存在，无法移动: {filepath}")
                return
                
            # 构建failed目录路径
            failed_dir = HJTC_OUTPUT_DIR.replace("downloads/", "downloads/failed/")
            
            # 确保failed目录存在
            self._ensure_directory_exists(failed_dir)
            
            # 构建目标文件路径
            target_path = os.path.join(failed_dir, os.path.basename(filepath))
            
            # 如果目标文件已存在，先删除
            if os.path.exists(target_path):
                os.remove(target_path)
                
            # 移动文件
            shutil.move(filepath, target_path)
            self.logger.info(f"文件已移动到failed目录: {target_path}")
        except Exception as e:
            self.logger.error(f"移动文件到failed目录也失败了: {e}")