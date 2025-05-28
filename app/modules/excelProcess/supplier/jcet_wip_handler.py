import pandas as pd
import os
from datetime import date
from typing import Dict, List, Optional, Any

from app.utils.helpers import load_yaml
from app.utils.logger import get_logger

class JcetWipHandler():
    """
    长电科技WIP处理器
    """
    def __init__(self):
        fields_config = load_yaml("app/config/wip_fields.yaml")
        self.config = fields_config["wip_fields"]["封装厂"]["长电科技"]
        self.file_dir = rf'downloads\封装进度表\长电科技\长电科技_{date.today().strftime("%Y%m%d")}.xlsx'
        self.craft_forecast = fields_config["wip_fields"]["封装厂"]["craft_forecast"]
        self.data_format = fields_config["wip_fields"]["封装厂"]["data_format"]
        self.logger = get_logger(__name__)

    def process(self) -> pd.DataFrame:
        """
        处理长电科技的WIP文件
        """
        step = self.config["关键字段映射"].keys()
        df_raw = pd.DataFrame(columns=step)

        if not os.path.exists(self.file_dir):
            self.logger.warning(f"文件不存在: {self.file_dir}")
            return None
        
        try:
            # 读取Excel文件并选择需要的列
            df = pd.read_excel(self.file_dir, sheet_name="Sheet1")
            # 检查DataFrame是否为空
            if df.empty:
                self.logger.warning("Excel文件内容为空")
                return None
            
            names = list(self.config["关键字段映射"].keys())
            df = df[names]
            key_columns = {k: v for k, v in self.config["关键字段映射"].items()}

            # 创建映射字典并重命名列
            mapping_dict = {k: v for k, v in key_columns.items()}
            df.rename(columns=mapping_dict, inplace=True)

            diff_cols = ['待装片','银胶固化','等离子清洗1','三目检','等离子清洗2','回流焊','切筋成型']

            for col in diff_cols:
                if not col in df.columns:
                    df[col] = 0
            
            df['测编打印'] = df['测试'] + df['编带']

            df["扣留信息"] = pd.NaT

            numerical_columns = list(self.craft_forecast.keys())
            # 只处理存在的数值列
            existing_numerical_columns = [col for col in numerical_columns if col in df.columns]
            
            # 处理千分位符号并转换为数字
            for col in existing_numerical_columns:
                df[col] = df[col].astype(str).str.replace(',', '').apply(pd.to_numeric, errors='coerce').fillna(0)
            
            # 处理在线合计和仓库库存
            df["在线合计"] = df["在线合计"].astype(str).str.replace(',', '').apply(pd.to_numeric, errors='coerce').fillna(0)
            df["仓库库存"] = df["仓库库存"].astype(str).str.replace(',', '').apply(pd.to_numeric, errors='coerce').fillna(0)

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

            df["封装厂"] = "长电科技"
            df["finished_at"] = pd.NaT

            df = df[self.data_format]

            return df
        except Exception as e:
            self.logger.error(f"处理长电科技WIP文件失败: {e}")
            return None
        
        

