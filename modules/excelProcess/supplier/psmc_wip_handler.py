import pandas as pd
from typing import Dict, List, Optional, Any

from .base_delivery_handler import BaseDeliveryExcelHandler
from utils.helpers import load_yaml
from utils.logger import Logger


class PsmcHandler(BaseDeliveryExcelHandler):
    """
    力积电Excel处理器
    """
    def __init__(self):
        self.logger = Logger().get_logger('psmcHandler')
        fields_config = load_yaml("config/wip_fields.yaml")
        self.config = fields_config["wip_fields"]["晶圆厂"]["力积电"]
        self.data_format = fields_config["wip_fields"]["data_format"]

    def process(self, match_result: Dict[str, Any]) -> pd.DataFrame:
        """
        处理力积电的Excel文件

        Args:
            match_result: 规则引擎匹配结果
            枚举:
             match_result:{
                'actions': {'save_attachment': True, 'mark_as_read': True, 'attachment_folder': 'attachments/temp/封装送货单/池州华宇'},
                'name': '封装送货单-池州华宇',
                'category': '封装送货单',
                'supplier': '池州华宇',
                'attachments': ['attachments/temp/晶圆厂/力积电/1.pdf', 'attachments/temp/晶圆厂/力积电/2.pdf']
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
                df = pd.read_excel(attachments[0], header=header)
                
                # 检查DataFrame是否为空
                if df.empty:
                    self.logger.error("Excel文件内容为空")
                    return None
                    
                # 检查是否包含所需的列
                missing_columns = set(name_values) - set(df.columns)
                if missing_columns:
                    self.logger.error(f"Excel文件缺少必要的列: {missing_columns}")
                    return None
                    
            except ValueError as e:
                if "No sheet named" in str(e):
                    self.logger.error("Excel文件中没有默认工作表")
                    return None
                raise
            except pd.errors.EmptyDataError:
                self.logger.error("Excel文件为空")
                return None
            
            df = df[name_values]
            # 创建反向映射字典
            reverse_names = {v: k for k, v in names.items()}
            # 重命名列
            df.rename(columns=reverse_names, inplace=True)

            # 处理非数值型错误
            df["layerCount"] = pd.to_numeric(df["layerCount"], errors='coerce')
            df["remainLayer"] = pd.to_numeric(df["remainLayer"], errors='coerce')
            # 计算currentPosition，处理NaN情况
            df["currentPosition"] = df.apply(
                lambda row: row["layerCount"] - row["remainLayer"] 
                if pd.notna(row["layerCount"]) and pd.notna(row["remainLayer"]) 
                else pd.NaT, 
                axis=1
            )
            df["supplier"] = "力积电"
            df["finished_at"] = pd.NaT
            hold_mask = df["forecastDate"].str.contains("HOLD", na=False)
            wh_mask = df["forecastDate"].str.contains("WH", na=False)

            # 保存原始的forecastDate值到status字段
            df.loc[hold_mask, "status"] = df.loc[hold_mask, "forecastDate"]
            df.loc[wh_mask, "status"] = "STOCK"

            self.logger.debug(df[["purchaseOrder","status","forecastDate"]])

            # 将forecastDate列转换为日期类型,格式为%Y-%m-%d，处理错误值
            df["forecastDate"] = pd.to_datetime(df["forecastDate"], errors='coerce')
            # 将forecastDate列转换为日期类型,格式为%Y-%m-%d，处理错误值
            df["forecastDate"] = df["forecastDate"].apply(
                lambda x: (x + pd.Timedelta(days=7)).date() if pd.notna(x) else pd.NaT
            )

            self.logger.debug(df[["purchaseOrder","status","forecastDate"]])

            # 清除特殊状态的forecastDate
            df.loc[hold_mask, "forecastDate"] = pd.NaT
            df.loc[wh_mask, "forecastDate"] = (pd.Timestamp.today() + pd.Timedelta(days=3)).date()

            self.logger.debug(df[["purchaseOrder","status","forecastDate"]])

            df = df[data_format]
            self.logger.debug(f"成功处理力积电Excel文件")
            return df
        except Exception as e:
            self.logger.error(f"处理力积电Excel文件失败: {e}")
            return None

