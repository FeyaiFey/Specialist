import pandas as pd
import datetime
from typing import Dict, List, Optional, Any

from .base_delivery_handler import BaseDeliveryExcelHandler
from app.utils.helpers import load_yaml
from app.utils.logger import get_logger

class HisemiWipHandler(BaseDeliveryExcelHandler):
    """
    池州华宇WIP处理器
    """
    def __init__(self):
        fields_config = load_yaml("app/config/wip_fields.yaml")
        self.config = fields_config["wip_fields"]["封装厂"]["池州华宇"]
        self.craft_forecast = fields_config["wip_fields"]["封装厂"]["craft_forecast"]
        self.data_format = fields_config["wip_fields"]["封装厂"]["data_format"]
        self.logger = get_logger(__name__)

    def process(self, match_result: Dict[str, Any]) -> pd.DataFrame:
        """
        处理池州华宇wip的Excel文件

        Args:
            match_result: 规则引擎匹配结果
            枚举:
             match_result:{
                'actions': {'save_attachment': True, 'mark_as_read': True, 'attachment_folder': 'attachments/temp/封装送货单/池州华宇'},
                'name': '封装送货单-池州华宇',
                'category': '封装送货单',
                'supplier': '池州华宇',
                'attachments': ['attachments/temp/封装厂/池州华宇/1.pdf', 'attachments/temp/封装厂/池州华宇/2.pdf']
            }
            
        Returns:
            pd.DataFrame: 处理结果
        """
        try:
            key_columns = self.config["关键字段映射"]
            data_format = self.data_format
            names = list(key_columns.keys())
            attachments = match_result.get("attachments")
            if not attachments:
                self.logger.error(f"匹配结果中缺少附件")
                return None
            
            # 读取Excel文件
            try:
                df = pd.read_excel(attachments[0], header=0, sheet_name="Sheet1")
                
                # 检查DataFrame是否为空
                if df.empty:
                    self.logger.error("Excel文件内容为空")
                    return None
                    
                # 检查是否包含所需的列
                missing_columns = set(names) - set(df.columns)
                if missing_columns:
                    self.logger.error(f"Excel文件缺少必要的列: {missing_columns}")
                    return None
                    
            except ValueError as e:
                if "No sheet named" in str(e):
                    self.logger.error("Excel文件中没有名为'Sheet1'的工作表")
                    return None
                raise

            df = df[names]
            
            # 创建映射字典并重命名列
            mapping_dict = {k: v for k, v in key_columns.items()}
            df.rename(columns=mapping_dict, inplace=True)

            # 将数值列转换为数值类型
            numerical_columns = list(self.craft_forecast.keys())
            df[numerical_columns] = df[numerical_columns].apply(pd.to_numeric, errors='coerce').fillna(0)

            # 确保订单号列为字符串类型
            df["订单号"] = df["订单号"].fillna('').astype(str)

            # 从后往前遍历numerical_columns，找到第一个值大于0的列名
            df["当前工序"] = df.apply(
                lambda row: "STOCK" if row["仓库库存"] > 0 else next(
                    (col for col in numerical_columns[::-1] if row[col] > 0),
                    "研磨"
                ),
                axis=1
            )

            # 根据当前工序，计算预计完成时间
            df["预计交期"] = df["当前工序"].apply(
                lambda x: (pd.Timestamp.now() + pd.Timedelta(days=self.craft_forecast.get(x, 0))).date() if x else None
            )

            # 如果除了研磨,切割,待装片,其他工序的和都为0,则预计交期为空
            exclude_process = ["研磨", "切割", "待装片"]
            process_columns = [col for col, days in self.craft_forecast.items() if col not in exclude_process]
            other_process_mask = df[process_columns].sum(axis=1) == 0
            df.loc[other_process_mask, "预计交期"] = pd.NaT

            # 计算预计数量
            tomorrow_columns = [k for k, v in self.craft_forecast.items() if v <= 1]
            three_days_columns = [k for k, v in self.craft_forecast.items() if v <= 3]
            seven_days_columns = [k for k, v in self.craft_forecast.items() if v <= 7]

            df["次日预计"] = df[tomorrow_columns].sum(axis=1, min_count=1)
            df["三日预计"] = df[three_days_columns].sum(axis=1, min_count=1)
            df["七日预计"] = df[seven_days_columns].sum(axis=1, min_count=1)

            # 添加供应商信息和完成时间
            df["封装厂"] = "池州华宇"
            df["finished_at"] = pd.NaT

            # 过滤掉订单号为空的记录
            df = df[df["订单号"].str.strip() != ""]

            df = df[data_format]

            self.logger.debug(f"成功处理池州华宇WIP文件")

            return df

        except Exception as e:
            self.logger.error(f"处理池州华宇WIP文件时发生错误: {e}")
            return None
        
    
