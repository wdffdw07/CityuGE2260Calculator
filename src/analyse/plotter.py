"""
可视化分析模块
绘制账户价值曲线和收益率分析
"""
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from datetime import datetime
from typing import List
import matplotlib.font_manager as fm


class PortfolioPlotter:
    """组合分析绘图器"""
    
    def __init__(self):
        """初始化绘图器"""
        # 设置中文字体 - 强制使用指定字体
        import matplotlib
        matplotlib.rcParams['font.sans-serif'] = ['SimHei', 'Microsoft YaHei', 'SimSun', 'KaiTi', 'FangSong']
        matplotlib.rcParams['axes.unicode_minus'] = False
        # 清除字体缓存
        matplotlib.font_manager._load_fontmanager(try_read_cache=False)
        print("✓ 已配置中文字体")
    
    def plot_portfolio_evolution(self, dates: List[datetime], values: List[float], 
                                 initial_cash: float = 100000, portfolio_name: str = "",
                                 stock_values: dict = None):
        """
        绘制组合演进图
        
        Args:
            dates: 日期列表
            values: 账户价值列表
            initial_cash: 初始资金
            portfolio_name: 组合名称
            stock_values: 每个股票的价值变化 {ticker: [values]}
        """
        if not dates or not values:
            print("✗ 无数据可绘制")
            return
        
        # 计算统计数据
        total_return = ((values[-1] - initial_cash) / initial_cash) * 100
        max_value = max(values)
        min_value = min(values)
        max_idx = values.index(max_value)
        min_idx = values.index(min_value)
        
        # 如果有每日收益率数据，计算波动率
        if len(values) > 1:
            daily_returns = [(values[i] - values[i-1]) / values[i-1] * 100 for i in range(1, len(values))]
            avg_return = sum(daily_returns) / len(daily_returns) if daily_returns else 0
            volatility = (sum((r - avg_return) ** 2 for r in daily_returns) / len(daily_returns)) ** 0.5 if daily_returns else 0
        else:
            daily_returns = []
            avg_return = 0
            volatility = 0
        
        # 创建图表 - 如果有股票数据则3行，否则2行
        # 调整figure布局，右侧留空间放表格
        if stock_values and any(stock_values.values()):
            fig = plt.figure(figsize=(18, 12))
            gs = fig.add_gridspec(3, 1, height_ratios=[2, 1.5, 1], hspace=0.3, left=0.08, right=0.78)
            ax1 = fig.add_subplot(gs[0])
            ax2 = fig.add_subplot(gs[1])
            ax3 = fig.add_subplot(gs[2])
        else:
            fig = plt.figure(figsize=(18, 10))
            gs = fig.add_gridspec(2, 1, height_ratios=[2, 1], hspace=0.3, left=0.08, right=0.78)
            ax1 = fig.add_subplot(gs[0])
            ax2 = None
            ax3 = fig.add_subplot(gs[1])
        
        title = f'📊 组合演进分析'
        if portfolio_name:
            title += f' - {portfolio_name}'
        fig.suptitle(title, fontsize=16, fontweight='bold')
        
        # === 图1: 账户总价值曲线 ===
        ax1.plot(dates, values, linewidth=2.5, color='#2E86AB', marker='o', markersize=4, label='账户总价值', zorder=3)
        ax1.axhline(y=initial_cash, color='gray', linestyle='--', alpha=0.5, label='初始资金', linewidth=1.5)
        ax1.fill_between(dates, initial_cash, values, alpha=0.15, color='#2E86AB')
        
        # 标注最高点和最低点
        ax1.scatter([dates[max_idx]], [max_value], color='green', s=150, zorder=5, marker='^', edgecolors='darkgreen', linewidths=1.5)
        ax1.scatter([dates[min_idx]], [min_value], color='red', s=150, zorder=5, marker='v', edgecolors='darkred', linewidths=1.5)
        
        ax1.set_ylabel('账户价值 (HKD)', fontsize=12, fontweight='bold')
        ax1.set_title('账户总价值变化', fontsize=13, pad=10)
        ax1.grid(True, alpha=0.3, linestyle='--')
        ax1.legend(loc='upper left', fontsize=10)
        ax1.xaxis.set_major_formatter(mdates.DateFormatter('%m-%d'))
        
        # 在图的右侧添加结算数据表格（使用figure坐标）
        stats_data = [
            ['Initial Cash', f'${initial_cash:,.2f}'],
            ['Final Value', f'${values[-1]:,.2f}'],
            ['Total Profit', f'${values[-1] - initial_cash:,.2f}'],
            ['Total Return', f'{total_return:.2f}%'],
            ['Max Value', f'${max_value:,.2f}'],
            ['Min Value', f'${min_value:,.2f}'],
            ['Avg Daily Return', f'{avg_return:.3f}%'],
            ['Volatility', f'{volatility:.3f}%']
        ]
        
        # 创建独立的axis用于放置表格（在figure右侧）
        # 位置：[left, bottom, width, height] in figure coordinates
        table_ax = fig.add_axes([0.80, 0.70, 0.18, 0.20])
        table_ax.axis('off')  # 隐藏坐标轴
        
        # 创建表格
        table = table_ax.table(cellText=stats_data,
                              colWidths=[0.5, 0.5],
                              cellLoc='left',
                              loc='center',
                              bbox=[0, 0, 1, 1])
        
        table.auto_set_font_size(False)
        table.set_fontsize(10)
        table.scale(1, 2)
        
        # 设置表格样式
        for i in range(len(stats_data)):
            table[(i, 0)].set_facecolor('#E8F4F8')
            table[(i, 0)].set_text_props(weight='bold', fontsize=10)
            table[(i, 1)].set_facecolor('#F5F5F5')
            table[(i, 1)].set_text_props(fontsize=10)
            table[(i, 0)].set_edgecolor('black')
            table[(i, 1)].set_edgecolor('black')
            table[(i, 0)].set_linewidth(1.5)
            table[(i, 1)].set_linewidth(1.5)
        
        # === 图2: 每个股票的持仓价值变化 ===
        if ax2 and stock_values:
            # 过滤掉全为0的股票
            active_stocks = {ticker: vals for ticker, vals in stock_values.items() 
                           if any(v > 0 for v in vals)}
            
            if active_stocks:
                # 使用不同颜色
                colors = plt.cm.tab10(range(len(active_stocks)))
                
                for idx, (ticker, vals) in enumerate(active_stocks.items()):
                    # 确保值列表长度与日期匹配
                    if len(vals) == len(dates):
                        ax2.plot(dates, vals, linewidth=2, marker='o', markersize=3, 
                               label=ticker, color=colors[idx], alpha=0.8)
                
                ax2.set_ylabel('持仓价值 (HKD)', fontsize=12, fontweight='bold')
                ax2.set_title('各股票持仓价值变化', fontsize=13, pad=10)
                ax2.grid(True, alpha=0.3, linestyle='--')
                ax2.legend(loc='best', fontsize=9, ncol=2)
                ax2.xaxis.set_major_formatter(mdates.DateFormatter('%m-%d'))
        
        # === 图3: 每日收益率 ===
        if len(values) > 1:
            colors_ret = ['green' if r >= 0 else 'red' for r in daily_returns]
            
            ax3.bar(dates[1:], daily_returns, color=colors_ret, alpha=0.6, width=0.8)
            ax3.axhline(y=0, color='black', linestyle='-', linewidth=0.8)
            ax3.set_xlabel('日期', fontsize=12, fontweight='bold')
            ax3.set_ylabel('日收益率 (%)', fontsize=12, fontweight='bold')
            ax3.set_title('每日收益率', fontsize=13, pad=10)
            ax3.grid(True, alpha=0.3, axis='y', linestyle='--')
            ax3.xaxis.set_major_formatter(mdates.DateFormatter('%m-%d'))
        
        plt.xticks(rotation=45)
        plt.tight_layout()
        
        # 显示统计信息到控制台
        print(f"\n📈 统计摘要:")
        print(f"  初始资金: ${initial_cash:,.2f}")
        print(f"  最终价值: ${values[-1]:,.2f}")
        print(f"  总收益: ${values[-1] - initial_cash:,.2f}")
        print(f"  总收益率: {total_return:.2f}%")
        print(f"  最高价值: ${max_value:,.2f} ({dates[max_idx].strftime('%Y-%m-%d')})")
        print(f"  最低价值: ${min_value:,.2f} ({dates[min_idx].strftime('%Y-%m-%d')})")
        print(f"  平均日收益率: {avg_return:.3f}%")
        print(f"  收益率波动率: {volatility:.3f}%")
        
        # 保存图片
        from pathlib import Path
        output_dir = Path('history')
        output_dir.mkdir(exist_ok=True)
        
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = f'portfolio_{portfolio_name}_{timestamp}.png' if portfolio_name else f'portfolio_{timestamp}.png'
        filepath = output_dir / filename
        
        plt.savefig(filepath, dpi=150, bbox_inches='tight', facecolor='white')
        print(f"\n💾 图表已保存: {filepath}")
        
        # 保存统计报告文本文件
        report_filename = filepath.stem + '_report.txt'
        report_path = output_dir / report_filename
        
        with open(report_path, 'w', encoding='utf-8') as f:
            f.write(f"{'='*60}\n")
            f.write(f"Portfolio Analysis Report - {portfolio_name}\n")
            f.write(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write(f"{'='*60}\n\n")
            
            f.write(f"Initial Cash:         ${initial_cash:,.2f}\n")
            f.write(f"Final Value:          ${values[-1]:,.2f}\n")
            f.write(f"Total Profit:         ${values[-1] - initial_cash:,.2f}\n")
            f.write(f"Total Return:         {total_return:.2f}%\n")
            f.write(f"Max Value:            ${max_value:,.2f} ({dates[max_idx].strftime('%Y-%m-%d')})\n")
            f.write(f"Min Value:            ${min_value:,.2f} ({dates[min_idx].strftime('%Y-%m-%d')})\n")
            f.write(f"Average Daily Return: {avg_return:.3f}%\n")
            f.write(f"Volatility:           {volatility:.3f}%\n")
            
            if stock_values and any(stock_values.values()):
                f.write(f"\n{'='*60}\n")
                f.write(f"Stock Holdings Summary\n")
                f.write(f"{'='*60}\n\n")
                
                for ticker, vals in stock_values.items():
                    if vals and len(vals) == len(dates):
                        final_value = vals[-1]
                        if final_value > 0:
                            f.write(f"{ticker:15} Final Value: ${final_value:,.2f}\n")
        
        print(f"💾 统计报告已保存: {report_path}")
        
        plt.show()
    
    def plot_holdings_pie(self, holdings: dict, portfolio_name: str = ""):
        """
        绘制持仓饼图
        
        Args:
            holdings: 持仓字典 {ticker: {'quantity': xxx, 'value': xxx}}
            portfolio_name: 组合名称
        """
        if not holdings:
            print("✗ 无持仓数据")
            return
        
        # 准备数据
        labels = []
        values = []
        
        for ticker, info in holdings.items():
            labels.append(ticker)
            values.append(info['value'])
        
        # 创建饼图
        fig, ax = plt.subplots(figsize=(10, 8))
        
        colors = plt.cm.Set3(range(len(labels)))
        wedges, texts, autotexts = ax.pie(
            values, 
            labels=labels, 
            autopct='%1.1f%%',
            startangle=90,
            colors=colors
        )
        
        # 美化文字
        for text in texts:
            text.set_fontsize(11)
        for autotext in autotexts:
            autotext.set_color('white')
            autotext.set_fontweight('bold')
            autotext.set_fontsize(10)
        
        title = '📊 持仓分布'
        if portfolio_name:
            title += f' - {portfolio_name}'
        ax.set_title(title, fontsize=14, fontweight='bold', pad=20)
        
        plt.tight_layout()
        
        # 保存图片
        from pathlib import Path
        output_dir = Path('history')
        output_dir.mkdir(exist_ok=True)
        
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = f'holdings_{portfolio_name}_{timestamp}.png' if portfolio_name else f'holdings_{timestamp}.png'
        filepath = output_dir / filename
        
        plt.savefig(filepath, dpi=150, bbox_inches='tight', facecolor='white')
        print(f"\n💾 图表已保存: {filepath}")
        
        plt.show()
