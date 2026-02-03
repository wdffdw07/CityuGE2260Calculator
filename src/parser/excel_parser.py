"""
Excel订单文件解析器
支持 .xlsx 和 .csv 格式
"""
import pandas as pd
from pathlib import Path
from typing import List, Dict, Tuple
from datetime import datetime, timedelta
import re


class ExcelParser:
    """订单文件解析器"""
    
    @staticmethod
    def extract_ticker(asset_name: str) -> str:
        """
        从资产名称中提取股票代码
        
        Examples:
            "盈富基金" -> "2800.HK"
            "Tracker Fund of Hong Kong" -> "2800.HK"
            "中国飞鹤" -> "3033.HK"
        """
        # 常见股票名称映射
        NAME_MAPPING = {
            '盈富': '2800.HK',
            'tracker fund': '2800.HK',
            '中国飞鹤': '3033.HK',
            '飞鹤': '3033.HK',
            '博时': '2819.HK',
            '证券保险': '2819.HK',
            '领展': '0823.HK',
            '瑞声': '3199.HK',
            '阿里': '9988.HK',
            '阿里巴巴': '9988.HK',
            'alibaba': '9988.HK',
        }
        
        # 转小写便于匹配
        name_lower = asset_name.lower()
        
        # 尝试映射匹配
        for key, ticker in NAME_MAPPING.items():
            if key in name_lower:
                return ticker
        
        # 尝试从文本中提取数字代码
        code_match = re.search(r'(\d{4})', asset_name)
        if code_match:
            code = code_match.group(1)
            return f"{code}.HK"
        
        # 如果已经是代码格式
        if re.match(r'^\d{4}\.HK$', asset_name):
            return asset_name
        
        raise ValueError(f"无法识别资产名称: {asset_name}")
    
    @staticmethod
    def adjust_to_trading_day(date_obj: datetime) -> datetime:
        """
        将日期调整到交易日
        周六 -> 下周一
        周日 -> 下周一
        """
        weekday = date_obj.weekday()
        
        if weekday == 5:  # 周六
            return date_obj + timedelta(days=2)
        elif weekday == 6:  # 周日
            return date_obj + timedelta(days=1)
        else:
            return date_obj
    
    def parse_order_file(self, file_path: Path) -> Tuple[List[Dict], datetime]:
        """
        解析订单文件
        
        Args:
            file_path: 订单文件路径
        
        Returns:
            (订单列表, 执行日期)
            订单格式: [{'ticker': xxx, 'action': xxx, 'quantity': xxx, 'asset_type': xxx}]
        """
        # 从文件夹名称提取日期
        date_str = file_path.parent.name
        try:
            order_date = datetime.strptime(date_str, '%Y%m%d')
        except ValueError:
            raise ValueError(f"文件夹名称格式错误，应为 YYYYMMDD: {date_str}")
        
        # 执行日期 = 订单日期的下一个交易日
        execution_date = self.adjust_to_trading_day(order_date + timedelta(days=1))
        
        # 读取文件
        if file_path.suffix == '.xlsx':
            df = pd.read_excel(file_path)
        elif file_path.suffix == '.csv':
            df = pd.read_csv(file_path)
        else:
            raise ValueError(f"不支持的文件格式: {file_path.suffix}")
        
        # 解析订单
        orders = []
        
        for _, row in df.iterrows():
            try:
                # 提取字段（支持多种列名格式）
                asset_name = str(row.get('Asset Name', row.get('资产名称', '')))
                
                # Action列可能有多种格式
                action = None
                for col in df.columns:
                    if 'action' in col.lower():
                        action = str(row.get(col, '')).strip().lower()
                        break
                if not action:
                    action = str(row.get('Action', row.get('操作', ''))).strip().lower()
                
                quantity = float(row.get('Quantity', row.get('数量', 0)))
                
                # Asset Type列可能有多种格式
                asset_type = 'Stock'
                for col in df.columns:
                    if 'asset type' in col.lower():
                        asset_type = str(row.get(col, 'Stock'))
                        break
                if asset_type == 'Stock':
                    asset_type = str(row.get('Asset Type', row.get('资产类型', 'Stock')))
                
                # 跳过无效行
                if pd.isna(asset_name) or not asset_name or action == 'hold':
                    continue
                
                # 提取代码
                ticker = self.extract_ticker(asset_name)
                
                # 标准化action
                if action in ['buy', '买入', 'b']:
                    action = 'Buy'
                elif action in ['sell', '卖出', 's']:
                    action = 'Sell'
                else:
                    continue
                
                orders.append({
                    'ticker': ticker,
                    'action': action,
                    'quantity': quantity,
                    'asset_type': asset_type
                })
                
            except Exception as e:
                print(f"⚠ 解析行时出错，跳过: {e}")
                continue
        
        return orders, execution_date
    
    def find_order_files(self, order_folder: Path) -> List[Path]:
        """
        在订单文件夹中查找所有订单文件
        
        Args:
            order_folder: 订单文件夹路径（如 order/20260125）
        
        Returns:
            订单文件路径列表
        """
        # 查找所有xlsx和csv文件
        xlsx_files = list(order_folder.glob('*.xlsx'))
        csv_files = list(order_folder.glob('*.csv'))
        
        all_files = xlsx_files + csv_files
        
        if not all_files:
            raise FileNotFoundError(f"在 {order_folder} 中找不到订单文件")
        
        return sorted(all_files)  # 按文件名排序
    
    def find_order_file(self, order_folder: Path) -> Path:
        """
        在订单文件夹中查找订单文件（兼容旧版本，返回第一个文件）
        
        Args:
            order_folder: 订单文件夹路径（如 order/20260125）
        
        Returns:
            订单文件路径
        """
        files = self.find_order_files(order_folder)
        return files[0]

