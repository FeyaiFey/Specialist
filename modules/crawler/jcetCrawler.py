"""
长电科技爬虫模块
"""
import os
import json
import re
import pandas as pd
from datetime import datetime
from pathlib import Path
from bs4 import BeautifulSoup
from typing import Any

from modules.dataBaseService.bll.wip_assy import WipAssyBLL
from modules.crawler.base import BaseCrawler
from modules.excelProcess.supplier.jcet_wip_handler import JcetWipHandler
from utils.helpers import move_file


class JcetCrawler(BaseCrawler):
    """爬取长电科技WIP数据"""
    
    # 基础URL
    BASE_URL = "https://jcetreport.jcetglobal.com:8995/WebReport/decision"
    
    def __init__(self):
        """
        初始化长电科技爬虫
        """
        super().__init__()
        
        # 配置文件路径
        self.config_dir = Path(os.path.abspath("config"))
        self.COOKIE_FILE = self.config_dir / "jcet_cookies.json"
        self.CURL_FILE = self.config_dir / "cookie.txt"
        self.TOKEN_FILE = self.config_dir / "jcet_token.json"
        
        # 创建配置目录
        self.config_dir.mkdir(parents=True, exist_ok=True)
        
        # 更新请求头
        self.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36',
            'Accept': 'application/json, text/javascript, */*; q=0.01',
            'Content-Type': 'application/json',
            'Origin': 'https://jcetreport.jcetglobal.com:8995',
            'Referer': 'https://jcetreport.jcetglobal.com:8995/WebReport/decision/login',
            'X-Requested-With': 'XMLHttpRequest',
            'Cache-Control': 'no-cache',
            'Pragma': 'no-cache',
            'Connection': 'keep-alive'
        })
        
        self.session.trust_env = False
        self.access_token = None

    def save_token(self, token_data: dict):
        """
        保存token信息到文件
        
        Args:
            token_data: token数据
        """
        try:
            token_path = Path(self.TOKEN_FILE)
            token_path.parent.mkdir(parents=True, exist_ok=True)
            
            with open(token_path, 'w', encoding='utf-8') as f:
                json.dump(token_data, f, indent=2, ensure_ascii=False)
            
            self.logger.debug("Token已保存")
        except Exception as e:
            self.logger.error(f"保存Token失败: {str(e)}")
            raise

    def load_token(self) -> dict:
        """
        从文件加载token
        
        Returns:
            dict: token数据
        """
        try:
            if not os.path.exists(self.TOKEN_FILE):
                return {}
                
            with open(self.TOKEN_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            self.logger.error(f"加载Token失败: {str(e)}")
            return {}

    def refresh_token(self) -> bool:
        """
        刷新token
        
        Returns:
            bool: 是否成功
        """
        try:
            # 先尝试登录获取token
            login_url = f"{self.BASE_URL}/login"
            login_data = {
                "username": "A2-099",
                "encrypted": False,
                "password": "Tel68241373$",
                "validity": -2
            }
            
            response = self.session.post(
                login_url, 
                json=login_data,
                headers=self.headers, 
                verify=False
            )
            
            # self.logger.debug(f"登录响应: {response.text}")
            
            if response.status_code == 200:
                data = response.json()
                if 'data' in data and 'accessToken' in data['data']:
                    self.access_token = data['data']['accessToken']
                    self.save_token({'accessToken': self.access_token})
                    self.headers['Authorization'] = f'Bearer {self.access_token}'
                    return True
                    
            # 如果登录失败，尝试刷新token
            refresh_url = f"{self.BASE_URL}/token/refresh"
            
            # 从保存的token文件中获取oldToken
            token_data = self.load_token()
            if not token_data or 'accessToken' not in token_data:
                self.logger.error("无法获取oldToken进行刷新")
                return False
                
            refresh_data = {
                "oldToken": token_data['accessToken'],
                "tokenTimeOut": 1209599999  # 从截图中看到的超时时间
            }
            
            # self.logger.debug(f"刷新Token请求数据: {refresh_data}")
            
            response = self.session.post(
                refresh_url, 
                json=refresh_data,
                headers=self.headers, 
                verify=False
            )
            
            # self.logger.debug(f"刷新Token响应: {response.text}")
            
            if response.status_code == 200:
                data = response.json()
                if 'data' in data and 'accessToken' in data['data']:
                    self.access_token = data['data']['accessToken']
                    self.save_token({'accessToken': self.access_token})
                    self.headers['Authorization'] = f'Bearer {self.access_token}'
                    return True
            
            self.logger.error(f"刷新Token失败: {response.text}")
            return False
            
        except Exception as e:
            self.logger.error(f"刷新Token失败: {str(e)}")
            return False

    def extract_cookies_from_curl(self, curl_command: str) -> dict:
        """
        从cURL命令中提取Cookie和Token
        
        Args:
            curl_command: cURL命令字符串
            
        Returns:
            dict: Cookie字典
        """
        try:
            cookies = {}
            
            # 从-b参数提取Cookie
            cookie_pattern = r"-b '([^']+)'"
            cookie_match = re.search(cookie_pattern, curl_command)
            if cookie_match:
                cookie_str = cookie_match.group(1)
                # self.logger.debug(f"从-b参数提取的Cookie字符串: {cookie_str}")
                for cookie in cookie_str.split('; '):
                    if '=' in cookie:
                        name, value = cookie.split('=', 1)
                        cookies[name] = value
            
            # 如果没有找到Cookie，尝试从请求头中提取
            if not cookies:
                headers = {}
                header_pattern = r"-H '([^:]+): ([^']+)'"
                for match in re.finditer(header_pattern, curl_command):
                    name, value = match.groups()
                    headers[name] = value
                
                if 'Cookie' in headers:
                    cookie_str = headers['Cookie']
                    # self.logger.debug(f"从Cookie头提取的Cookie字符串: {cookie_str}")
                    for cookie in cookie_str.split('; '):
                        if '=' in cookie:
                            name, value = cookie.split('=', 1)
                            cookies[name] = value
            
            if not cookies:
                self.logger.error("未找到有效的Cookie信息")
                return {}
                
            # 确保必要的Cookie存在
            required_cookies = ['JSESSIONID', 'tenantId', 'fine_remember_login']
            missing_cookies = [cookie for cookie in required_cookies if cookie not in cookies]
            if missing_cookies:
                self.logger.warning(f"缺少必要的Cookie: {', '.join(missing_cookies)}")
                return {}
            
            self.logger.debug(f"提取的Cookie: {cookies}")
            return cookies
            
        except Exception as e:
            self.logger.error(f"从cURL命令提取Cookie失败: {str(e)}")
            self.logger.exception("详细错误信息:")
            return {}

    def update_cookies_from_file(self) -> bool:
        """
        从cookie.txt文件更新Cookie
        
        Returns:
            bool: 更新是否成功
        """
        try:
            # 检查文件是否存在
            if not os.path.isfile(self.CURL_FILE):
                self.logger.error(f"文件 {self.CURL_FILE} 不存在")
                return False
            
            # 读取curl命令
            with open(self.CURL_FILE, 'r', encoding='utf-8') as f:
                curl_command = f.read().strip()
            
            # 提取Cookie
            cookies = self.extract_cookies_from_curl(curl_command)
            if not cookies:
                return False
            
            # 保存Cookie
            self.save_cookies(cookies)
            
            # 提取并保存token
            try:
                response_pattern = r'"accessToken":\s*"([^"]+)"'
                token_match = re.search(response_pattern, curl_command)
                if token_match:
                    self.access_token = token_match.group(1)
                    self.save_token({'accessToken': self.access_token})
                    self.headers['Authorization'] = f'Bearer {self.access_token}'
                    self.logger.debug("Token已更新")
            except Exception as e:
                self.logger.error(f"提取Token失败: {str(e)}")
            
            self.logger.debug("Cookie已更新")
            return True
            
        except Exception as e:
            self.logger.error(f"更新Cookie失败: {str(e)}")
            return False

    def save_cookies(self, cookies: dict):
        """
        保存Cookie到文件
        """
        try:
            cookie_path = Path(os.path.abspath(self.COOKIE_FILE))
            cookie_path.parent.mkdir(parents=True, exist_ok=True)
            
            with open(cookie_path, 'w', encoding='utf-8') as f:
                json.dump(cookies, f, indent=2, ensure_ascii=False)
            
            # self.logger.debug(f"Cookie已保存到: {cookie_path}")
        except Exception as e:
            self.logger.error(f"保存Cookie失败: {str(e)}")
            raise

    def load_cookies(self) -> dict:
        """
        从文件加载Cookie
        """
        try:
            cookie_path = Path(os.path.abspath(self.COOKIE_FILE))
            if not cookie_path.exists():
                self.logger.error(f"Cookie文件不存在: {cookie_path}")
                return {}
                
            with open(cookie_path, 'r', encoding='utf-8') as f:
                cookies = json.load(f)
                
                # 验证必要的Cookie是否存在
                required_cookies = ['JSESSIONID', 'tenantId', 'fine_remember_login']
                missing_cookies = [cookie for cookie in required_cookies if cookie not in cookies]
                if missing_cookies:
                    self.logger.error(f"Cookie文件缺少必要的Cookie: {', '.join(missing_cookies)}")
                    return {}
                
                return cookies
        except Exception as e:
            self.logger.error(f"加载Cookie失败: {str(e)}")
            return {}

    def check_login_status(self) -> bool:
        """
        检查登录状态
        """
        try:
            # 尝试访问需要登录的接口
            test_url = f"{self.BASE_URL}/v10/entry/access/old-platform-reportlet-entry-1040?width=1624&height=235"
            response = self.session.get(test_url, headers=self.headers, verify=False)
            # 记录响应详情以便调试
            # self.logger.debug(f"登录状态检查响应码: {response.status_code}")
            # self.logger.debug(f"响应头: {dict(response.headers)}")
            # self.logger.debug(f"响应内容: {response.text[:200]}") 
            
            # 检查响应状态和内容
            if response.status_code == 200:
                # 检查是否是错误页面
                if 'Oops' in response.text or '出错啦' in response.text:
                    self.logger.error("检测到错误页面")
                    return False
                    
                # 检查是否是登录页面
                if 'login' in response.text.lower() and 'password' in response.text.lower():
                    self.logger.error("检测到登录页面，表明需要重新登录")
                    return False
                
                # 检查是否包含session无效的错误信息
                if 'SessionID' in response.text and 'not exist' in response.text:
                    self.logger.error("Session已失效，需要重新登录")
                    return False
                
                # 检查响应内容是否包含表格数据的特征
                if 'WIP' in response.text :
                    self.logger.debug("检测到wip字段，认为登录有效")
                    return True
                    
                self.logger.debug("响应内容不包含明确的错误标识，认为登录有效")
                return True
                
            elif response.status_code == 302:
                self.logger.error("登录已过期，需要重定向到登录页面")
                return False
            else:
                self.logger.error(f"登录检查失败，HTTP状态码: {response.status_code}")
                return False
            
        except Exception as e:
            self.logger.error(f"检查登录状态失败: {str(e)}")
            self.logger.exception("详细错误信息:")
            return False

    def login(self) -> bool:
        """
        使用Cookie登录系统
        
        Returns:
            bool: 登录是否成功
        """
        try:
            self.logger.debug("尝试使用Cookie登录...")
            
            # 检查cookie.txt是否存在，优先从curl命令更新Cookie
            if os.path.isfile(self.CURL_FILE):
                self.logger.debug("发现cookie.txt文件，尝试更新Cookie...")
                if self.update_cookies_from_file():
                    cookies = self.load_cookies()
                    if cookies:
                        self.logger.debug(f"从cookie.txt更新Cookie成功: {cookies}")
                        self.session.cookies.update(cookies)
                        
                        # 尝试获取新token
                        if not self.refresh_token():
                            self.logger.error("无法获取有效的token")
                            return False
                        
                        if self.check_login_status():
                            self.logger.debug("登录成功")
                            return True
            
            # 如果没有cookie.txt或更新失败，尝试直接读取cookie文件
            cookies = self.load_cookies()
            if cookies:
                self.logger.debug(f"使用现有Cookie: {cookies}")
                self.session.cookies.update(cookies)
                
                # 尝试获取新token
                if not self.refresh_token():
                    self.logger.error("无法获取有效的token")
                    return False
                
                if self.check_login_status():
                    self.logger.debug("登录成功")
                    return True
            
            # 如果所有尝试都失败
            self.logger.error("""
            无法登录系统。请按以下步骤操作：
            1. 使用浏览器手动登录长电科技系统
            2. 登录成功后，按F12打开开发者工具
            3. 在Network标签页找到登录请求
            4. 右键请求 -> Copy -> Copy as cURL (bash)
            5. 将复制的内容保存到 config/cookie.txt 文件中
            
            注意：
            - 请确保复制的是登录成功后的请求
            - 确保cookie.txt中包含完整的cURL命令
            - 如果已有cookie.txt，请尝试重新获取最新的登录请求
            """)
            return False
            
        except Exception as e:
            self.logger.error(f"登录失败: {str(e)}")
            self.logger.exception("详细错误信息:")
            return False
        
    def _clean_session_cookies(self):
        """
        清理重复的sessionID Cookie
        """
        # 获取所有Cookie
        all_cookies = list(self.session.cookies)
        # 找到所有sessionID Cookie
        session_cookies = [cookie for cookie in all_cookies if cookie.name == 'sessionID']
        
        if len(session_cookies) > 1:
            # 保留最新的sessionID，删除其他的
            newest_cookie = session_cookies[-1]
            for cookie in session_cookies[:-1]:
                self.session.cookies.clear(cookie.domain, cookie.path, cookie.name)
            self.logger.debug(f"清理旧的sessionID Cookie，保留最新的: {newest_cookie.value}")
    
    def get_wip_data(self) -> Any:
        """
        获取WIP数据并保存为Excel
        
        Returns:
            bool: 是否成功获取并保存数据
        """
        try:
            # 清理重复的sessionID Cookie
            self._clean_session_cookies()

            # 确保sessionID存在
            session_id = self.session.cookies.get('sessionID')
            if not session_id:
                self.logger.error("缺少sessionID，需要重新登录")
                if not self.login():
                    return False
                self._clean_session_cookies()
                session_id = self.session.cookies.get('sessionID')
                
            # 更新请求头
            self.headers.update({
                'sessionID': session_id,
                'Accept': 'text/html, */*; q=0.01',
                'X-Requested-With': 'XMLHttpRequest',
                'Referer': f'{self.BASE_URL}/v10/entry/access/old-platform-reportlet-entry-1040?width=1624&height=312'
            })
        
            # 获取表格数据
            timestamp = int(datetime.now().timestamp() * 1000)
            report_url = f"{self.BASE_URL}/view/report"
            report_params = {
                "_": timestamp,
                "__boxModel__": "false",
                "op": "fr_view",
                "cmd": "view_content",
                "cid": "d3c43ee69a8d7208f0dc27529ae893f8#1744355701805#7f69b963",
                "reportIndex": "0",
                "iid": f"0.{str(timestamp)[-11:]}"
            }
            
            response = self.session.get(
                report_url,
                params=report_params,
                headers=self.headers,
                verify=False
            )

            # 确保fine_auth_token存在于Cookie中
            if 'fine_auth_token' not in self.session.cookies:
                self.session.cookies.set('fine_auth_token', self.access_token)
            
            if response.status_code != 200:
                self.logger.error("获取表格数据失败")
                return False
                
            # 解析JSON获取HTML内容
            data = json.loads(response.text)
            html = data['html']

            # 使用BeautifulSoup解析HTML
            soup = BeautifulSoup(html, 'html.parser')

            # 找到表格主体 - 使用第二个匹配的表格（包含数据的表格）
            tables = soup.find_all('table', class_='x-table', attrs={'style': lambda x: x and 'width:2592px' in x})
            if len(tables) < 2:
                self.logger.error("未找到数据表格")
                return False
                
            table = tables[1]  # 使用第二个表格

            # 获取表头
            headers = []
            header_row = tables[0].find('tr')  # 使用第一个表格的表头
            for td in header_row.find_all('td'):
                div = td.find('div')
                if div:
                    headers.append(div.text.strip())

            # 获取数据行
            data_rows = []
            for row in table.find_all('tr'):
                row_data = []
                for td in row.find_all('td'):
                    div = td.find('div')
                    if div:
                        text = div.text.strip()
                        # 移除特殊字符和多余的空格
                        text = ' '.join(text.split())
                        row_data.append(text)
                    else:
                        row_data.append('')
                if len(row_data) == len(headers) and any(row_data):  # 只添加非空行且列数匹配的行
                    # 跳过"总计"行
                    if not row_data[0].startswith('总计'):
                        data_rows.append(row_data)

            # 创建DataFrame并保存到Excel
            df = pd.DataFrame(data_rows, columns=headers)
            df.columns = [' '.join(col.split()) for col in df.columns]  # 清理列名

            # 获取输出目录
            output_dir = os.getenv("JCET_OUTPUT_DIR")
            os.makedirs(output_dir, exist_ok=True)

            # 生成文件名
            date_str = datetime.now().strftime("%Y%m%d")
            file_path = os.path.join(output_dir, f'长电科技_{date_str}.xlsx')

            # 将数据转换为DataFrame并保存为Excel
            df.to_excel(file_path, index=False)
            
            self.logger.info(f"成功获取并保存表格数据，共 {len(df)} 行")
            return file_path
            
        except Exception as e:
            self.logger.error(f"获取WIP数据失败: {str(e)}")
            self.logger.exception("详细错误信息:")
            return False
    
    def run(self) -> bool:
        """
        运行爬虫任务
        """
        if not self.login():
            return False
        try:
            filepath = self.get_wip_data()

            jcet_wip_handler = JcetWipHandler()
            df = jcet_wip_handler.process()
            
            # 更新数据库
            wip_assy_bll = WipAssyBLL()
            wip_assy_bll.update_supplier_progress(df.to_dict(orient="records"))

            self.close()
            # 移动文件,若存在则覆盖
            target_path = os.getenv("JCET_OUTPUT_DIR").replace("pending", "processed")+f"/{os.path.basename(filepath)}"
            if os.path.exists(target_path):
                os.remove(target_path)
            move_file(filepath, target_path)

            return True
        except Exception as e:
            self.logger.error(f"长电科技进度表处理失败: {str(e)}")
            move_file(filepath, os.getenv("JCET_OUTPUT_DIR").replace("pending", "failed")+f"/{os.path.basename(filepath)}")
            return False
        
        

