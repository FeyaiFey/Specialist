"""
基础爬虫类模块
提供所有爬虫的基础功能
"""

import os
import requests
import urllib3
from app.utils.logger import get_logger

class BaseCrawler:
    """基础爬虫类"""
    
    def __init__(self):
        """初始化基础爬虫"""
        # 初始化日志记录器
        self.logger = get_logger(__name__)
        # 创建session
        self.session = requests.Session()
        # 禁用SSL警告
        urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
        # 基础请求头
        self.headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/132.0.0.0 Safari/537.36",
            "Accept": "application/json, text/javascript, */*; q=0.01",
            "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8"
        } 
        # 代理设置
        self.proxies = {
            'http': None,
            'https': None
        }
        # 禁用系统代理
        self._disable_system_proxy()
        self.session.trust_env = False
        self.logger.debug("爬虫初始化完成")
    
    def _disable_system_proxy(self):
        """禁用系统代理"""
        os.environ['NO_PROXY'] = '*'
        os.environ['no_proxy'] = '*'
        os.environ['HTTP_PROXY'] = ''
        os.environ['HTTPS_PROXY'] = ''
        os.environ['http_proxy'] = ''
        os.environ['https_proxy'] = ''
    
    def get(self, url: str, **kwargs) -> requests.Response:
        """发送GET请求"""
        return self.session.get(
            url,
            headers=self.headers,
            proxies=self.proxies,
            verify=False,
            timeout=30,
            **kwargs
        )
    
    def post(self, url: str, **kwargs) -> requests.Response:
        """发送POST请求"""
        return self.session.post(
            url,
            headers=self.headers,
            proxies=self.proxies,
            verify=False,
            timeout=30,
            **kwargs
        )
    
    def save_file(self, content: bytes, filename: str, output_dir: str) -> str:
        """
        保存文件
        
        Args:
            content: 文件内容
            filename: 文件名
            output_dir: 输出目录
            
        Returns:
            str: 保存的文件路径
        """
        os.makedirs(output_dir, exist_ok=True)
        filepath = os.path.join(output_dir, filename)
        with open(filepath, 'wb') as f:
            f.write(content)
        return filepath
    
    def close(self):
        """关闭爬虫"""
        self.session.close()
    
    def run(self):
        """
        运行爬虫任务
        子类必须实现此方法
        """
        raise NotImplementedError("子类必须实现run方法") 