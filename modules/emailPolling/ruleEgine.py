from typing import Dict, Any, List, Optional, Union, Tuple
from fnmatch import fnmatch
from dataclasses import dataclass
import re

from utils.logger import Logger
from utils.helpers import load_yaml


@dataclass
class EmailConditions:
    """邮件匹配条件"""
    from_: Optional[List[str]] = None
    to: Optional[List[str]] = None
    cc: Optional[List[str]] = None
    subject_contains: Optional[List[str]] = None
    subject_regex: Optional[str] = None

@dataclass
class EmailActions:
    """邮件处理动作"""
    save_attachment: bool = False
    mark_as_read: bool = True
    attachment_folder: Optional[str] = None

@dataclass
class EmailRule:
    """邮件处理规则"""
    name: str
    category: str
    supplier: str
    conditions: EmailConditions
    actions: EmailActions
    enabled: bool = True

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'EmailRule':
        """从字典创建规则对象"""
        conditions = EmailConditions(
            from_=data['conditions'].get('from'),
            to=data['conditions'].get('to'),
            cc=data['conditions'].get('cc'),
            subject_contains=data['conditions'].get('subject_contains'),
            subject_regex=data['conditions'].get('subject_regex')
        )
        actions = EmailActions(
            save_attachment=data['actions'].get('save_attachment', False),
            mark_as_read=data['actions'].get('mark_as_read', True),
            attachment_folder=data['actions'].get('attachment_folder')
        )
        return cls(
            name=data['name'],
            category=data['category'],
            supplier=data['supplier'],
            conditions=conditions,
            actions=actions,
            enabled=data.get('enabled', True)
        )
class RuleEngine:
    """邮件规则引擎"""
    def __init__(self, rules_file: str):
        """
        初始化规则引擎
        Args:
            rules_file: 规则配置文件路径
        """
        self.logger = Logger().get_logger('RuleEngine')
        self.rules = self._load_rules(rules_file)
        

    def _load_rules(self, rules_file: str) -> Dict[str, List[EmailRule]]:
        """加载规则配置"""
        try:
            email_rules = load_yaml(rules_file)
            self.logger.debug(f"成功加载{len(email_rules['rules'])}条规则")
            return email_rules        
        except Exception as e:
            self.logger.error(f"加载规则配置失败: {str(e)}")
            raise

    def match_pattern(self, value: Union[str, List[str]], patterns: List[str]) -> bool:
        """
        检查值是否匹配模式列表中的任意一个
        
        支持通配符匹配，如 "*@domain.com"
        
        参数:
            value: 要匹配的值（字符串或列表）
            patterns: 模式列表
            
        返回:
            bool: 是否匹配成功
        """
        if not patterns:
            return True
        if isinstance(value, list):
            return any(any(fnmatch(addr.lower(), pattern.lower()) 
                         for pattern in patterns)
                     for addr in value)
        return any(fnmatch(value.lower(), pattern.lower()) for pattern in patterns)

    def check_rule_conditions(self, email_data: Dict, rule: Dict) -> bool:
        """
        检查邮件是否匹配规则条件
        
        检查邮件的发件人、收件人、抄送人、主题是否满足规则中定义的条件
        所有条件都满足才返回True
        
        参数:
            email_data: 邮件数据字典
            rule: 规则字典
            
        返回:
            bool: 是否满足所有条件
        """
        conditions = rule.get('conditions', {})
        
        # 检查发件人
        if not self._check_from_condition(email_data, conditions):
            return False
            
        # 检查收件人
        if not self._check_to_condition(email_data, conditions):
            return False
            
        # 检查抄送人
        if not self._check_cc_condition(email_data, conditions):
            return False
            
        # 检查主题
        if not self._check_subject_condition(email_data, conditions):
            return False
                
        return True

    def _check_from_condition(self, email_data: Dict, conditions: Dict) -> bool:
        """检查发件人条件"""
        if 'from_contains' in conditions:
            return self.match_pattern(email_data.get('from', ''), conditions['from_contains'])
        return True

    def _check_to_condition(self, email_data: Dict, conditions: Dict) -> bool:
        """检查收件人条件"""
        if 'to_contains' in conditions:
            return self.match_pattern(email_data.get('to', []), conditions['to_contains'])
        return True

    def _check_cc_condition(self, email_data: Dict, conditions: Dict) -> bool:
        """检查抄送人条件"""
        if 'cc_contains' in conditions:
            return self.match_pattern(email_data.get('cc', []), conditions['cc_contains'])
        return True

    def _check_subject_condition(self, email_data: Dict, conditions: Dict) -> bool:
        """检查主题条件"""
        subject = email_data.get('subject', '')
        
        # 检查主题关键词
        if 'subject_contains' in conditions:
            if not any(keyword.lower() in subject.lower() 
                      for keyword in conditions['subject_contains']):
                return False
                
        # 检查主题正则表达式
        if conditions.get('subject_regex'):
            if not re.search(conditions['subject_regex'], subject):
                return False
                
        return True
    
    def apply_rules(self, email_data: Dict) -> Dict[str, Any]:
        """
        应用邮件规则
        

        遍历所有启用的规则，返回第一个匹配的规则的动作和相关信息
        
        参数:
            email_data: 邮件数据字典
            
        返回:
            tuple: (规则动作字典, 规则名称, 邮件类别, 供应商)
            {
                'actions': {'save_attachment': True, 'mark_as_read': True, 'attachment_folder': 'attachments/temp/封装送货单/池州华宇'},
                'name': '封装送货单-池州华宇',
                'category': '封装送货单',
                'supplier': '池州华宇'
            }

        """
        self.logger.debug(f"开始匹配规则，邮件主题: {email_data.get('subject', '')}")

        # 检查每个规则
        for rule in self.rules.get('rules', []):
            if rule.get('enabled', True) and self.check_rule_conditions(email_data, rule):
                self.logger.info(f"邮件匹配规则: {rule.get('name', 'unnamed_rule')}")
                return {
                    'actions': rule.get('actions', {}),
                    'name': rule.get('name', 'unnamed_rule'),
                    'category': rule.get('category', '未分类'),
                    'supplier': rule.get('supplier', '未知'),
                    'allowed_extensions': rule.get('allowed_extensions', [])
                }
        
        # 如果没有匹配的规则，使用默认规则
        default_rule = self.rules.get('默认规则', {})
        self.logger.debug("邮件使用默认规则处理")
        return {
            'actions': default_rule.get('actions', {}),
            'name': default_rule.get('name', 'unnamed_rule'),
            'category': default_rule.get('category', '未分类'),
            'supplier': default_rule.get('supplier', '未知'),
            'allowed_extensions': default_rule.get('allowed_extensions', [])
        }