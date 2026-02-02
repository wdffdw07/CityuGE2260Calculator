"""
主程序 - "时光机"控制器
基于事件溯源的订单驱动回测系统
"""
import sys
from pathlib import Path
from datetime import datetime, timedelta, date
import backtrader as bt
import yfinance as yf

# 添加项目路径
sys.path.insert(0, str(Path(__file__).parent))

from src.storage import DatabaseManager
from src.parser import ExcelParser
from src.strategy import MultiBatchOrderStrategy
from src.analyse import PortfolioPlotter


# ========== 全局配置 ==========
INITIAL_CASH = 100000.0  # 初始资金 100,000 HKD
COMMISSION_RATE = 0.001  # 佣金率 0.1%
DB_PATH = 'history/trading.db'


class TradingEngine:
    """交易引擎 - 核心时光机"""
    
    def __init__(self):
        """初始化引擎"""
        self.db = DatabaseManager(DB_PATH)
        self.parser = ExcelParser()
        self.plotter = PortfolioPlotter()
        self.cerebro = None
        self.results = None
    
    def run(self):
        """主运行流程"""
        print("\n" + "=" * 80)
        print("📈 2260 订单驱动回测系统 - 事件溯源版")
        print("=" * 80)
        
        # 显示菜单
        print("\n📋 操作模式:")
        print("  [1] 执行新订单（增量模式）")
        print("  [2] 查看现有组合")
        print("  [3] 退出系统")
        
        choice = input("\n请选择操作 (1/2/3): ").strip()
        
        if choice == '1':
            self.execute_new_orders()
        elif choice == '2':
            self.view_portfolios()
        elif choice == '3':
            print("\n✓ 退出系统")
            return
        else:
            print("\n✗ 无效选项")
    
    def execute_new_orders(self):
        """执行新订单流程"""
        print("\n" + "=" * 80)
        print("📂 步骤 1: 解析订单文件")
        print("=" * 80)
        
        # 输入订单日期
        order_date_str = input("\n请输入订单日期 (格式: YYYYMMDD): ").strip()
        try:
            order_date = datetime.strptime(order_date_str, '%Y%m%d').date()
        except ValueError:
            print("✗ 日期格式错误")
            return
        
        # 查找订单文件
        order_folder = Path('order') / order_date_str
        if not order_folder.exists():
            print(f"✗ 找不到订单文件夹: {order_folder}")
            return
        
        try:
            order_file = self.parser.find_order_file(order_folder)
            print(f"✓ 找到订单文件: {order_file}")
        except FileNotFoundError as e:
            print(f"✗ {e}")
            return
        
        # 解析订单
        try:
            orders, execution_date = self.parser.parse_order_file(order_file)
            print(f"✓ 解析出 {len(orders)} 个有效订单")
            print(f"✓ 执行日期: {execution_date.strftime('%Y-%m-%d %A')}")
            
            print(f"\n📋 订单摘要:")
            for i, order in enumerate(orders, 1):
                print(f"  {i}. {order['action']:<5} {order['ticker']:<10} x {order['quantity']:<6.0f}")
        except Exception as e:
            print(f"✗ 解析订单失败: {e}")
            return
        
        # 输入组合名称
        portfolio_name = input("\n请输入组合名称 (新建或追加): ").strip()
        if not portfolio_name:
            print("✗ 组合名称不能为空")
            return
        
        # ========== 步骤 2: 保存订单到数据库 ==========
        print("\n" + "=" * 80)
        print("💾 步骤 2: 保存订单到数据库")
        print("=" * 80)
        
        # 执行日期是解析器返回的
        exec_date = execution_date.date() if isinstance(execution_date, datetime) else execution_date
        saved_count = self.db.save_orders(portfolio_name, order_date, exec_date, orders)
        if saved_count == 0:
            print("订单已存在，将使用现有记录继续")
        
        # ========== 步骤 3: 加载全部历史订单 ==========
        print("\n" + "=" * 80)
        print("📚 步骤 3: 加载历史订单（时光机启动）")
        print("=" * 80)
        
        all_orders = self.db.get_all_orders(portfolio_name)
        if not all_orders:
            print("✗ 没有历史订单")
            return
        
        summary = self.db.get_portfolio_summary(portfolio_name)
        print(f"✓ 组合: {portfolio_name}")
        print(f"  - 总订单数: {summary['total_orders']}")
        print(f"  - 首次交易: {summary['first_date']}")
        print(f"  - 最新交易: {summary['last_date']}")
        print(f"  - 涉及股票: {len(summary['tickers'])} 个")
        print(f"  - 交易批次: {len(summary['order_dates'])} 天")
        
        # ========== 步骤 4: 获取市场数据 ==========
        print("\n" + "=" * 80)
        print("📊 步骤 4: 获取市场数据")
        print("=" * 80)
        
        # 收集所有股票代码
        all_tickers = list(summary['tickers'])
        print(f"\n需要获取 {len(all_tickers)} 个股票的数据...")
        
        # 确定时间范围
        # 数据获取：从第一个订单日期前5天开始（确保数据充足）
        data_start_date = summary['first_date'] - timedelta(days=5)
        
        # 回测起始：从第一个执行日期前一天开始（避免图表显示无意义的初始日期）
        backtest_start_date = summary['first_execution_date'] - timedelta(days=1)
        
        # end_date需要确保在最后执行日期之后至少5个自然日（保证有2-3个交易日）
        last_order_date = summary['last_date']
        min_end_date = last_order_date + timedelta(days=10)
        today = datetime.now().date()
        end_date = max(min_end_date, today + timedelta(days=3))
        
        print(f"  数据范围: {data_start_date} → {end_date}")
        print(f"  回测范围: {backtest_start_date} → {end_date}")
        print(f"  (首次执行: {summary['first_execution_date']})")
        
        # 获取数据
        market_data = self.fetch_market_data(all_tickers, data_start_date, end_date)
        if not market_data:
            print("✗ 未能获取市场数据")
            return
        
        # ========== 步骤 5: 运行回测（时光机回放）==========
        print("\n" + "=" * 80)
        print("⚙ 步骤 5: 执行完整回测（事件重放）")
        print("=" * 80)
        
        final_value, positions = self.run_backtest(market_data, all_orders, backtest_start_date, end_date)
        
        # ========== 步骤 6: 显示结果 ==========
        self.display_results(final_value, positions, portfolio_name)
        
        # ========== 步骤 7: 可视化 ==========
        plot_choice = input("\n是否绘制组合演进图? (y/n): ").strip().lower()
        if plot_choice == 'y':
            self.plot_results(portfolio_name)
    
    def fetch_market_data(self, tickers: list, start_date: date, end_date: date) -> dict:
        """
        获取市场数据
        
        Returns:
            {ticker: DataFrame}
        """
        market_data = {}
        
        for ticker in tickers:
            try:
                print(f"  → 获取 {ticker}... ", end='', flush=True)
                
                data = yf.download(
                    ticker,
                    start=start_date.strftime('%Y-%m-%d'),
                    end=(end_date + timedelta(days=1)).strftime('%Y-%m-%d'),
                    progress=False
                )
                
                if data.empty:
                    print("✗ 无数据")
                    continue
                
                # 处理MultiIndex列名
                if isinstance(data.columns, pd.MultiIndex):
                    data.columns = [col[0] if isinstance(col, tuple) else col for col in data.columns]
                
                # 重置索引，确保date列
                data.reset_index(inplace=True)
                
                # 标准化列名
                data.columns = [col.lower() for col in data.columns]
                
                market_data[ticker] = data
                print(f"✓ ({len(data)} 条)")
                
            except Exception as e:
                print(f"✗ 失败: {e}")
                continue
        
        print(f"\n✓ 成功获取 {len(market_data)}/{len(tickers)} 个股票数据")
        return market_data
    
    def run_backtest(self, market_data: dict, orders: list, start_date: date, end_date: date):
        """
        运行Backtrader回测
        
        Returns:
            (最终价值, 持仓字典)
        """
        # 初始化Cerebro
        self.cerebro = bt.Cerebro()
        
        # 设置初始资金和佣金
        self.cerebro.broker.setcash(INITIAL_CASH)
        self.cerebro.broker.setcommission(commission=COMMISSION_RATE)
        
        print(f"\n⚙ 引擎配置:")
        print(f"  - 初始资金: ${INITIAL_CASH:,.2f}")
        print(f"  - 佣金率: {COMMISSION_RATE*100:.2f}%")
        print(f"  - Cheat-On-Open: 开启")
        
        # 添加数据源
        print(f"\n📈 加载数据源:")
        for ticker, df in market_data.items():
            data_feed = bt.feeds.PandasData(
                dataname=df,
                datetime='date',
                open='open',
                high='high',
                low='low',
                close='close',
                volume='volume',
                openinterest=-1,
                fromdate=datetime.combine(start_date, datetime.min.time()),
                todate=datetime.combine(end_date, datetime.max.time())
            )
            data_feed._name = ticker
            self.cerebro.adddata(data_feed, name=ticker)
            print(f"  ✓ {ticker}: {len(df)} 条数据")
        
        # 添加策略
        self.cerebro.addstrategy(
            MultiBatchOrderStrategy,
            history_orders=orders,
            verbose=True
        )
        
        # 开启Cheat-On-Open
        self.cerebro.broker.set_coc(True)
        
        # 运行回测
        print(f"\n🚀 开始回测...")
        print(f"初始资金: ${self.cerebro.broker.getvalue():,.2f}\n")
        
        self.results = self.cerebro.run()
        
        # 获取最终结果
        final_value = self.cerebro.broker.getvalue()
        profit = final_value - INITIAL_CASH
        return_rate = (profit / INITIAL_CASH) * 100
        
        print(f"\n" + "=" * 60)
        print(f"📊 回测结果:")
        print(f"  - 最终资金: ${final_value:,.2f}")
        print(f"  - 总收益: ${profit:,.2f}")
        print(f"  - 收益率: {return_rate:.2f}%")
        print("=" * 60)
        
        # 获取持仓
        positions = self.get_positions()
        
        return final_value, positions
    
    def get_positions(self) -> dict:
        """获取当前持仓"""
        if not self.results:
            return {}
        
        strategy = self.results[0]
        positions = {}
        
        for data in strategy.datas:
            position = strategy.getposition(data)
            if position.size > 0:
                ticker = data._name
                positions[ticker] = {
                    'quantity': position.size,
                    'cost_price': position.price,
                    'current_price': data.close[0],
                    'value': position.size * data.close[0],
                    'profit': (data.close[0] - position.price) * position.size
                }
        
        return positions
    
    def display_results(self, final_value: float, positions: dict, portfolio_name: str):
        """显示回测结果"""
        print(f"\n💼 当前持仓 ({len(positions)} 个):")
        print("=" * 90)
        print(f"{'代码':<12} {'数量':>8} {'成本价':>12} {'现价':>12} {'市值':>15} {'盈亏':>15}")
        print("-" * 90)
        
        total_value = 0
        total_profit = 0
        
        for ticker, pos in positions.items():
            print(
                f"{ticker:<12} "
                f"{pos['quantity']:>8.0f} "
                f"${pos['cost_price']:>11.4f} "
                f"${pos['current_price']:>11.4f} "
                f"${pos['value']:>14,.2f} "
                f"${pos['profit']:>14,.2f}"
            )
            total_value += pos['value']
            total_profit += pos['profit']
        
        print("-" * 90)
        print(f"{'合计':<12} {'':<8} {'':<12} {'':<12} ${total_value:>14,.2f} ${total_profit:>14,.2f}")
        print("=" * 90)
        
        cash = final_value - total_value
        print(f"\n账户摘要:")
        print(f"  持仓市值: ${total_value:,.2f}")
        print(f"  现金余额: ${cash:,.2f}")
        print(f"  账户总值: ${final_value:,.2f}")
    
    def plot_results(self, portfolio_name: str):
        """绘制结果图表"""
        if not self.results:
            return
        
        strategy = self.results[0]
        dates = strategy.daily_dates
        values = strategy.daily_values
        stock_values = strategy.stock_values  # 获取每个股票的价值变化
        
        if dates and values:
            self.plotter.plot_portfolio_evolution(dates, values, INITIAL_CASH, portfolio_name, stock_values)
    
    def view_portfolios(self):
        """查看现有组合"""
        print("\n" + "=" * 80)
        print("📊 现有组合列表")
        print("=" * 80)
        
        portfolios = self.db.list_portfolios()
        
        if not portfolios:
            print("\n✗ 暂无组合")
            return
        
        print(f"\n共 {len(portfolios)} 个组合:\n")
        
        for i, name in enumerate(portfolios, 1):
            summary = self.db.get_portfolio_summary(name)
            print(f"{i}. {name}")
            print(f"   - 订单数: {summary['total_orders']}")
            print(f"   - 时间跨度: {summary['first_date']} → {summary['last_date']}")
            print(f"   - 股票数: {len(summary['tickers'])}")
            print(f"   - 交易日: {len(summary['order_dates'])} 天")
            print()


def main():
    """主入口"""
    try:
        engine = TradingEngine()
        engine.run()
    except KeyboardInterrupt:
        print("\n\n✓ 用户中断")
    except Exception as e:
        print(f"\n✗ 程序错误: {e}")
        import traceback
        traceback.print_exc()


if __name__ == '__main__':
    # 兼容pandas导入
    import pandas as pd
    main()
