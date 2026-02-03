"""
多批次订单策略 - 支持历史订单重放
基于事件溯源模式
"""
import backtrader as bt
from datetime import datetime, date, timedelta
from typing import List, Dict
from collections import defaultdict


class MultiBatchOrderStrategy(bt.Strategy):
    """
    多批次订单执行策略
    按时间顺序自动执行所有历史订单
    """
    
    params = (
        ('history_orders', []),  # 历史订单列表
        ('verbose', True),  # 是否显示详细日志
    )
    
    def __init__(self):
        """初始化策略"""
        self.data_map = {}  # ticker -> data映射
        self.daily_values = []  # 每日账户价值
        self.daily_dates = []  # 日期列表
        self.executed_count = 0  # 已执行订单数
        self.pending_orders = []  # 待执行订单队列
        
        # 每个股票的每日持仓价值
        self.stock_values = defaultdict(list)  # ticker -> [values]
        
        # 按执行日期分组订单
        # 注意：在Cheat-On-Open模式下，需要提前1天下单才能在目标日开盘成交
        # 所以我们按execution_date - 1天来分组
        self.orders_by_date = defaultdict(list)
        self.all_order_dates = []  # 所有订单日期（用于检查）
        
        for order in self.params.history_orders:
            # 使用execution_date进行分组
            exec_date = order.execution_date if hasattr(order, 'execution_date') else order.get('execution_date', order.get('order_date'))
            # 确保是date对象
            if isinstance(exec_date, datetime):
                exec_date = exec_date.date()
            
            # 关键修改：提前1天下单，这样在execution_date当天开盘成交
            order_date = exec_date - timedelta(days=1)
            self.orders_by_date[order_date].append(order)
            self.all_order_dates.append(order_date)
        
        # 建立数据映射
        for data in self.datas:
            if hasattr(data, '_name'):
                self.data_map[data._name] = data
        
        if self.params.verbose:
            print(f"\n📋 策略初始化:")
            print(f"  - 总订单数: {len(self.params.history_orders)}")
            print(f"  - 执行批次: {len(self.orders_by_date)} 天")
            print(f"  - Cheat-On-Open: 订单将在目标日前1天挂单，目标日开盘成交")
            print(f"  - 数据源: {len(self.data_map)} 个股票")
            
            # 显示执行计划
            sorted_dates = sorted(self.orders_by_date.keys())
            print(f"\n📅 执行计划 (Cheat-On-Open: 提前1天下单):")
            for i, date_key in enumerate(sorted_dates[:5]):
                count = len(self.orders_by_date[date_key])
                # 显示实际成交日期（下单日+1天）
                actual_exec_date = date_key + timedelta(days=1)
                print(f"  {i+1}. {date_key} 下单 → {actual_exec_date} 开盘成交: {count} 条订单")
            if len(sorted_dates) > 5:
                print(f"  ... 还有 {len(sorted_dates) - 5} 个批次")
    
    def log(self, txt, dt=None):
        """日志函数"""
        if not self.params.verbose:
            return
        
        if dt is None:
            try:
                dt = self.datas[0].datetime.date(0)
            except:
                dt = date.today()
        print(f"[{dt}] {txt}")
    
    def notify_order(self, order):
        """订单状态通知"""
        if order.status in [order.Completed]:
            if order.isbuy():
                self.log(
                    f'✓ 买入: {order.data._name} | '
                    f'数量: {order.executed.size:.0f} | '
                    f'价格: ${order.executed.price:.4f} | '
                    f'成本: ${order.executed.value:.2f}'
                )
            elif order.issell():
                self.log(
                    f'✓ 卖出: {order.data._name} | '
                    f'数量: {order.executed.size:.0f} | '
                    f'价格: ${order.executed.price:.4f} | '
                    f'金额: ${order.executed.value:.2f}'
                )
            self.executed_count += 1
        
        elif order.status in [order.Canceled, order.Margin, order.Rejected]:
            self.log(f'✗ 订单失败: {order.data._name} - {order.getstatusname()}')
    
    def notify_trade(self, trade):
        """交易通知"""
        if trade.isclosed:
            self.log(
                f'💰 平仓: {trade.data._name} | '
                f'毛利: ${trade.pnl:.2f} | '
                f'净利: ${trade.pnlcomm:.2f}'
            )
    
    def next(self):
        """策略主逻辑 - 每个交易日调用"""
        current_date = self.datas[0].datetime.date(0)
        
        # 调试：显示所有数据源的当前日期
        if self.params.verbose and len(self.daily_dates) < 10:  # 增加显示天数便于调试
            self.log(f"📅 当前日期: {current_date}")
            for data in self.datas[:min(3, len(self.datas))]:  # 只显示前3个
                self.log(f"  {data._name}: {data.datetime.date(0)}")
        
        # 重要：在订单处理前记录每日数据
        # 这样记录的是订单执行前的状态（避免Cheat-On-Open预留position的影响）
        self.daily_dates.append(current_date)
        self.daily_values.append(self.broker.getvalue())
        
        # 记录每个股票的每日持仓价值
        for data in self.datas:
            ticker = data._name
            position = self.getposition(data)
            if position.size > 0:
                stock_value = position.size * data.close[0]
            else:
                stock_value = 0.0
            self.stock_values[ticker].append(stock_value)
            
            # 调试：显示持仓信息
            if self.params.verbose and len(self.daily_dates) <= 10:
                if position.size > 0:
                    self.log(f"   持仓记录 {ticker}: {position.size} @ ${data.close[0]:.2f} = ${stock_value:.2f}")
        
        # 检查是否有订单要在今天执行（精确匹配 - 订单日期是交易日）
        if current_date in self.orders_by_date:
            orders_today = self.orders_by_date[current_date]
            
            if self.params.verbose:
                self.log("=" * 60)
                self.log(f"执行 {len(orders_today)} 条订单（下单日匹配）")
                self.log("=" * 60)
            
            for order_info in orders_today:
                self.execute_single_order(order_info)
            
            # 标记为已处理
            del self.orders_by_date[current_date]
        
        # 关键修复：检查下一个交易日
        # 获取下一个交易日（如果存在）
        next_trading_day = None
        if len(self.datas) > 0:
            try:
                # 向前看1步，获取下一个交易日
                next_trading_day = self.datas[0].datetime.date(1)
            except:
                # 如果没有下一个交易日，说明回测即将结束
                pass
        
        # 如果有下一个交易日，检查是否有订单日期落在当前日期和下一个交易日之间
        if next_trading_day:
            pending_dates = sorted([d for d in self.orders_by_date.keys()])
            
            for order_date in pending_dates:
                # 订单日期在当前日期和下一个交易日之间（current < order_date < next）
                # 说明订单日期不是交易日，应该在今天下单，下个交易日成交
                if current_date < order_date < next_trading_day:
                    orders = self.orders_by_date[order_date]
                    
                    if self.params.verbose:
                        self.log("=" * 60)
                        self.log(f"⚠️  订单日期 {order_date} 不是交易日")
                        self.log(f"   交易日序列: {current_date} → [{order_date}空位] → {next_trading_day}")
                        self.log(f"   将在今天 ({current_date}) 下单")
                        self.log(f"   目标: {next_trading_day} 开盘成交")
                        self.log("=" * 60)
                    
                    for order_info in orders:
                        self.execute_single_order(order_info)
                    
                    # 标记为已处理
                    del self.orders_by_date[order_date]
                    break  # 一次只处理一个批次
    
    def execute_single_order(self, order_info):
        """执行单个订单"""
        # 兼容OrderRecord对象和字典
        if hasattr(order_info, 'ticker'):
            ticker = order_info.ticker
            action = order_info.action
            quantity = order_info.quantity
        else:
            ticker = order_info['ticker']
            action = order_info['action']
            quantity = order_info['quantity']
        
        # 获取对应的数据源
        data = self.data_map.get(ticker)
        if data is None:
            self.log(f"✗ 错误: 找不到 {ticker} 的数据")
            return
        
        # 获取当前持仓
        position = self.getposition(data)
        
        # 执行买入
        if action.lower() == 'buy':
            target_price = data.open[0]  # Cheat-On-Open: 使用开盘价
            self.log(f"→ 挂单买入: {ticker} x {quantity:.0f} @ ${target_price:.4f}")
            self.buy(data=data, size=quantity, exectype=bt.Order.Market)
        
        # 执行卖出
        elif action.lower() == 'sell':
            if position.size <= 0:
                self.log(f"✗ 警告: {ticker} 无持仓，无法卖出")
                return
            
            if position.size < quantity:
                self.log(f"⚠ 警告: {ticker} 持仓 {position.size:.0f} 不足，卖出全部")
                quantity = position.size
            
            target_price = data.open[0]
            self.log(f"→ 挂单卖出: {ticker} x {quantity:.0f} @ ${target_price:.4f}")
            self.sell(data=data, size=quantity, exectype=bt.Order.Market)
    
    def stop(self):
        """回测结束"""
        if self.params.verbose:
            self.log("=" * 60)
            self.log("回测结束")
            self.log(f"总计执行 {self.executed_count} 条订单")
            self.log(f"最终账户价值: ${self.broker.getvalue():.2f}")
            self.log("=" * 60)
