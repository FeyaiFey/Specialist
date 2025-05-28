import pandas as pd
import os
from datetime import date
from typing import Dict, List, Optional, Any

from app.utils.helpers import load_yaml
from app.utils.logger import get_logger

class XinfengWipHandler():
    """
    江苏芯丰WIP处理器
    """
    def __init__(self):
        fields_config = load_yaml("app/config/wip_fields.yaml")
        self.config = fields_config["wip_fields"]["封装厂"]["江苏芯丰"]
        self.file_dir = rf'downloads\封装进度表\江苏芯丰\江苏芯丰_{date.today().strftime("%Y%m%d")}.xlsx'
        self.craft_forecast = fields_config["wip_fields"]["封装厂"]["craft_forecast"]
        self.data_format = fields_config["wip_fields"]["封装厂"]["data_format"]
        self.logger = get_logger(__name__)

    def process(self) -> pd.DataFrame:
        """
        处理江苏芯丰的WIP文件
        """
        step = self.config["关键字段映射"].keys()
        df_raw = pd.DataFrame(columns=step)

        if not os.path.exists(self.file_dir):
            self.logger.error(f"文件不存在: {self.file_dir}")
            return None
        
        try:
            # 读取Excel文件并选择需要的列
            df = pd.read_excel(self.file_dir, sheet_name="Sheet1")

            # 检查DataFrame是否为空
            if df.empty:
                self.logger.error("Excel文件内容为空")
                return None
            df = df[['customerSoCode', 'currentqty', 'stepName']]

            # 按customerSoCode和stepName分组求和
            df = df.groupby(['customerSoCode', 'stepName'])['currentqty'].sum().reset_index()

            # 数据透视，将stepName转换为列
            df = df.pivot(
                index='customerSoCode',
                columns='stepName',
                values='currentqty'
            ).reset_index()

            # 合并原始数据
            df = pd.merge(df, df_raw, on='customerSoCode', how='left', suffixes=('', '_drop'))
            df = df.loc[:, ~df.columns.str.endswith('_drop')]

            # 填充缺失值为0并转换为整数
            df = df.fillna(0)
            numeric_cols = df.columns.difference(['customerSoCode'])
            df[numeric_cols] = df[numeric_cols].astype(int)

            # 计算在线合计
            total_cols = numeric_cols.difference(['TOTAL(TOTAL)'])
            df['TOTAL(TOTAL)'] = df[total_cols].sum(axis=1)

            # 获取并应用字段映射
            field_mapping = self.config['关键字段映射']
            df = df.rename(columns=field_mapping)

            df['电镀'] = df['电镀1'] + df['电镀2']
            df['打印'] = df['打印1'] + df['打印2']

            df.drop(columns=['电镀1', '电镀2', '打印1', '打印2'], inplace=True)

            df = df[['订单号', '研磨', '切割', '待装片', '装片', '银胶固化', '等离子清洗1', '键合', '三目检', '等离子清洗2', '塑封', '后固化', '回流焊', '电镀', '打印', '后切割', '切筋成型', '外观检', '测编打印', '包装', '待入库', '在线合计', '仓库库存', '扣留信息']]
            
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
            df["封装厂"] = "江苏芯丰"
            df["finished_at"] = pd.NaT

            # 过滤掉订单号为空的记录
            df = df[df["订单号"].str.strip() != ""]

            df = df[self.data_format]

            self.logger.debug(f"处理江苏芯丰的WIP文件成功")

            return df
        except Exception as e:
            self.logger.error(f"处理江苏芯丰的WIP文件失败: {e}")
            return None
        
        

