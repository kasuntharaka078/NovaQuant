# 🚀 NovaQuant - Advanced Trading Bot

A professional-grade multi-strategy backtesting and paper trading platform built with Streamlit.

## Features

### 📊 Multiple Trading Strategies
- **SMA Crossover** - Classic Simple Moving Average crossover strategy
- **RSI Overbought/Sold** - Relative Strength Index based signals
- **MACD** - Moving Average Convergence Divergence
- **Bollinger Bands** - Mean reversion strategy using Bollinger Bands
- **Hybrid (SMA + RSI)** - Combined strategy requiring both SMA and RSI signals

### 🛡️ Risk Management
- Configurable position sizing based on account risk percentage
- Stop-loss levels with automatic exit
- Take-profit targets
- Risk/reward ratio visualization

### 📈 Advanced Analytics
- **Comprehensive Performance Metrics:**
  - Total Return & Annual Return
  - Sharpe Ratio (risk-adjusted returns)
  - Maximum Drawdown
  - Win Rate
  - Profit Factor
  - Volatility
  - Total Trades

- **Visual Analysis:**
  - Equity Curve
  - Drawdown Over Time
  - Price with Indicators
  - Trade Log

### 🔬 Optimization
- Grid search parameter optimization
- Multi-symbol comparison
- Period backtesting

### 💾 Data Management
- Upload CSV files with OHLCV data
- Fetch live data from Binance (via CCXT)
- Date range filtering (3 months, 6 months, 1 year, custom)
- Export results as JSON

### 📱 Paper Trading
- Simulated live trading on Binance testnet
- Real-time signal generation
- Position management
- Order execution logging

## Installation

### 1. Clone the Repository
```bash
git clone https://github.com/kasuntharaka078-2/NovaQuant.git
cd NovaQuant
```

### 2. Create Virtual Environment (Optional but Recommended)
```bash
# On Windows
python -m venv venv
venv\Scripts\activate

# On macOS/Linux
python3 -m venv venv
source venv/bin/activate
```

### 3. Install Dependencies
```bash
pip install -r requirements.txt
```

## Running the Application

### Start Streamlit App
```bash
streamlit run app.py
```

The app will open in your default browser at `http://localhost:8501`

## Usage Guide

### Step 1: Load Data
1. Choose data source:
   - **Upload CSV**: Your own OHLCV data (columns: date, open, high, low, close, volume)
   - **Fetch from Binance**: Live data from Binance testnet
2. Select the trading symbol (e.g., BTC/USDT, ETH/USDT)

### Step 2: Configure Strategy
1. Select strategy type from dropdown
2. Adjust strategy-specific parameters:
   - **SMA**: Short and long periods
   - **RSI**: Period, overbought (default 70), oversold (default 30) levels
   - **MACD**: Fast, slow, and signal periods
   - **Bollinger Bands**: Period and standard deviations
   - **Hybrid**: Combined SMA and RSI parameters

### Step 3: Set Risk Management
1. Initial capital (USD)
2. Risk per trade (% of equity)
3. Enable/configure stop-loss percentage
4. Enable/configure take-profit percentage

### Step 4: Run Backtest
1. Select backtest period (All data, Last 3/6/12 months, Custom)
2. View results:
   - Key metrics (Equity, Return, Sharpe, etc.)
   - Performance charts (Equity curve, Drawdown)
   - Trade log with entry/exit points
   - Detailed signal data

### Step 5: Optimize Parameters (Optional)
1. Check "Run Parameter Optimization"
2. App will search combinations and rank by return
3. View top 10 parameter sets

