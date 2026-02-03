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
            order_files = self.parser.find_order_files(order_folder)
            
            # 如果有多个文件，让用户选择
            if len(order_files) > 1:
                print(f"\n找到 {len(order_files)} 个订单文件:")
                for i, file_path in enumerate(order_files, 1):
                    print(f"  [{i}] {file_path.name}")
                
                while True:
                    choice = input(f"\n请选择文件 (1-{len(order_files)}): ").strip()
                    try:
                        idx = int(choice) - 1
                        if 0 <= idx < len(order_files):
                            order_file = order_files[idx]
                            break
                        else:
                            print(f"✗ 请输入 1 到 {len(order_files)} 之间的数字")
                    except ValueError:
                        print("✗ 请输入有效的数字")
            else:
                order_file = order_files[0]
            
            print(f"✓ 使用订单文件: {order_file.name}")
            
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
        last_execution_date = summary['last_execution_date']  # 最后的执行日期
        min_end_date = last_order_date + timedelta(days=10)
        today = datetime.now().date()
        end_date = max(min_end_date, today + timedelta(days=1))  # 包含今天
        
        # 判断今天是否是周末
        weekday = today.weekday()
        is_weekend = weekday >= 5  # 5=周六, 6=周日
        
        # 获取最近的交易日（用于提示）
        if is_weekend:
            # 周六/周日 -> 上周五
            days_since_friday = weekday - 4
            last_trading_day = today - timedelta(days=days_since_friday)
            # 下周一
            next_trading_day = today + timedelta(days=(7 - weekday))
        else:
            last_trading_day = today
            next_trading_day = today
        
        print(f"  数据范围: {data_start_date} → {end_date}")
        print(f"  回测范围: {backtest_start_date} → {end_date}")
        print(f"  (首次执行: {summary['first_execution_date']})")
        print(f"  (最后执行: {last_execution_date})")
        print(f"  (今天: {today} {'【周末】' if is_weekend else ''})")
        
        # 检查最后执行日期是否在未来
        if last_execution_date > today:
            print(f"\n⚠️  执行日期在未来: {last_execution_date}")
            if is_weekend and last_execution_date == next_trading_day:
                print(f"   这是周末订单，将在下周一 ({next_trading_day}) 执行")
                print(f"   ❌ 股市还未开盘，暂无数据可用")
                print(f"   请在 {next_trading_day} 之后重新运行")
            else:
                print(f"   ❌ 执行日期还未到来，暂无数据可用")
                print(f"   请在 {last_execution_date} 之后重新运行")
            return
        
        # 周末提示
        if is_weekend:
            print(f"\n📅 今天是周末，股市休市")
            print(f"   最新可用数据: {last_trading_day} (上周五)")
        
        # 如果最后订单是今天，提醒用户
        if last_order_date == today:
            if is_weekend:
                print(f"\n⚠️  注意: 订单日期是今天（周末）")
                print(f"   订单将在下周一 ({next_trading_day}) 执行")
                print(f"   当前无法计算结果，请在下周一开盘后重新运行")
            else:
                print(f"\n⚠️  注意: 最后订单日期是今天 ({today})")
                print(f"   当天的市场数据可能还未更新（通常在收盘后1-2小时可用）")
                print(f"   如果数据未更新，建议稍后重新运行以获取完整结果")
        elif is_weekend and (today - last_order_date).days <= 2:
            # 订单是周五/周六
            print(f"\n📅 订单日期在本周末附近")
            print(f"   最新可用数据: {last_trading_day} (上周五)")
        
        # 获取数据
        market_data = self.fetch_market_data(all_tickers, data_start_date, end_date)
        if not market_data:
            print("✗ 未能获取市场数据")
            return
                # 检查关键日期的数据可用性
        print(f"\n🔍 数据可用性检查:")
        all_available_dates = set()
        for ticker, df in market_data.items():
            if 'date' in df.columns:
                dates = set(pd.to_datetime(df['date']).dt.date)
                all_available_dates.update(dates)
        
        if last_execution_date not in all_available_dates:
            print(f"   ❌ 执行日期 {last_execution_date} 的数据不可用")
            print(f"   可用数据范围: {min(all_available_dates)} → {max(all_available_dates)}")
            print(f"\n⚠️  无法执行回测：订单执行日期 ({last_execution_date}) 没有市场数据")
            
            if last_execution_date == today:
                print(f"   原因: 今天的数据通常在收盘后1-2小时才可用")
                print(f"   建议: 请在今天收盘后（约18:00后）重新运行")
            else:
                print(f"   建议: 等待数据更新后重新运行")
            return
        
        # 检查执行日期之后是否有数据（backtrader需要至少一个后续交易日来完成订单）
        sorted_dates = sorted(all_available_dates)
        execution_date_index = sorted_dates.index(last_execution_date) if last_execution_date in sorted_dates else -1
        
        if execution_date_index == -1:
            # 执行日期不在可用数据中
            print(f"   ❌ 关键问题：执行日期 {last_execution_date} 不在任何股票的交易数据中")
            print(f"   可用交易日: {', '.join(str(d) for d in sorted_dates[:10])}")
            
            # 检查是否是刚过去的日期（数据延迟）
            days_ago = (today - last_execution_date).days
            if days_ago == 1:
                print(f"\n   📌 {last_execution_date} 是昨天")
                print(f"   原因: Yahoo Finance的历史数据通常延迟1-2天更新")
                print(f"   昨天的数据可能今天晚些时候或明天才会出现在数据库中")
                print(f"\n   建议: 请明天（{today + timedelta(days=1)}）重新运行")
            elif days_ago == 0:
                print(f"\n   📌 {last_execution_date} 是今天")
                print(f"   原因: 当天数据通常在收盘后1-2小时可用")
                print(f"   建议: 请今晚18:00后或明天重新运行")
            elif 2 <= days_ago <= 5:
                print(f"\n   📌 {last_execution_date} 是{days_ago}天前")
                print(f"   可能原因: ")
                # 检查是否是周末
                weekday = last_execution_date.weekday()
                if weekday >= 5:
                    print(f"   - 这天是周末（{['周一','周二','周三','周四','周五','周六','周日'][weekday]}），非交易日")
                else:
                    print(f"   - 可能是公众假期（春节、中秋等）")
                    print(f"   - 或所有股票停牌")
            else:
                # 检查是否是假期
                weekday = last_execution_date.weekday()
                if weekday >= 5:
                    print(f"\n   {last_execution_date} 是周末，非交易日")
                else:
                    print(f"\n   {last_execution_date} 是工作日({['周一','周二','周三','周四','周五'][weekday]})，但可能是公众假期或所有股票停牌")
            
            # 找到最接近的交易日
            future_dates = [d for d in sorted_dates if d > last_execution_date]
            if future_dates:
                next_date = min(future_dates)
                print(f"\n   最近的可用交易日: {next_date}")
                print(f"\n💡 临时方案: 将订单日期改为 {(next_date - timedelta(days=1)).strftime('%Y%m%d')}，")
                print(f"              订单将在 {next_date} 执行")
            return
        
        has_next_day = execution_date_index < len(sorted_dates) - 1
        
        if not has_next_day:
            print(f"   ⚠️  执行日期 {last_execution_date} 是最后一个交易日")
            print(f"   可用数据: {sorted_dates[0]} → {sorted_dates[-1]} (共{len(sorted_dates)}个交易日)")
            print(f"\n❌ 无法完成订单结算：Backtrader需要执行日期之后至少一个交易日的数据")
            
            if last_execution_date == today:
                weekday = today.weekday()
                if weekday < 4:  # 周一到周四
                    next_trading_day = today + timedelta(days=1)
                    print(f"   订单将在今天 ({today}) 执行，但需要明天 ({next_trading_day}) 的数据才能结算")
                    print(f"   建议: 请在明天 ({next_trading_day}) 收盘后重新运行")
                else:  # 周五
                    next_trading_day = today + timedelta(days=3)  # 下周一
                    print(f"   订单将在今天 ({today}) 执行，但需要下周一 ({next_trading_day}) 的数据才能结算")
                    print(f"   建议: 请在下周一 ({next_trading_day}) 收盘后重新运行")
            else:
                print(f"   建议: 等待下一个交易日的数据更新后重新运行")
            return
        else:
            next_trading_day = sorted_dates[execution_date_index + 1]
            print(f"   ✓ 执行日期 {last_execution_date} 的数据可用")
            print(f"   ✓ 后续交易日 {next_trading_day} 的数据可用（用于订单结算）")
        
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
        today = datetime.now().date()
        
        for ticker in tickers:
            try:
                print(f"  → 获取 {ticker}... ", end='', flush=True)
                
                # 如果end_date是今天或未来，使用period='max'来获取最新数据
                if end_date >= today:
                    data = yf.download(
                        ticker,
                        start=start_date.strftime('%Y-%m-%d'),
                        end=None,  # 获取到最新
                        progress=False
                    )
                else:
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
                
                # 详细检查数据日期
                if 'date' in data.columns:
                    data_dates = pd.to_datetime(data['date']).dt.date
                    first_date = data_dates.min()
                    last_date = data_dates.max()
                    
                    # 显示所有日期（用于调试）
                    all_dates = sorted(data_dates.unique())
                    date_str = ', '.join(str(d) for d in all_dates)
                    
                    print(f"✓ ({len(data)} 条, {first_date} → {last_date})")
                    print(f"  详细日期: {date_str}")
                else:
                    print(f"✓ ({len(data)} 条)")
                
                market_data[ticker] = data
                
            except Exception as e:
                print(f"✗ 失败: {e}")
                continue
        
        if not market_data:
            print(f"\n✗ 未能获取任何市场数据")
            return market_data
        
        # 检查数据完整性
        print(f"\n✓ 成功获取 {len(market_data)}/{len(tickers)} 个股票数据")
        
        # 检查所有股票的最后数据日期
        last_dates = []
        for ticker, df in market_data.items():
            if 'date' in df.columns:
                last_date = pd.to_datetime(df['date']).dt.date.max()
                last_dates.append(last_date)
        
        if last_dates:
            earliest_last_date = min(last_dates)
            print(f"⚠️  最早的最后数据日期: {earliest_last_date}")
            if earliest_last_date < today:
                print(f"   所有股票的数据都只到 {earliest_last_date}，可能无法完整计算今日持仓")
        
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
        
        # 收集所有股票的日期范围，找到公共日期区间
        all_dates_by_ticker = {}
        for ticker, df in market_data.items():
            if 'date' in df.columns:
                dates = set(pd.to_datetime(df['date']).dt.date)
                all_dates_by_ticker[ticker] = dates
        
        # 找到所有股票共有的日期
        common_dates = set.intersection(*all_dates_by_ticker.values()) if all_dates_by_ticker else set()
        
        if common_dates:
            common_start = min(common_dates)
            common_end = max(common_dates)
            print(f"  公共日期范围: {common_start} → {common_end} (共{len(common_dates)}个交易日)")
            
            # 显示公共日期列表（用于调试）
            sorted_common = sorted(common_dates)
            print(f"  公共日期明细: {', '.join(str(d) for d in sorted_common)}")
            
            # 确保回测起始日期在公共日期范围内
            if start_date < common_start:
                print(f"  ⚠️  回测起始日 {start_date} 早于公共起始日 {common_start}，将从 {common_start} 开始")
                actual_start = common_start
            elif start_date > common_end:
                print(f"  ❌ 回测起始日 {start_date} 晚于公共结束日 {common_end}")
                return None, {}
            else:
                actual_start = start_date
                print(f"  ✓ 回测将从 {actual_start} 开始")
        else:
            actual_start = start_date
        
        for ticker, df in market_data.items():
            # 注意：不要在fromdate/todate中限制日期，让backtrader自己处理
            # 只要确保数据足够即可
            data_feed = bt.feeds.PandasData(
                dataname=df,
                datetime='date',
                open='open',
                high='high',
                low='low',
                close='close',
                volume='volume',
                openinterest=-1
            )
            data_feed._name = ticker
            self.cerebro.adddata(data_feed, name=ticker)
            
            # 显示每个股票的实际数据范围
            if 'date' in df.columns:
                df_dates = pd.to_datetime(df['date']).dt.date
                ticker_start = df_dates.min()
                ticker_end = df_dates.max()
                print(f"  ✓ {ticker}: {len(df)} 条数据 ({ticker_start} → {ticker_end})")
            else:
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
        total_cost = 0  # 总成本（数量 × 成本价）
        
        for ticker, pos in positions.items():
            position_cost = pos['quantity'] * pos['cost_price']
            total_cost += position_cost
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
        
        # 计算佣金：总成本与持仓成本的差额（从现金中扣除的部分）
        commission_paid = INITIAL_CASH - cash - total_cost
        
        print(f"\n账户摘要:")
        print(f"  初始资金: ${INITIAL_CASH:,.2f}")
        print(f"  持仓成本: ${total_cost:,.2f}")
        print(f"  交易佣金: ${commission_paid:,.2f}")
        print(f"  持仓市值: ${total_value:,.2f}")
        print(f"  现金余额: ${cash:,.2f}")
        print(f"  账户总值: ${final_value:,.2f}")
        print(f"\n  Portfolio Balance: ${final_value - INITIAL_CASH:,.2f} ({((final_value - INITIAL_CASH) / INITIAL_CASH * 100):.2f}%)")
    
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
        
        # 让用户选择组合
        try:
            choice = input("\n请输入组合名称查看详情（或按Enter返回）: ").strip()
            if not choice:
                return
            
            if choice not in portfolios:
                print(f"\n✗ 组合 '{choice}' 不存在")
                return
            
            # 执行回测以查看该组合
            print(f"\n{'='*80}")
            print(f"📚 加载组合: {choice}")
            print(f"{'='*80}")
            
            orders = self.db.get_all_orders(choice)
            if not orders:
                print(f"\n✗ 组合 '{choice}' 没有订单")
                return
            
            summary = self.db.get_portfolio_summary(choice)
            print(f"✓ 组合: {choice}")
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
            last_execution_date = summary['last_execution_date']  # 最后的执行日期
            min_end_date = last_order_date + timedelta(days=10)
            today = datetime.now().date()
            end_date = max(min_end_date, today + timedelta(days=1))  # 包含今天
            
            # 判断今天是否是周末
            weekday = today.weekday()
            is_weekend = weekday >= 5  # 5=周六, 6=周日
            
            # 获取最近的交易日（用于提示）
            if is_weekend:
                # 周六/周日 -> 上周五
                days_since_friday = weekday - 4
                last_trading_day = today - timedelta(days=days_since_friday)
                # 下周一
                next_trading_day = today + timedelta(days=(7 - weekday))
            else:
                last_trading_day = today
                next_trading_day = today
            
            print(f"  数据范围: {data_start_date} → {end_date}")
            print(f"  回测范围: {backtest_start_date} → {end_date}")
            print(f"  (首次执行: {summary['first_execution_date']})")
            print(f"  (最后执行: {last_execution_date})")
            print(f"  (今天: {today} {'【周末】' if is_weekend else ''})")
            
            # 检查最后执行日期是否在未来
            if last_execution_date > today:
                print(f"\n⚠️  执行日期在未来: {last_execution_date}")
                if is_weekend and last_execution_date == next_trading_day:
                    print(f"   这是周末订单，将在下周一 ({next_trading_day}) 执行")
                    print(f"   ❌ 股市还未开盘，暂无数据可用")
                    print(f"   请在 {next_trading_day} 之后重新运行")
                else:
                    print(f"   ❌ 执行日期还未到来，暂无数据可用")
                    print(f"   请在 {last_execution_date} 之后重新运行")
                return
            
            # 周末提示
            if is_weekend:
                print(f"\n📅 今天是周末，股市休市")
                print(f"   最新可用数据: {last_trading_day} (上周五)")
            
            # 如果最后订单是今天，提醒用户
            if last_order_date == today:
                if is_weekend:
                    print(f"\n⚠️  注意: 订单日期是今天（周末）")
                    print(f"   订单将在下周一 ({next_trading_day}) 执行")
                    print(f"   当前无法计算结果，请在下周一开盘后重新运行")
                else:
                    print(f"\n⚠️  注意: 最后订单日期是今天 ({today})")
                    print(f"   当天的市场数据可能还未更新（通常在收盘后1-2小时可用）")
                    print(f"   如果数据未更新，建议稍后重新运行以获取完整结果")
            elif is_weekend and (today - last_order_date).days <= 2:
                # 订单是周五/周六
                print(f"\n📅 订单日期在本周末附近")
                print(f"   最新可用数据: {last_trading_day} (上周五)")
            
            # 获取数据
            market_data = self.fetch_market_data(all_tickers, data_start_date, end_date)
            if not market_data:
                print("✗ 未能获取市场数据")
                return
                    # 检查关键日期的数据可用性
            print(f"\n🔍 数据可用性检查:")
            all_available_dates = set()
            for ticker, df in market_data.items():
                if 'date' in df.columns:
                    dates = set(pd.to_datetime(df['date']).dt.date)
                    all_available_dates.update(dates)
            
            if last_execution_date not in all_available_dates:
                print(f"   ❌ 执行日期 {last_execution_date} 的数据不可用")
                print(f"   可用数据范围: {min(all_available_dates)} → {max(all_available_dates)}")
                print(f"\n⚠️  无法执行回测：订单执行日期 ({last_execution_date}) 没有市场数据")
                
                if last_execution_date == today:
                    print(f"   原因: 今天的数据通常在收盘后1-2小时才可用")
                    print(f"   建议: 请在今天收盘后（约18:00后）重新运行")
                else:
                    print(f"   建议: 等待数据更新后重新运行")
                return
            
            # 检查执行日期之后是否有数据（backtrader需要至少一个后续交易日来完成订单）
            sorted_dates = sorted(all_available_dates)
            execution_date_index = sorted_dates.index(last_execution_date) if last_execution_date in sorted_dates else -1
            
            if execution_date_index == -1:
                # 执行日期不在可用数据中
                print(f"   ❌ 关键问题：执行日期 {last_execution_date} 不在任何股票的交易数据中")
                print(f"   可用交易日: {', '.join(str(d) for d in sorted_dates[:10])}")
                
                # 检查是否是刚过去的日期（数据延迟）
                days_ago = (today - last_execution_date).days
                if days_ago == 1:
                    print(f"\n   📌 {last_execution_date} 是昨天")
                    print(f"   原因: Yahoo Finance的历史数据通常延迟1-2天更新")
                    print(f"   昨天的数据可能今天晚些时候或明天才会出现在数据库中")
                    print(f"\n   建议: 请明天（{today + timedelta(days=1)}）重新运行")
                elif days_ago == 0:
                    print(f"\n   📌 {last_execution_date} 是今天")
                    print(f"   原因: 当天数据通常在收盘后1-2小时可用")
                    print(f"   建议: 请今晚18:00后或明天重新运行")
                elif 2 <= days_ago <= 5:
                    print(f"\n   📌 {last_execution_date} 是{days_ago}天前")
                    print(f"   可能原因: ")
                    # 检查是否是周末
                    weekday = last_execution_date.weekday()
                    if weekday >= 5:
                        print(f"   - 这天是周末（{['周一','周二','周三','周四','周五','周六','周日'][weekday]}），非交易日")
                    else:
                        print(f"   - 可能是公众假期（春节、中秋等）")
                        print(f"   - 或所有股票停牌")
                else:
                    # 检查是否是假期
                    weekday = last_execution_date.weekday()
                    if weekday >= 5:
                        print(f"\n   {last_execution_date} 是周末，非交易日")
                    else:
                        print(f"\n   {last_execution_date} 是工作日({['周一','周二','周三','周四','周五'][weekday]})，但可能是公众假期或所有股票停牌")
                
                # 找到最接近的交易日
                future_dates = [d for d in sorted_dates if d > last_execution_date]
                if future_dates:
                    next_date = min(future_dates)
                    print(f"\n   最近的可用交易日: {next_date}")
                    print(f"\n💡 临时方案: 将订单日期改为 {(next_date - timedelta(days=1)).strftime('%Y%m%d')}，")
                    print(f"              订单将在 {next_date} 执行")
                return
            
            has_next_day = execution_date_index < len(sorted_dates) - 1
            
            if not has_next_day:
                print(f"   ⚠️  执行日期 {last_execution_date} 是最后一个交易日")
                print(f"   可用数据: {sorted_dates[0]} → {sorted_dates[-1]} (共{len(sorted_dates)}个交易日)")
                print(f"\n❌ 无法完成订单结算：Backtrader需要执行日期之后至少一个交易日的数据")
                
                if last_execution_date == today:
                    weekday = today.weekday()
                    if weekday < 4:  # 周一到周四
                        next_trading_day = today + timedelta(days=1)
                        print(f"   订单将在今天 ({today}) 执行，但需要明天 ({next_trading_day}) 的数据才能结算")
                        print(f"   建议: 请在明天 ({next_trading_day}) 收盘后重新运行")
                    else:  # 周五
                        next_trading_day = today + timedelta(days=3)  # 下周一
                        print(f"   订单将在今天 ({today}) 执行，但需要下周一 ({next_trading_day}) 的数据才能结算")
                        print(f"   建议: 请在下周一 ({next_trading_day}) 收盘后重新运行")
                else:
                    print(f"   建议: 等待下一个交易日的数据更新后重新运行")
                return
            else:
                next_trading_day = sorted_dates[execution_date_index + 1]
                print(f"   ✓ 执行日期 {last_execution_date} 的数据可用")
                print(f"   ✓ 后续交易日 {next_trading_day} 的数据可用（用于订单结算）")
            
            # ========== 步骤 5: 运行回测（时光机回放）==========
            print("\n" + "=" * 80)
            print("⚙ 步骤 5: 执行完整回测（事件重放）")
            print("=" * 80)
            
            final_value, positions = self.run_backtest(market_data, orders, backtest_start_date, end_date)
            
            # ========== 步骤 6: 显示结果 ==========
            self.display_results(final_value, positions, choice)
            
            # ========== 步骤 7: 可视化 ==========
            plot_choice = input("\n是否绘制组合演进图? (y/n): ").strip().lower()
            if plot_choice == 'y':
                self.plot_results(choice)
            
            # 询问是否绘图
            plot_choice = input("\n是否绘制组合演进图? (y/n): ").strip().lower()
            if plot_choice == 'y':
                self.plot_results(choice)
                
        except KeyboardInterrupt:
            print("\n\n✓ 返回主菜单")
            return


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
