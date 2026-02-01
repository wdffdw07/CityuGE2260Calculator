# CityU GE2260 Calculator

基于**事件溯源（Event Sourcing）**架构的订单驱动回测系统，专为香港股票市场设计的T+N交易模拟器。

[![Python](https://img.shields.io/badge/Python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![Backtrader](https://img.shields.io/badge/Backtrader-1.9.78-green.svg)](https://www.backtrader.com/)
[![License](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

## 🌟 核心特性

- ✅ **事件溯源架构**：只存储订单历史，每次从头回放计算持仓
- ✅ **零误差**：避免持仓状态不同步问题，确保数据一致性
- ✅ **T+N支持**：完美支持增量交易，可跨多个交易周期
- ✅ **完整统计**：从首次订单到今天的完整净值曲线
- ✅ **自动复权**：yfinance数据包含分红拆股调整
- ✅ **可视化分析**：账户价值曲线和每日收益率分析

## 📊 系统架构

```
2260calculator/
├── main.py                # 主程序 - 时光机控制器
├── run.bat / run.ps1      # 启动脚本
├── clear_database.py      # 数据库清理工具
├── quick_clear.py         # 快速清空脚本
├── order/                 # 订单文件夹
│   └── YYYYMMDD/          # 日期子文件夹
│       └── Trade Order Form.xlsx
├── history/               # 数据库（自动生成）
│   └── trading.db
└── src/                   # 源代码
    ├── parser/            # 解析层 - Excel/CSV订单解析
    ├── storage/           # 存储层 - 订单历史管理
    ├── strategy/          # 策略层 - 多批次订单执行
    └── analyse/           # 分析层 - 可视化绘图
```

## 🚀 快速开始

### 环境要求

- Python 3.10+
- uv (推荐) 或 pip

> **⚠️ 重要提示：** 本项目**必须安装 backtrader**！  
> backtrader 是一个专业的Python量化回测框架，是本系统的核心依赖。系统使用backtrader的事件驱动引擎来执行交易策略、计算持仓、统计收益等所有核心功能。**没有backtrader，系统将无法运行**。请务必按照下方步骤完成安装。

### 环境配置

#### 方法一：使用 requirements.txt（推荐）

```bash
# 1. 克隆或下载项目
cd CityuGE2260Calculator

# 2. 创建虚拟环境（推荐）
python -m venv venv

# 3. 激活虚拟环境
# Windows CMD
venv\Scripts\activate.bat

# Windows PowerShell
venv\Scripts\Activate.ps1

# Linux/Mac
source venv/bin/activate

# 4. 安装所有依赖
pip install -r requirements.txt
```

#### 方法二：使用 uv（更快速）

```bash
# 1. 安装uv
pip install uv

# 2. 创建虚拟环境并安装依赖
uv venv
uv pip install -r requirements.txt
```

#### 方法三：手动安装

```bash
pip install backtrader>=1.9.78.123 yfinance>=1.1.0 pandas>=2.3.3 openpyxl>=3.1.5 matplotlib sqlalchemy>=2.0.46
```

### 核心依赖说明

本项目的核心依赖是 **backtrader**，一个功能强大的Python量化回测框架：

- **backtrader (>=1.9.78.123)**: 事件驱动的回测引擎，支持多种交易策略
- **yfinance**: 从Yahoo Finance获取港股历史数据（自动复权）
- **pandas**: 数据处理和分析
- **openpyxl**: Excel订单文件解析
- **matplotlib**: 绘制净值曲线和收益率图表
- **sqlalchemy**: 订单历史数据库管理（SQLite）

### 验证安装

```bash
python -c "import backtrader; print(f'Backtrader version: {backtrader.__version__}')"
python -c "import yfinance; import pandas; import openpyxl; print('所有依赖安装成功！')"
```

### 准备订单文件

在 `order/YYYYMMDD/` 文件夹中放入Excel订单文件：

| Asset Name | Asset Type | Action | Quantity |
|------------|------------|--------|----------|
| 2800.HK Tracker Fund | Stock | Buy | 500 |
| 3033.HK CSOP HS TECH | Stock | Buy | 800 |

### 运行系统

```bash
# Windows批处理
run.bat

# PowerShell
.\run.ps1

# 直接运行
uv run python main.py
```

## 📖 使用流程

### 1. 执行新订单（增量模式）

```
1. 选择"执行新订单"
2. 输入订单日期（YYYYMMDD格式）
3. 输入组合名称（新建或追加）
4. 系统自动：
   - 解析订单文件
   - 加载所有历史订单
   - 获取市场数据
   - 从头回放所有交易
   - 统计到今天
   - 显示持仓和收益
```

### 2. 查看现有组合

```
查看已创建的投资组合列表
显示订单数、时间跨度、股票数等信息
```

## 🎯 核心理念：事件溯源

传统系统存储"当前持仓"，而本系统存储"历史交易记录"。

**优势**：
- 🔒 **数据不可变**：订单历史永久保存，不会被覆盖
- 🔄 **完全可重现**：任何时刻的状态都能通过重放订单精确还原
- 🐛 **零状态错误**：避免持仓数据不同步导致的错误
- 📈 **完整审计**：从第一天到今天的完整资金曲线

**工作流程**：
```
历史订单 → 按时间排序 → Backtrader重放 → 计算持仓 → 显示结果
```

## 🔧 技术栈

| 组件 | 版本 | 用途 |
|------|------|------|
| Backtrader | 1.9.78+ | 回测引擎（Cheat-On-Open模式）|
| yfinance | 1.1.0+ | 获取香港股市数据（.HK后缀）|
| SQLAlchemy | 2.0+ | ORM框架（订单持久化）|
| pandas | 2.3+ | 数据处理 |
| openpyxl | 3.1+ | Excel文件读取 |
| matplotlib | - | 图表可视化 |

## 📊 配置参数

```python
INITIAL_CASH = 100000.0    # 初始资金 100,000 HKD
COMMISSION_RATE = 0.001    # 佣金率 0.1%
```

## 🛠️ 工具脚本

### 数据库清理工具

```bash
# 完整清理工具（带确认）
uv run python clear_database.py

# 快速清空（无确认）
uv run python quick_clear.py
```

## 📝 订单文件格式

支持 `.xlsx` 和 `.csv` 格式：

**Excel列名支持**：
- `Asset Name` / `资产名称`
- `Asset Type (Stock, Bond, Foreign Currency)` / `资产类型`
- `Action (Buy/ Sell/ Hold)` / `操作`
- `Quantity` / `数量`

**股票代码识别**：
- 自动识别：`2800.HK`、`盈富基金`、`Tracker Fund`
- 支持映射：常见股票名称自动转换为代码

## 📈 示例输出

```
💼 当前持仓 (5 个):
==================================================================
代码         数量      成本价       现价        市值        盈亏
------------------------------------------------------------------
2800.HK      500    $26.98     $27.60    $13,800    +$310
3033.HK      800    $5.61      $5.61     $4,484     $0
2819.HK      200    $102.10    $101.80   $20,360    -$60
0823.HK      100    $35.84     $35.92    $3,592     +$8
3199.HK      40     $116.00    $116.90   $4,676     +$36
------------------------------------------------------------------
合计                                      $46,912    +$294
==================================================================

账户摘要:
  持仓市值: $46,912.00
  现金余额: $53,335.38
  账户总值: $100,247.38
  总收益率: 0.25%
```

## 🎨 可视化

系统自动生成双图表：
1. **账户总价值曲线**：完整资金变化趋势
2. **每日收益率柱状图**：红绿柱展示涨跌

## 🔍 常见问题

### Q: 为什么选择事件溯源？
A: 传统方式存储持仓容易出错，事件溯源通过存储订单历史确保数据绝对准确，且支持任意时刻状态重现。

### Q: 支持哪些股票市场？
A: 目前专注香港股市（.HK后缀），可扩展至其他yfinance支持的市场。

### Q: T+7是什么意思？
A: 支持隔多天追加订单，系统自动从第一笔订单开始完整回放。

### Q: 数据从哪里来？
A: 使用yfinance从Yahoo Finance获取实时行情数据（包含复权）。

## 📄 许可证

MIT License

## 🙏 致谢

- [Backtrader](https://www.backtrader.com/) - 强大的Python回测框架
- [yfinance](https://github.com/ranaroussi/yfinance) - 免费金融数据API
- 香港城市大学 GE2260 课程

## 📧 联系方式

如有问题或建议，欢迎提Issue或PR！

---

**注意**：本系统仅用于教育和研究目的，不构成投资建议。投资有风险，入市需谨慎。
