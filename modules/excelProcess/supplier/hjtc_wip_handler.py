import pandas as pd
from typing import Dict, List, Optional, Any

from utils.logger import Logger
from utils.helpers import load_yaml

def process_hjtc_excel(file_path: str) -> Optional[str]:
    """
    处理和舰科技Excel文件
    
    Args:
        file_path: 要处理的Excel文件路径
        
    Returns:
        Optional[str]: 处理后的文件路径，如果处理失败则返回None
    """
    logger = Logger().get_logger('hjtc_wip_handler')
    fields_config = load_yaml("config/wip_fields.yaml")
    try:
        header = fields_config["wip_fields"]["晶圆厂"]["和舰科技"]["header"]
        names = fields_config["wip_fields"]["晶圆厂"]["和舰科技"]["names"]
        name_values = list(names.values())
        data_format = fields_config["wip_fields"]["data_format"]
        
        # 读取CSV文件
        try:
            df = pd.read_csv(file_path, header=header, encoding='utf-8')
            
            # 检查DataFrame是否为空
            if df.empty:
                logger.error("CSV文件内容为空")
                return None
                
            # 检查是否包含所需的列
            missing_columns = set(name_values) - set(df.columns)
            if missing_columns:
                logger.error(f"CSV文件缺少必要的列: {missing_columns}")
                return None
                
        except pd.errors.EmptyDataError:
            logger.error("CSV文件为空")
            return None
            
        df = df[name_values]
        # 创建反向映射字典
        reverse_names = {v: k for k, v in names.items()}
        # 重命名列
        df.rename(columns=reverse_names, inplace=True)

        # 处理数值型字段，将非数值转换为NaN
        df["layerCount"] = pd.to_numeric(df["layerCount"], errors='coerce')
        df["currentPosition"] = pd.to_numeric(df["currentPosition"], errors='coerce')

        # 安全处理日期转换
        df["forecastDate"] = pd.to_datetime(df["forecastDate"], errors='coerce')
        # 只对非空日期进行偏移计算
        df["forecastDate"] = df["forecastDate"].apply(
            lambda x: (x + pd.Timedelta(days=7)).date() if pd.notna(x) else pd.NaT
        )

        df["supplier"] = "和舰科技"
        df["finished_at"] = pd.NaT

        # 处理STOCK状态
        stock_mask = df["status"].str.contains("STOCK", na=False)
        df.loc[stock_mask, ["layerCount", "remainLayer", "currentPosition"]] = pd.NaT

        # 安全计算remainLayer
        df["remainLayer"] = df.apply(
            lambda row: row["layerCount"] - row["currentPosition"]
            if pd.notna(row["layerCount"]) and pd.notna(row["currentPosition"])
            else None,
            axis=1
        )
        df = df[data_format]
        logger.debug(f"成功处理和舰科技Excel文件")
        return df
    
    except Exception as e:
        logger.error(f"处理和舰科技Excel文件失败: {e}")
        return None

