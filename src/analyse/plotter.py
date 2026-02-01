"""
可视化分析模块
绘制账户价值曲线和收益率分析
"""
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from datetime import datetime
from typing import List


class PortfolioPlotter:
    """组合分析绘图器"""
    
    def __init__(self):
        """初始化绘图器"""
        # 设置中文字体
        plt.rcParams['font.sans-serif'] = ['Microsoft YaHei', 'SimHei', 'Arial']
        plt.rcParams['axes.unicode_minus'] = False
    
    def plot_portfolio_evolution(self, dates: List[datetime], values: List[float], 
                                 initial_cash: float = 100000, portfolio_name: str = ""):
        """
        绘制组合演进图
        
        Args:
            dates: 日期列表
            values: 账户价值列表
            initial_cash: 初始资金
            portfolio_name: 组合名称
        """
        if not dates or not values:
            print("✗ 无数据可绘制")
            return
        
        # 创建图表
        fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(14, 9))
        
        title = f'📊 组合演进分析'
        if portfolio_name:
            title += f' - {portfolio_name}'
        fig.suptitle(title, fontsize=16, fontweight='bold')
        
        # === 图1: 账户总价值曲线 ===
        ax1.plot(dates, values, linewidth=2, color='#2E86AB', marker='o', markersize=4, label='账户价值')
        ax1.axhline(y=initial_cash, color='gray', linestyle='--', alpha=0.5, label='初始资金')
        ax1.fill_between(dates, initial_cash, values, alpha=0.2, color='#2E86AB')
        
        # 标注最高点和最低点
        max_value = max(values)
        min_value = min(values)
        max_idx = values.index(max_value)
        min_idx = values.index(min_value)
        
        ax1.scatter([dates[max_idx]], [max_value], color='green', s=100, zorder=5, marker='^')
        ax1.scatter([dates[min_idx]], [min_value], color='red', s=100, zorder=5, marker='v')
        
        ax1.set_ylabel('账户价值 (HKD)', fontsize=12, fontweight='bold')
        ax1.set_title('账户总价值变化', fontsize=13, pad=10)
        ax1.grid(True, alpha=0.3, linestyle='--')
        ax1.legend(loc='best')
        ax1.xaxis.set_major_formatter(mdates.DateFormatter('%m-%d'))
        
        # === 图2: 每日收益率 ===
        if len(values) > 1:
            daily_returns = [(values[i] - values[i-1]) / values[i-1] * 100 for i in range(1, len(values))]
            colors = ['green' if r >= 0 else 'red' for r in daily_returns]
            
            ax2.bar(dates[1:], daily_returns, color=colors, alpha=0.6, width=0.8)
            ax2.axhline(y=0, color='black', linestyle='-', linewidth=0.8)
            ax2.set_xlabel('日期', fontsize=12, fontweight='bold')
            ax2.set_ylabel('日收益率 (%)', fontsize=12, fontweight='bold')
            ax2.set_title('每日收益率', fontsize=13, pad=10)
            ax2.grid(True, alpha=0.3, axis='y', linestyle='--')
            ax2.xaxis.set_major_formatter(mdates.DateFormatter('%m-%d'))
        
        plt.xticks(rotation=45)
        plt.tight_layout()
        
        # 显示统计信息
        total_return = ((values[-1] - initial_cash) / initial_cash) * 100
        print(f"\n📈 统计摘要:")
        print(f"  初始资金: ${initial_cash:,.2f}")
        print(f"  最终价值: ${values[-1]:,.2f}")
        print(f"  总收益: ${values[-1] - initial_cash:,.2f}")
        print(f"  总收益率: {total_return:.2f}%")
        print(f"  最高价值: ${max_value:,.2f} ({dates[max_idx].strftime('%Y-%m-%d')})")
        print(f"  最低价值: ${min_value:,.2f} ({dates[min_idx].strftime('%Y-%m-%d')})")
        
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
        plt.show()
