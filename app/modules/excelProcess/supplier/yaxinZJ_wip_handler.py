import pandas as pd
from typing import Dict, Any
import warnings
warnings.filterwarnings("ignore")


from app.utils.helpers import load_yaml
from app.utils.logger import get_logger

class YaxinZJWipHandler():
    """
    浙江亚芯WIP处理器
    """
    def __init__(self):
        fields_config = load_yaml("app/config/wip_fields.yaml")
        self.craft_forecast = fields_config["wip_fields"]["封装厂"]["craft_forecast"]
        self.logger = get_logger(__name__)
        self.data_format = fields_config["wip_fields"]["封装厂"]["data_format"]

    def process(self, match_result: Dict[str, Any]) -> pd.DataFrame:
        """
        处理浙江亚芯的WIP文件
        """
        file_path = match_result.get("attachments")[0]
        if not file_path:
            self.logger.error(f"匹配结果中缺少浙江亚芯进度表附件")
            return None
        
        try:
            df = pd.read_excel(file_path, header=0)
            if df.empty:
                self.logger.error(f"浙江亚芯进度表无实际内容")
                return None
            
            # 确认列是否存在
            try:
                df = df[
                ["客户订单号",
                "装片",
                "装片2",
                "装片3",
                "前固化",
                "前固化2",
                "前固化3",
                "PLASMA1",
                "键合",
                "点胶",
                "键合检验",
                "键合检验2",
                "塑封",
                "后固化",
                "电镀",
                "去溢料",
                "打印",
                "切筋",
                "切筋打弯(高站高)",
                "编带检",
                "条检",
                "测试",
                "外检",
                "包装"]
                ]
            except:
                self.logger.error(f"浙江亚芯进度表缺少必要列")
                return None
            
            df[
                ["装片",
                "装片2",
                "装片3",
                "前固化",
                "前固化2",
                "前固化3",
                "PLASMA1",
                "键合",
                "点胶",
                "键合检验",
                "键合检验2",
                "塑封",
                "后固化",
                "电镀",
                "去溢料",
                "打印",
                "切筋",
                "切筋打弯(高站高)",
                "编带检",
                "条检",
                "测试",
                "外检",
                "包装"
                ]] = df[
                    ["装片",
                    "装片2",
                    "装片3",
                    "前固化",
                    "前固化2",
                    "前固化3",
                    "PLASMA1",
                    "键合",
                    "点胶",
                    "键合检验",
                    "键合检验2",
                    "塑封",
                    "后固化",
                    "电镀",
                    "去溢料",
                    "打印",
                    "切筋",
                    "切筋打弯(高站高)",
                    "编带检",
                    "条检",
                    "测试",
                    "外检",
                    "包装"]].apply(pd.to_numeric, errors='coerce').fillna(0)

            df.rename(columns={"装片":"装片1","前固化":"前固化1","键合检验":"键合检验1"},inplace=True)

            df["装片"] = df[["装片1","装片2","装片3"]].sum(axis=1, min_count=1)
            df["银胶固化"] = df[["前固化1","前固化2","前固化3"]].sum(axis=1, min_count=1)
            df["三目检"] = df["键合检验1"] + df["键合检验2"]
            df["电镀"] = df["电镀"] + df["去溢料"]
            df["切筋成型"] = df["切筋"] + df["切筋打弯(高站高)"]
            df["外观检"] = df["条检"] + df["外检"] + df["编带检"]

            df.drop(columns=["装片1","装片2","装片3","前固化1","前固化2","前固化3","键合检验1","键合检验2","条检","外检","编带检","切筋打弯(高站高)"],inplace=True)

            df[['研磨', '切割', '待装片', '等离子清洗2', '后切割', '回流焊', '待入库','在线合计', '仓库库存']] = 0

            df["扣留信息"] = ""

            df.rename(columns={"客户订单号":"订单号","PLASMA1":"等离子清洗1","测试":"测编打印"},inplace=True)

            df = df[
                ['订单号', 
                '研磨', 
                '切割', 
                '待装片', 
                '装片', 
                '银胶固化', 
                '等离子清洗1', 
                '键合', 
                '三目检', 
                '等离子清洗2', 
                '塑封', 
                '后固化', 
                '回流焊', 
                '电镀', 
                '打印', 
                '后切割', 
                '切筋成型', 
                '外观检', 
                '测编打印', 
                '包装', 
                '待入库', 
                '在线合计', 
                '仓库库存', 
                '扣留信息']]
            
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
            df["封装厂"] = "浙江亚芯"
            df["finished_at"] = pd.NaT

            # 过滤掉订单号为空的记录
            df = df[df["订单号"].str.strip() != ""]

            df = df[self.data_format]

            # 替换订单号内容

            self.logger.debug(f"处理浙江亚芯的WIP文件成功")

            return df
        except Exception as e:
            self.logger.error(f"处理浙江亚芯的WIP文件失败: {e}")
            return None
        
        

