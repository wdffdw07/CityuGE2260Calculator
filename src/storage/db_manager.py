"""
数据库管理器 - 负责订单记录的增删查
"""
from typing import List, Dict
from datetime import date
from .models import OrderRecord, init_database


class DatabaseManager:
    """订单历史管理器"""
    
    def __init__(self, db_path='history/trading.db'):
        """初始化数据库连接"""
        self.engine, self.Session = init_database(db_path)
    
    def save_orders(self, portfolio_name: str, order_date: date, execution_date: date, orders: List[Dict]) -> int:
        """
        保存新订单到数据库（追加模式）
        
        Args:
            portfolio_name: 组合名称
            order_date: 订单日期
            execution_date: 执行日期
            orders: 订单列表 [{'ticker': xxx, 'action': xxx, 'quantity': xxx}]
        
        Returns:
            成功保存的订单数量
        """
        session = self.Session()
        saved_count = 0
        
        try:
            # 检查是否已存在该日期的订单
            existing = session.query(OrderRecord).filter_by(
                portfolio_name=portfolio_name,
                order_date=order_date
            ).count()
            
            if existing > 0:
                print(f"⚠ 警告: {order_date} 的订单已存在，跳过保存")
                return 0
            
            # 追加新订单
            for order in orders:
                if order['action'].lower() == 'hold':
                    continue
                
                record = OrderRecord(
                    portfolio_name=portfolio_name,
                    order_date=order_date,
                    execution_date=execution_date,
                    ticker=order['ticker'],
                    action=order['action'].capitalize(),
                    quantity=order['quantity'],
                    asset_type=order.get('asset_type', 'Stock')
                )
                session.add(record)
                saved_count += 1
            
            session.commit()
            print(f"✓ 成功保存 {saved_count} 条订单记录")
            return saved_count
            
        except Exception as e:
            session.rollback()
            print(f"✗ 保存订单失败: {e}")
            raise
        finally:
            session.close()
    
    def get_all_orders(self, portfolio_name: str) -> List[OrderRecord]:
        """
        获取组合的所有历史订单（按时间排序）
        
        Args:
            portfolio_name: 组合名称
        
        Returns:
            订单记录列表
        """
        session = self.Session()
        try:
            orders = session.query(OrderRecord).filter_by(
                portfolio_name=portfolio_name
            ).order_by(OrderRecord.order_date, OrderRecord.id).all()
            
            # 解除session绑定
            for order in orders:
                session.expunge(order)
            
            return orders
        finally:
            session.close()
    
    def get_order_dates(self, portfolio_name: str) -> List[date]:
        """
        获取组合的所有订单日期
        
        Args:
            portfolio_name: 组合名称
        
        Returns:
            日期列表（去重并排序）
        """
        session = self.Session()
        try:
            dates = session.query(OrderRecord.order_date).filter_by(
                portfolio_name=portfolio_name
            ).distinct().order_by(OrderRecord.order_date).all()
            
            return [d[0] for d in dates]
        finally:
            session.close()
    
    def list_portfolios(self) -> List[str]:
        """列出所有组合名称"""
        session = self.Session()
        try:
            names = session.query(OrderRecord.portfolio_name).distinct().all()
            return [n[0] for n in names]
        finally:
            session.close()
    
    def get_portfolio_summary(self, portfolio_name: str) -> Dict:
        """
        获取组合摘要信息
        
        Returns:
            {'total_orders': xxx, 'first_date': xxx, 'last_date': xxx, 'tickers': [], 'first_execution_date': xxx}
        """
        session = self.Session()
        try:
            orders = session.query(OrderRecord).filter_by(
                portfolio_name=portfolio_name
            ).order_by(OrderRecord.order_date).all()
            
            if not orders:
                return None
            
            tickers = list(set([o.ticker for o in orders]))
            
            # 获取最早的执行日期
            execution_dates = [o.execution_date for o in orders]
            first_execution_date = min(execution_dates)
            
            return {
                'total_orders': len(orders),
                'first_date': orders[0].order_date,
                'last_date': orders[-1].order_date,
                'first_execution_date': first_execution_date,  # 第一个执行日期
                'tickers': tickers,
                'order_dates': list(set([o.order_date for o in orders]))
            }
        finally:
            session.close()
