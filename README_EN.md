# CityU GE2260 Calculator

An **Event Sourcing** architecture-based order-driven backtesting system designed for Hong Kong stock market T+N trading simulation.

[![Python](https://img.shields.io/badge/Python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![Backtrader](https://img.shields.io/badge/Backtrader-1.9.78-green.svg)](https://www.backtrader.com/)
[![License](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

## 🌟 Core Features

- ✅ **Event Sourcing Architecture**: Store only order history, replay from scratch to calculate positions
- ✅ **Zero Errors**: Avoid position state synchronization issues, ensure data consistency
- ✅ **T+N Support**: Perfect incremental trading support across multiple trading cycles
- ✅ **Complete Statistics**: Full equity curve from first order to today
- ✅ **Auto Adjustment**: yfinance data includes dividend and split adjustments
- ✅ **Visual Analysis**: Account value curves and daily return rate analysis
- ✅ **Multi-Stock Tracking**: Individual position value curves for each stock
- ✅ **Auto Reporting**: Export charts and detailed text reports automatically

## 📊 System Architecture

```
2260calculator/
├── main.py                # Main program - Time machine controller
├── run.bat / run.ps1      # Launch scripts
├── clear_database.py      # Database cleanup tool
├── quick_clear.py         # Quick clear script
├── order/                 # Order folder
│   └── YYYYMMDD/          # Date subfolders
│       └── Trade Order Form.xlsx
├── history/               # Database & Reports (auto-generated)
│   ├── trading.db         # Order history database
│   ├── portfolio_*.png    # Chart images
│   └── portfolio_*_report.txt  # Statistics reports
└── src/                   # Source code
    ├── parser/            # Parsing layer - Excel/CSV order parsing
    ├── storage/           # Storage layer - Order history management
    ├── strategy/          # Strategy layer - Multi-batch order execution
    └── analyse/           # Analysis layer - Visualization plotting
```

## 🚀 Quick Start

### Requirements

- Python 3.10+
- uv (recommended) or pip

> **⚠️ IMPORTANT:** This project **requires backtrader**!  
> Backtrader is a professional Python quantitative backtesting framework and the core dependency of this system. The system uses backtrader's event-driven engine to execute trading strategies, calculate positions, compute returns, and all other core functions. **Without backtrader, the system will not run**. Please follow the steps below to complete the installation.

### Environment Setup

#### Method 1: Using requirements.txt (Recommended)

```bash
# 1. Clone or download the project
cd CityuGE2260Calculator

# 2. Create virtual environment (recommended)
python -m venv venv

# 3. Activate virtual environment
# Windows CMD
venv\Scripts\activate.bat

# Windows PowerShell
venv\Scripts\Activate.ps1

# Linux/Mac
source venv/bin/activate

# 4. Install all dependencies
pip install -r requirements.txt
```

#### Method 2: Using uv (Faster)

```bash
# 1. Install uv
pip install uv

# 2. Create virtual environment and install dependencies
uv venv
uv pip install -r requirements.txt
```

#### Method 3: Manual Installation

```bash
pip install backtrader>=1.9.78.123 yfinance>=1.1.0 pandas>=2.3.3 openpyxl>=3.1.5 matplotlib sqlalchemy>=2.0.46
```

### Core Dependencies

The core dependency of this project is **backtrader**, a powerful Python quantitative backtesting framework:

- **backtrader (>=1.9.78.123)**: Event-driven backtesting engine supporting multiple trading strategies
- **yfinance**: Fetch Hong Kong stock historical data from Yahoo Finance (auto-adjusted)
- **pandas**: Data processing and analysis
- **openpyxl**: Excel order file parsing
- **matplotlib**: Plot equity curves and return charts
- **sqlalchemy**: Order history database management (SQLite)

### Verify Installation

```bash
python -c "import backtrader; print(f'Backtrader version: {backtrader.__version__}')"
python -c "import yfinance; import pandas; import openpyxl; print('All dependencies installed successfully!')"
```

### Prepare Order Files

Place Excel order files in `order/YYYYMMDD/` folder:

| Asset Name | Asset Type | Action | Quantity |
|------------|------------|--------|----------|
| 2800.HK Tracker Fund | Stock | Buy | 500 |
| 3033.HK CSOP HS TECH | Stock | Buy | 800 |

### Run the System

```bash
# Windows Batch
run.bat

# PowerShell
.\run.ps1

# Direct run
uv run python main.py
```

## 📖 Usage Workflow

### 1. Execute New Orders (Incremental Mode)

```
1. Select "Execute New Orders"
2. Enter order date (YYYYMMDD format)
3. Enter portfolio name (create new or append to existing)
4. System automatically:
   - Parse order files
   - Load all historical orders
   - Fetch market data
   - Replay all trades from the beginning
   - Calculate statistics to today
   - Display positions and returns
   - Generate charts and reports
```

### 2. View Existing Portfolios

```
View list of created portfolios
Display order count, time span, stock count, etc.
```

## 🎯 Core Concept: Event Sourcing

Traditional systems store "current positions," while this system stores "historical transaction records."

**Advantages**:
- 🔒 **Immutable Data**: Order history is permanently saved, never overwritten
- 🔄 **Fully Reproducible**: Any state at any moment can be accurately restored by replaying orders
- 🐛 **Zero State Errors**: Avoid errors caused by position data inconsistencies
- 📈 **Complete Audit Trail**: Full capital curve from day one to today

**Workflow**:
```
Historical Orders → Sort by Time → Backtrader Replay → Calculate Positions → Display Results
```

## 🔧 Technology Stack

| Component | Version | Purpose |
|-----------|---------|---------|
| Backtrader | 1.9.78+ | Backtesting engine (Cheat-On-Open mode) |
| yfinance | 1.1.0+ | Fetch Hong Kong market data (.HK suffix) |
| SQLAlchemy | 2.0+ | ORM framework (order persistence) |
| pandas | 2.3+ | Data processing |
| openpyxl | 3.1+ | Excel file reading |
| matplotlib | - | Chart visualization |

## 📊 Configuration Parameters

```python
INITIAL_CASH = 100000.0    # Initial cash: 100,000 HKD
COMMISSION_RATE = 0.001    # Commission rate: 0.1%
```

## 🛠️ Utility Scripts

### Database Cleanup Tools

```bash
# Full cleanup tool (with confirmation)
uv run python clear_database.py

# Quick clear (no confirmation)
uv run python quick_clear.py
```

## 📝 Order File Format

Supports `.xlsx` and `.csv` formats:

**Excel Column Names Supported**:
- `Asset Name` / `资产名称`
- `Asset Type (Stock, Bond, Foreign Currency)` / `资产类型`
- `Action (Buy/ Sell/ Hold)` / `操作`
- `Quantity` / `数量`

**Stock Code Recognition**:
- Auto-detect: `2800.HK`, `盈富基金`, `Tracker Fund`
- Mapping support: Common stock names automatically converted to codes

## 📈 Sample Output

```
💼 Current Holdings (5 stocks):
==================================================================
Ticker       Quantity   Cost Price   Current   Market Value   P&L
------------------------------------------------------------------
2800.HK      500        $26.98       $27.60    $13,800        +$310
3033.HK      800        $5.61        $5.61     $4,484         $0
2819.HK      200        $102.10      $101.80   $20,360        -$60
0823.HK      100        $35.84       $35.92    $3,592         +$8
3199.HK      40         $116.00      $116.90   $4,676         +$36
------------------------------------------------------------------
Total                                           $46,912        +$294
==================================================================

Account Summary:
  Market Value: $46,912.00
  Cash Balance: $53,335.38
  Total Value:  $100,247.38
  Total Return: 0.25%
```

## 🎨 Visualization

The system automatically generates comprehensive charts:

1. **Account Total Value Curve**: Complete capital change trend
   - Line chart with initial cash reference
   - Peak and valley markers
   - Statistics table on the right side
   
2. **Individual Stock Position Values**: Each stock's position value over time
   - Multiple color-coded lines
   - Track individual stock performance
   
3. **Daily Return Rate Bar Chart**: Red/green bars showing gains/losses
   - Easy visual identification of volatility
   - Daily performance tracking

**Auto-Export**:
- Charts saved as PNG files in `history/` folder
- Detailed text reports with all statistics
- Files named with portfolio name and timestamp

## 🔍 FAQ

### Q: Why Event Sourcing?
A: Traditional methods store positions which can cause errors. Event sourcing stores order history to ensure absolute accuracy and supports state reproduction at any point in time.

### Q: Which stock markets are supported?
A: Currently focused on Hong Kong stock market (.HK suffix), can be extended to other markets supported by yfinance.

### Q: What does T+N mean?
A: Support for adding orders after multiple days. The system automatically replays completely from the first order.

### Q: Where does the data come from?
A: Uses yfinance to fetch real-time market data from Yahoo Finance (including adjustments).

### Q: Can I use my own order format?
A: Yes, modify the parser in `src/parser/excel_parser.py` to adapt to your format.

### Q: How are Chinese fonts handled in charts?
A: Charts use English labels to avoid font encoding issues. All statistics are also exported as text reports.

## 📊 Output Files

All results are saved in the `history/` folder:

- `trading.db` - SQLite database with order history
- `portfolio_[name]_[timestamp].png` - Chart images
- `portfolio_[name]_[timestamp]_report.txt` - Detailed statistics reports

Report content includes:
- Initial Cash, Final Value, Total Profit, Return Rate
- Max/Min Values with dates
- Average Daily Return, Volatility
- Individual stock final values

## 📄 License

MIT License

## 🙏 Acknowledgments

- [Backtrader](https://www.backtrader.com/) - Powerful Python backtesting framework
- [yfinance](https://github.com/ranaroussi/yfinance) - Free financial data API
- City University of Hong Kong GE2260 Course

## 📧 Contact

For questions or suggestions, feel free to open an Issue or submit a PR!

---

**Disclaimer**: This system is for educational and research purposes only and does not constitute investment advice. Investing carries risk; trade carefully.