### Step 6: Paper Trade (Optional)
1. Get API keys from [Binance Testnet](https://testnet.binance.vision)
2. Enter API credentials in sidebar
3. Click "Start Paper Trader"
4. Monitor live signals and simulated orders

### Step 7: Export Results
1. Click "Export Backtest Results as JSON"
2. Download detailed backtest data for analysis

## CSV Format

If using Upload CSV option, ensure your file has these columns:

```csv
date,open,high,low,close,volume
2023-01-01 00:00:00,16500.00,16650.00,16450.00,16600.00,1234.56
2023-01-01 01:00:00,16600.00,16750.00,16550.00,16700.00,1345.67
```

## Strategy Details

### SMA Crossover
- **Signal**: Buy when SMA(short) > SMA(long), Sell when SMA(short) < SMA(long)
- **Best for**: Trending markets
- **Parameters**: SMA periods (typically 10/30 or 20/50)

### RSI Overbought/Sold
- **Signal**: Buy when RSI < Oversold (default 30), Sell when RSI > Overbought (default 70)
- **Best for**: Range-bound markets
- **Parameters**: RSI period (typically 14)

### MACD
- **Signal**: Buy when MACD > Signal line, Sell when MACD < Signal line
- **Best for**: Momentum trends
- **Parameters**: Fast (12), Slow (26), Signal (9)

### Bollinger Bands
- **Signal**: Buy at lower band, Sell at upper band
- **Best for**: Mean reversion
- **Parameters**: Period (20), Standard deviations (2.0)

### Hybrid (SMA + RSI)
- **Signal**: Buy only when SMA shows uptrend AND RSI shows oversold
- **Best for**: Filtered entries with confluence
- **Parameters**: Both SMA and RSI parameters

## API Keys (Paper Trading)

1. Visit [Binance Testnet](https://testnet.binance.vision)
2. Create an account
3. Generate API Key and Secret
4. Enter in NovaQuant sidebar
5. Start paper trading on testnet

## Performance Metrics Explained

- **Total Return %**: Overall profit/loss percentage
- **Annual Return %**: Extrapolated yearly return
- **Sharpe Ratio**: Risk-adjusted returns (higher is better, >1 is good)
- **Max Drawdown %**: Largest decline from peak (lower is better)
- **Win Rate %**: Percentage of winning trades
- **Profit Factor**: Gross profit / Gross loss ratio (>1 is profitable)
- **Volatility %**: Standard deviation of returns
- **Total Trades**: Number of buy/sell signals generated

## Limitations & Disclaimers

⚠️ **Important:**
- This is an educational tool. Use **testnet/paper accounts only**.
- Backtests use historical data and may not reflect future performance.
- No transaction costs, slippage, or fees are modeled.
- Paper trading uses placeholder position sizing (0.001).
- Always implement proper risk management and position sizing.
- Past performance does not guarantee future results.

## Roadmap

- [ ] Real order execution with proper position sizing
- [ ] Multiple timeframe analysis
- [ ] ML-based signal generation
- [ ] Portfolio optimization (Markowitz)
- [ ] Options strategies
- [ ] Risk-on/off indicators
- [ ] API for external signals
- [ ] Database logging for trade history

## Troubleshooting

### App won't start
```bash
# Check Python version (requires 3.8+)
python --version

# Reinstall dependencies
pip install -r requirements.txt --force-reinstall

# Clear Streamlit cache
streamlit cache clear
```

### CCXT connection errors
- Ensure internet connection is active
- Check Binance testnet status
- Verify API keys are correct

### CSV upload issues
- Check column names match: date, open, high, low, close, volume
- Ensure date format is ISO 8601 (YYYY-MM-DD HH:MM:SS)
- No missing values in price columns

## Contributing

Contributions welcome! Please:
1. Fork the repository
2. Create a feature branch
3. Commit changes
4. Push to branch
5. Open a Pull Request

## License

MIT License - see LICENSE file for details

## Support

For issues, questions, or suggestions:
- Open an [Issue](https://github.com/kasuntharaka078-2/NovaQuant/issues)
- Start a [Discussion](https://github.com/kasuntharaka078-2/NovaQuant/discussions)

---

**Built with ❤️ using Streamlit, Pandas, and CCXT**
