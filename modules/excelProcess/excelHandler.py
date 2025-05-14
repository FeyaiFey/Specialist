from typing import Dict, List, Any

from utils.logger import Logger
from .supplier.hisemi_delivery_handler import HisemiDeliveryHandler
from .supplier.hanqi_delivery_handler import HanQiDeliveryHandler
from .supplier.xinfeng_delivery_handler import XinFengDeliveryHandler
from .supplier.psmc_wip_handler import PsmcHandler
from .supplier.csmc_fab1_wip_handler import CsmcFAB1Handler
from .supplier.csmc_fab2_wip_handler import CsmcFAB2Handler
from .supplier.rsmc_wip_handler import RsmcHandler
from .supplier.hisemi_wip_handler import HisemiWipHandler
from .supplier.hanqi_wip_handler import HanqiWipHandler
from .supplier.utils import SupplierUtils

class ExcelHandler:
    """
    Excel文件处理器
    提供Excel文件的读取和分发处理功能
    """
    
    # 供应商处理器映射
    SUPPLIER_HANDLERS = {
        '封装送货单_池州华宇': HisemiDeliveryHandler,
        '封装进度表_池州华宇': HisemiWipHandler,
        '封装送货单_山东汉旗': HanQiDeliveryHandler,
        '封装进度表_山东汉旗': HanqiWipHandler,
        '封装送货单_江苏芯丰': XinFengDeliveryHandler,
        '晶圆进度表_荣芯': RsmcHandler,
        '晶圆进度表_上华FAB1': CsmcFAB1Handler,
        '晶圆进度表_上华FAB2': CsmcFAB2Handler,
        '晶圆进度表_力积电': PsmcHandler,
        # 可以继续添加其他供应商,爬虫项目除外
    }
    
    def __init__(self):
        """
        初始化文件处理器
        """
        self.logger = Logger().get_logger('excel_handler')
        
    def process_excel(self, match_result: Dict) -> Any:
        """
        处理送货单Excel文件
        
        Args:
            match_result: 规则引擎匹配结果
            枚举：
            match_result:{
                'actions': {'save_attachment': True, 'mark_as_read': True, 'attachment_folder': 'attachments/temp/封装送货单/池州华宇'},
                'name': '封装送货单-池州华宇',
                'category': '封装送货单',
                'supplier': '池州华宇',
                'attachments': ['attachments/temp/封装送货单/池州华宇/1.pdf', 'attachments/temp/封装送货单/池州华宇/2.pdf']
            }
            
        Returns:
            Dict[str, List[Dict[str, Any]]]: 处理结果，按日期组织的数据字典
        """
        try:
            supplier = match_result.get('supplier')
            category = match_result.get('category')
            merge_supplier = f"{category}_{supplier}"
            if not supplier or not category:
                self.logger.error(f"email_data中缺少供应商或类别信息")
                return None
                
            if merge_supplier not in self.SUPPLIER_HANDLERS:
                self.logger.error(f"未找到[{merge_supplier}]的处理器")
                return None
                
            # 实例化对应的处理器
            handler_class = self.SUPPLIER_HANDLERS[merge_supplier]
            handler = handler_class()
            
            # 处理Excel文件
            if match_result.get('category') == '封装送货单':
                self.logger.debug(f"开始处理供应商[{supplier}]的送货单")
                result = handler.process(match_result)
                if result is None:
                    self.logger.warning(f"供应商[{supplier}]的送货单处理未返回数据")
                    return None
                try:
                    utils = SupplierUtils()
                    utils.copy_to_gzjc(supplier)
                    return result
                except Exception as e:
                    self.logger.error(f"添加到工作进程失败: {str(e)}")
                    return None
                
            elif match_result.get('category') in ['封装进度表', '晶圆进度表']:
                self.logger.debug(f"开始处理供应商[{supplier}]的进度表")
                result = handler.process(match_result)
                if result is None:
                    self.logger.warning(f"供应商[{supplier}]的进度表处理未返回数据")
                    return None
                else:
                    return result
        except Exception as e:
            self.logger.error(f"处理{supplier}的{category}Excel文件时出错: {str(e)}")
            return {}