import pandas as pd
import os
from datetime import date, timedelta
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.interval import IntervalTrigger

from app.utils.logger import get_logger
from app.modules.dataBaseService.dataBaseService import DatabaseSession
from app.modules.dataBaseService.dal.hisemi_analyze import HisemiAnalyzeDAL

class HisemiWipAnalyzeService:
    def __init__(self):
        self.scheduler = None
        self.job = None
        self.logger = get_logger(__name__)
        self.excel_folder = r'downloads\processed\封装进度表\池州华宇'
        self.hisemi_analyze_dal = HisemiAnalyzeDAL()

    def get_latest_date(self):
        """获取数据库中最新的日期"""
        with DatabaseSession() as session:
            data_base_last_date = HisemiAnalyzeDAL().get_last_date(session)
            return data_base_last_date

    def validate_excel_file(self,database_last_date):
        """验证2个Excel文件是否存在"""
        next_day = database_last_date + timedelta(days=1)
        next_2_day = database_last_date + timedelta(days=2)
        file_name_next_day = os.path.join(self.excel_folder,f'苏州华芯微电子股份有限公司的封装产品进展表{next_day}.xlsx')
        file_name_next_2_day = os.path.join(self.excel_folder,f'苏州华芯微电子股份有限公司的封装产品进展表{next_2_day}.xlsx')
        if os.path.exists(file_name_next_day) and os.path.exists(file_name_next_2_day):
            return file_name_next_day, file_name_next_2_day
        return None, None

    def get_next_day_data(self,database_last_date):
        """获取下一天的数据"""
        file_name_next_day, file_name_next_2_day = self.validate_excel_file(database_last_date)
        if file_name_next_day is None or file_name_next_2_day is None:
            self.logger.warning(f"缺少{database_last_date + timedelta(days=1)}或{database_last_date + timedelta(days=2)}的进度表")
            return None
        return file_name_next_day, file_name_next_2_day

    def batch_upload_database(self):
        """批量上传数据库"""
        database_last_date = self.get_latest_date()
        all_data = []  # 用于存储所有要上传的数据
        
        while database_last_date != (date.today()-timedelta(days=1)):
            # 获取下一天的数据
            next_files = self.get_next_day_data(database_last_date)
            if next_files is None:
                break
                
            file_name_next_day, file_name_next_2_day = next_files
            
            try:
                # 读取两天的Excel文件
                df1 = pd.read_excel(file_name_next_day, sheet_name="Sheet1")
                df2 = pd.read_excel(file_name_next_2_day, sheet_name="Sheet1") 
                
                # 获取工序列并找到关键列索引
                list_gongxu = list(df1.columns)
                yanmo_index = list_gongxu.index("研磨(Grinding)")
                zhuangpian1_index = list_gongxu.index("装片1(DB1)") + 1
                
                # 计算装片总数
                df1_1 = df1.copy()
                df2_1 = df2.copy()
                df1_1["装片总数"] = df1.iloc[:, yanmo_index:zhuangpian1_index].sum(axis=1).astype("int64")
                df2_1["装片总数"] = df2.iloc[:, yanmo_index:zhuangpian1_index].sum(axis=1).astype("int64")
                
                # 提取需要的列
                df1_1 = df1_1[['工单号(Run card No)', '封装形式(Package)', '装片总数']]
                df2_1 = df2_1[['工单号(Run card No)', '封装形式(Package)', '装片总数']]
                
                # 合并数据并计算装片量
                df_m1 = df1_1.merge(df2_1, on=["工单号(Run card No)", "封装形式(Package)"], how="left")
                df_m1.fillna(0, inplace=True)
                df_m1["装片量"] = (df_m1["装片总数_x"] - df_m1["装片总数_y"]).astype("int")
                
                # 按封装形式分组统计
                df_g = df_m1[["封装形式(Package)", "装片量"]].groupby(by='封装形式(Package)').sum("装片量")
                
                # 准备插入数据库的数据
                insert_data = {
                    'Date': database_last_date + timedelta(days=1),
                    'SOP8_12R': int(df_g.loc['SOP8(12R)'].装片量 if 'SOP8(12R)' in df_g.index else 0),
                    'SOP8': int(df_g.loc['SOP8'].装片量 if 'SOP8' in df_g.index else 0),
                    'DFN8': int(df_g.loc['DFN8L(2X2X0.5-P0.5)'].装片量 if 'DFN8L(2X2X0.5-P0.5)' in df_g.index else 0),
                    'SOP16_12R': int(df_g.loc['SOP16(12R)'].装片量 if 'SOP16(12R)' in df_g.index else 0),
                    'SOP16': int(df_g.loc['SOP16'].装片量 if 'SOP16' in df_g.index else 0),
                    'SOP14_12R': int(df_g.loc['SOP14(12R)'].装片量 if 'SOP14(12R)' in df_g.index else 0),
                    'SOP14': int(df_g.loc['SOP14'].装片量 if 'SOP14' in df_g.index else 0),
                    'TSSOP20L': int(df_g.loc['TSSOP20L'].装片量 if 'TSSOP20L' in df_g.index else 0),
                    'SOT26_14R': int(df_g.loc['SOT26(14R)'].装片量 if 'SOT26(14R)' in df_g.index else 0),
                    'SOT25_20R': int(df_g.loc['SOT25(20R)'].装片量 if 'SOT25(20R)' in df_g.index else 0),
                    'SOT25_14R': int(df_g.loc['SOT25(14R)'].装片量 if 'SOT25(14R)' in df_g.index else 0),
                    'SSOP24': int(df_g.loc['SSOP24'].装片量 if 'SSOP24' in df_g.index else 0),
                    'ESSOP10': int(df_g.loc['ESSOP10'].装片量 if 'ESSOP10' in df_g.index else 0),
                    'QFN20': int(df_g.loc['QFN20L(3X3X0.5-P0.4)'].装片量 if 'QFN20L(3X3X0.5-P0.4)' in df_g.index else 0),
                    'LQFP32': int(df_g.loc['LQFP32L(7X7)'].装片量 if 'LQFP32L(7X7)' in df_g.index else 0)
                }
                
                all_data.append(insert_data)
                self.logger.info(f"成功处理{database_last_date + timedelta(days=1)}的数据")
                
                database_last_date = database_last_date + timedelta(days=1)
                
            except Exception as e:
                self.logger.error(f"处理数据失败: {str(e)}")
                break
        
        # 批量插入数据
        if all_data:
            try:
                with DatabaseSession() as session:
                    self.hisemi_analyze_dal.batch_update_hisemi_analyze(session, all_data)
                    session.commit()
                self.logger.info(f"成功批量插入{len(all_data)}条数据")
            except Exception as e:
                self.logger.error(f"批量插入数据失败: {str(e)}")
                raise
    
    def start(self, hour: int = 0, minute: int = 0):
        """
        启动服务
        Args:
            hour: 运行的小时 (0-23)
            minute: 运行的分钟 (0-59)
        """
        if not 0 <= hour <= 23:
            raise ValueError("小时必须在0-23之间")
        if not 0 <= minute <= 59:
            raise ValueError("分钟必须在0-59之间")
            
        self.scheduler = BackgroundScheduler()
        self.scheduler.add_job(
            self.batch_upload_database,
            trigger='cron',
            hour=hour,
            minute=minute
        )
        self.scheduler.start()
        self.logger.info(f"已设置定时任务，将在每天 {hour:02d}:{minute:02d} 运行")

    def stop(self):
        """停止服务"""
        if self.scheduler:
            self.scheduler.shutdown()
            self.logger.info("服务已停止")
    
    def merge_dataframes(self, df_raw: pd.DataFrame, df_mapping: pd.DataFrame) -> pd.DataFrame:
        """
        将两个数据框按照customerSoCode和stepName进行映射
        Args:
            df_raw: 原始数据框，包含所有列名
            df_mapping: 映射数据框，包含customerSoCode、stepName和currentqty
        Returns:
            处理后的数据框
        """
        # 创建一个新的数据框，复制原始数据框的结构
        result_df = df_raw.copy()
        
        # 遍历映射数据框的每一行
        for _, row in df_mapping.iterrows():
            customer_so = row['customerSoCode']
            step_name = row['stepName']
            current_qty = row['currentqty']
            
            # 如果stepName在原始数据框的列中
            if step_name in result_df.columns:
                # 找到对应的customerSoCode行，并更新对应的列值
                mask = result_df['customerSoCode'] == customer_so
                if mask.any():
                    result_df.loc[mask, step_name] = current_qty
        
        return result_df
    
    

