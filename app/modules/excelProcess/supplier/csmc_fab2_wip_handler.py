import pandas as pd
from typing import Dict, List, Optional, Any

from .base_delivery_handler import BaseDeliveryExcelHandler
from app.utils.helpers import load_yaml
from app.utils.logger import get_logger

class CsmcFAB2Handler(BaseDeliveryExcelHandler):
    """
    上华FAB2Excel处理器
    """
    def __init__(self):
        fields_config = load_yaml("app/config/wip_fields.yaml")
        self.config = fields_config["wip_fields"]["晶圆厂"]["上华FAB2"]
        self.data_format = fields_config["wip_fields"]["data_format"]
        self.logger = get_logger(__name__)

    def process(self, match_result: Dict[str, Any]) -> pd.DataFrame:
        """
        处理上华FAB2的Excel文件

        Args:
            match_result: 规则引擎匹配结果
            枚举:
             match_result:{
                'actions': {'save_attachment': True, 'mark_as_read': True, 'attachment_folder': 'attachments/temp/封装送货单/池州华宇'},
                'name': '封装送货单-池州华宇',
                'category': '封装送货单',
                'supplier': '池州华宇',
                'attachments': ['attachments/temp/晶圆厂/上华/1.pdf', 'attachments/temp/晶圆厂/上华/2.pdf']
            }
            
        Returns:
            pd.DataFrame: 处理结果
        """
        try:
            header = self.config["header"]
            names = self.config["names"]
            name_values = list(names.values())
            data_format = self.data_format
            attachments = match_result.get("attachments")
            if not attachments:
                self.logger.error(f"匹配结果中缺少附件")
                return None
            
            # 读取Excel文件
            try:
                df = pd.read_excel(attachments[0], header=header, sheet_name="wip")
                
                # 检查DataFrame是否为空
                if df.empty:
                    self.logger.warning("Excel文件内容为空")
                    return None
                    
                # 检查是否包含所需的列
                missing_columns = set(name_values) - set(df.columns)
                if missing_columns:
                    self.logger.error(f"Excel文件缺少必要的列: {missing_columns}")
                    return None
                    
            except ValueError as e:
                if "No sheet named" in str(e):
                    self.logger.error("Excel文件中没有名为'wip'的工作表")
                    return None
                raise
            df = df[name_values]
            # 创建反向映射字典
            reverse_names = {v: k for k, v in names.items()}
            # 重命名列
            df.rename(columns=reverse_names, inplace=True)

            # 将layerCount列按"/"拆分，并创建新的currentPosition和layerCount列
            df[["currentPosition", "layerCount"]] = df["layerCount"].str.split("/", expand=True)
            
            # 将拆分后的列转换为数值类型,处理错误值为NaN
            df["currentPosition"] = pd.to_numeric(df["currentPosition"], errors='coerce')
            df["layerCount"] = pd.to_numeric(df["layerCount"], errors='coerce')

            # 安全计算remainLayer
            df["remainLayer"] = df.apply(
                lambda row: row["layerCount"] - row["currentPosition"]
                if pd.notna(row["layerCount"]) and pd.notna(row["currentPosition"])
                else None,
                axis=1
            )

            # 安全处理日期转换
            df["forecastDate"] = pd.to_datetime(df["forecastDate"], errors='coerce')
            # 只对非空日期进行偏移计算
            df["forecastDate"] = df["forecastDate"].apply(
                lambda x: (x + pd.Timedelta(days=7)).date() if pd.notna(x) else pd.NaT
            )

            df["supplier"] = "上华FAB2"
            df["finished_at"] = pd.NaT

            df = df[data_format]
            self.logger.debug(f"成功处理上华FAB2Excel文件")
            return df
        except Exception as e:
            self.logger.error(f"处理上华FAB2Excel文件失败: {e}")
            return None

