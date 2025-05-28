import pandas as pd
import datetime
from typing import Dict, List, Optional, Any

from .base_delivery_handler import BaseDeliveryExcelHandler
from app.utils.helpers import load_yaml
from app.utils.logger import get_logger

class HanqiWipHandler(BaseDeliveryExcelHandler):
    """
    山东汉旗WIP处理器
    """
    def __init__(self):
        fields_config = load_yaml("app/config/wip_fields.yaml")
        self.config = fields_config["wip_fields"]["封装厂"]["山东汉旗"]
        self.craft_forecast = fields_config["wip_fields"]["封装厂"]["craft_forecast"]
        self.data_format = fields_config["wip_fields"]["封装厂"]["data_format"]
        self.logger = get_logger(__name__)

    def process(self, match_result: Dict[str, Any]) -> pd.DataFrame:
        """
        处理山东汉旗wip的Excel文件

        Args:
            match_result: 规则引擎匹配结果
            枚举:
             match_result:{
                'actions': {'save_attachment': True, 'mark_as_read': True, 'attachment_folder': 'attachments/temp/封装送货单/山东汉旗'},
                'name': '封装送货单-山东汉旗',
                'category': '封装送货单',
                'supplier': '山东汉旗',
                'attachments': ['attachments/temp/封装厂/山东汉旗/1.pdf', 'attachments/temp/封装厂/山东汉旗/2.pdf']
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
                df = pd.read_excel(attachments[0], header=0)
                
                # 检查DataFrame是否为空
                if df.empty:
                    self.logger.error("Excel文件内容为空")
                    return None
                    
                # 检查是否包含所需的列
                df.columns = df.columns.str.strip()
                missing_columns = set(names) - set(df.columns)
                if missing_columns:
                    self.logger.error(f"Excel文件缺少必要的列: {missing_columns}")
                    return None
                    
            except ValueError as e:
                if "No sheet named" in str(e):
                    self.logger.error("Excel文件中没有名为'Sheet1'的工作表")
                    return None
                raise

            # 清理列名中的空格
            df.columns = df.columns.str.strip()

            df = df[names]

            key_columns = {k.strip(): v for k, v in key_columns.items()}
            
            # 创建映射字典并重命名列
            mapping_dict = {k: v for k, v in key_columns.items()}
            df.rename(columns=mapping_dict, inplace=True)

            # 整理数据
            marking_columns = ["Mar_king打印", "打印前烘烤"]
            # 只对存在的列进行求和
            existing_marking_columns = [col for col in marking_columns if col in df.columns]
            if existing_marking_columns:
                df[existing_marking_columns] = df[existing_marking_columns].apply(pd.to_numeric, errors='coerce').fillna(0)
                df["打印"] = df[existing_marking_columns].sum(axis=1, min_count=1)
            else:
                df["打印"] = 0

            test_columns = ["测试打印", "测试编带", "测试管装", "编带"]
            # 只对存在的列进行求和
            existing_test_columns = [col for col in test_columns if col in df.columns]
            if existing_test_columns:
                df[existing_test_columns] = df[existing_test_columns].apply(pd.to_numeric, errors='coerce').fillna(0)
                df["测编打印"] = df[existing_test_columns].sum(axis=1, min_count=1)
            else:
                df["测编打印"] = 0


            df[["研磨","切割","待装片","等离子清洗1","三目检","等离子清洗2","回流焊","后切割","外观检","待入库"]] = 0

            df["扣留信息"] = pd.NaT



            numerical_columns = list(self.craft_forecast.keys())
            # 只处理存在的数值列
            existing_numerical_columns = [col for col in numerical_columns if col in df.columns]
            df[existing_numerical_columns] = df[existing_numerical_columns].apply(pd.to_numeric, errors='coerce').fillna(0)

            df[["在线合计","仓库库存"]] = df[["在线合计","仓库库存"]].apply(pd.to_numeric, errors='coerce').fillna(0)

            df = df[['订单号', '研磨', '切割', '待装片', '装片', '银胶固化', '等离子清洗1', '键合', '三目检', '等离子清洗2', '塑封', '后固化', '回流焊', '电镀', '打印', '后切割', '切筋成型', '外观检', '测编打印', '包装', '待入库', '在线合计', '仓库库存', '扣留信息']]

            # 从后往前遍历numerical_columns，找到第一个值大于0的列名
            df["当前工序"] = df.apply(
                lambda row: "STOCK" if row["仓库库存"] > 0 else next(
                    (col for col in existing_numerical_columns[::-1] if row[col] > 0),
                    "研磨"
                ),
                axis=1
            )

            # 根据当前工序，计算预计完成时间 汉旗要加快递2天
            df["预计交期"] = df["当前工序"].apply(
                lambda x: pd.Timestamp.now().date() + pd.Timedelta(days=self.craft_forecast.get(x, 0) + 2) if x else pd.NaT
            )

            # 如果除了研磨,切割,待装片,其他工序的和都为0,则预计交期为空
            exclude_process = ["研磨", "切割", "待装片"]
            process_columns = [col for col, days in self.craft_forecast.items() if col not in exclude_process]
            # 只对存在的工序列进行求和
            existing_process_columns = [col for col in process_columns if col in df.columns]
            if existing_process_columns:
                other_process_mask = df[existing_process_columns].sum(axis=1) == 0
                df.loc[other_process_mask, "预计交期"] = pd.NaT
            
            # 计算不同时间段的预计产出
            tomorrow_columns = [k for k, v in self.craft_forecast.items() if v <= 1]
            three_days_columns = [k for k, v in self.craft_forecast.items() if v <= 3]
            seven_days_columns = [k for k, v in self.craft_forecast.items() if v <= 7]

            # 只对存在的列进行求和
            existing_tomorrow_columns = [col for col in tomorrow_columns if col in df.columns]
            existing_three_days_columns = [col for col in three_days_columns if col in df.columns]
            existing_seven_days_columns = [col for col in seven_days_columns if col in df.columns]

            df["次日预计"] = df[existing_tomorrow_columns].sum(axis=1, min_count=1) if existing_tomorrow_columns else 0
            df["三日预计"] = df[existing_three_days_columns].sum(axis=1, min_count=1) if existing_three_days_columns else 0
            df["七日预计"] = df[existing_seven_days_columns].sum(axis=1, min_count=1) if existing_seven_days_columns else 0

            df["封装厂"] = "山东汉旗"
            df["finished_at"] = pd.NaT

            df = df[data_format]

            self.logger.debug(f"成功处理山东汉旗Excel文件")

            return df

        except Exception as e:
            self.logger.error(f"处理山东汉旗Excel文件时发生错误: {e}")
            return None
        
    
