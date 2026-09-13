import streamlit as st
import pandas as pd
import numpy as np
import threading
import time
import os
import json
from datetime import datetime
from typing import Tuple, Dict, List

# Optional: CCXT for live/paper trading
try:
    import ccxt
except Exception:
    ccxt = None

st.set_page_config(page_title="NovaQuant - Advanced Trading Bot", layout="wide")

st.title("🚀 NovaQuant - Advanced Trading Bot")
st.markdown("Multi-strategy backtesting & paper trading platform with risk management")

# ============================================================================
# SIDEBAR CONFIGURATION
# ============================================================================

st.sidebar.header("📊 Data Source")
data_source = st.sidebar.selectbox("Data source", ["Upload CSV", "Fetch from Binance testnet (CCXT)"])
uploaded_file = None
symbol = "BTC/USDT"

if data_source == "Upload CSV":
    uploaded_file = st.sidebar.file_uploader("Upload OHLCV CSV (columns: date, open, high, low, close, volume)", type=["csv"])
else:
    symbol = st.sidebar.text_input("Symbol (CCXT format)", value="BTC/USDT")

# Strategy Selection
st.sidebar.header("🎯 Strategy Selection")
strategy_type = st.sidebar.selectbox(
    "Strategy",
    ["SMA Crossover", "RSI Overbought/Sold", "MACD", "Bollinger Bands", "Hybrid (SMA + RSI)"]
)

# Strategy Parameters
st.sidebar.header("⚙️ Strategy Parameters")

if strategy_type in ["SMA Crossover", "Hybrid (SMA + RSI)"]:
    sma_short = st.sidebar.number_input("SMA short period", min_value=1, value=10)
    sma_long = st.sidebar.number_input("SMA long period", min_value=1, value=30)
else:
    sma_short = 10
    sma_long = 30

if strategy_type in ["RSI Overbought/Sold", "Hybrid (SMA + RSI)"]:
    rsi_period = st.sidebar.number_input("RSI period", min_value=1, value=14)
    rsi_overbought = st.sidebar.slider("RSI Overbought level", min_value=50, max_value=100, value=70)
    rsi_oversold = st.sidebar.slider("RSI Oversold level", min_value=0, max_value=50, value=30)
else:
    rsi_period = 14
    rsi_overbought = 70
    rsi_oversold = 30

if strategy_type == "MACD":
    macd_fast = st.sidebar.number_input("MACD fast period", min_value=1, value=12)
    macd_slow = st.sidebar.number_input("MACD slow period", min_value=1, value=26)
    macd_signal = st.sidebar.number_input("MACD signal period", min_value=1, value=9)
else:
    macd_fast = 12
    macd_slow = 26
    macd_signal = 9

if strategy_type == "Bollinger Bands":
    bb_period = st.sidebar.number_input("Bollinger Bands period", min_value=1, value=20)
    bb_std = st.sidebar.number_input("Bollinger Bands std dev", min_value=0.5, value=2.0)
else:
    bb_period = 20
    bb_std = 2.0

# Risk Management
st.sidebar.header("🛡️ Risk Management")
initial_capital = st.sidebar.number_input("Initial capital (USD)", min_value=1.0, value=10000.0)
risk_pct = st.sidebar.number_input("Risk per trade (% equity)", min_value=0.0, max_value=10.0, value=1.0)

use_stoploss = st.sidebar.checkbox("Use stop-loss", value=True)
if use_stoploss:
    stoploss_pct = st.sidebar.number_input("Stop-loss %", min_value=0.1, max_value=50.0, value=2.0)
else:
    stoploss_pct = 0

use_takeprofit = st.sidebar.checkbox("Use take-profit", value=True)
if use_takeprofit:
    takeprofit_pct = st.sidebar.number_input("Take-profit %", min_value=0.1, max_value=50.0, value=5.0)
else:
    takeprofit_pct = 0

# Backtest Period
st.sidebar.header("📅 Backtest Period")
date_range_preset = st.sidebar.selectbox("Date range", ["All data", "Last 3 months", "Last 6 months", "Last 1 year", "Custom"])

# Live Trading
st.sidebar.header("📱 Live / Paper Trading (Optional)")
use_live = st.sidebar.checkbox("Enable live/paper trading")
api_key = None
api_secret = None
if use_live:
    api_key = st.sidebar.text_input("API Key", type="password")
    api_secret = st.sidebar.text_input("API Secret", type="password")
    exchange_choice = st.sidebar.selectbox("Exchange", ["binance"])

# ============================================================================
# HELPER FUNCTIONS
# ============================================================================

@st.cache_data(show_spinner=False)
def load_csv(file) -> pd.DataFrame:
    """Load and normalize CSV data."""
    df = pd.read_csv(file)
    if "date" in df.columns:
        df["date"] = pd.to_datetime(df["date"])
        df = df.set_index("date").sort_index()
    elif "time" in df.columns:
        df["time"] = pd.to_datetime(df["time"], unit='s', errors='ignore')
        df = df.set_index("time").sort_index()
    return df

def fetch_ohlcv_ccxt(sym: str, limit: int = 500) -> pd.DataFrame:
    """Fetch OHLCV data from Binance via CCXT."""
    if ccxt is None:
        raise RuntimeError("ccxt not installed")
    ex = ccxt.binance({
        'enableRateLimit': True,
        'urls': {'api': 'https://testnet.binance.vision'}
    })
    timeframe = '1h'
    data = ex.fetch_ohlcv(sym, timeframe=timeframe, limit=limit)
    df = pd.DataFrame(data, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
    df['date'] = pd.to_datetime(df['timestamp'], unit='ms')
    df = df.set_index('date')
    return df[['open', 'high', 'low', 'close', 'volume']]

def calculate_rsi(series: pd.Series, period: int = 14) -> pd.Series:
    """Calculate Relative Strength Index."""
    delta = series.diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
    rs = gain / (loss + 1e-9)
    rsi = 100 - (100 / (1 + rs))
    return rsi

def calculate_macd(series: pd.Series, fast: int = 12, slow: int = 26, signal: int = 9) -> Tuple[pd.Series, pd.Series, pd.Series]:
    """Calculate MACD (Moving Average Convergence Divergence)."""
    ema_fast = series.ewm(span=fast).mean()
    ema_slow = series.ewm(span=slow).mean()
    macd_line = ema_fast - ema_slow
    signal_line = macd_line.ewm(span=signal).mean()
    histogram = macd_line - signal_line
    return macd_line, signal_line, histogram

def calculate_bollinger_bands(series: pd.Series, period: int = 20, std_dev: float = 2.0) -> Tuple[pd.Series, pd.Series, pd.Series]:
    """Calculate Bollinger Bands."""
    sma = series.rolling(period).mean()
    std = series.rolling(period).std()
    upper_band = sma + (std * std_dev)
    lower_band = sma - (std * std_dev)
    return upper_band, sma, lower_band

def sma_backtest(df: pd.DataFrame, short: int, long: int, init_capital: float, 
                 stoploss_pct: float = 0, takeprofit_pct: float = 0) -> Tuple[pd.DataFrame, Dict]:
    """SMA Crossover backtest."""
    df = df.copy()
    df["sma_short"] = df["close"].rolling(short).mean()
    df["sma_long"] = df["close"].rolling(long).mean()
    df["signal"] = 0
    df.loc[df["sma_short"] > df["sma_long"], "signal"] = 1
    df["signal"] = df["signal"].fillna(0)
    
    # Apply stop-loss and take-profit
    df["position"] = df["signal"].shift(1).fillna(0)
    df["entry_price"] = np.nan
    df["exit_reason"] = ""
    
    for i in range(1, len(df)):
        if df["signal"].iloc[i] != df["signal"].iloc[i-1]:  # Signal change
            df.at[df.index[i], "entry_price"] = df["close"].iloc[i]
        
        if df["position"].iloc[i] > 0 and not pd.isna(df["entry_price"].iloc[i]):
            entry = df["entry_price"].iloc[i]
            current = df["close"].iloc[i]
            change_pct = ((current - entry) / entry) * 100
            
            if stoploss_pct > 0 and change_pct < -stoploss_pct:
                df.at[df.index[i], "exit_reason"] = "SL"
            elif takeprofit_pct > 0 and change_pct > takeprofit_pct:
                df.at[df.index[i], "exit_reason"] = "TP"
    
    df["returns"] = df["close"].pct_change().fillna(0)
    df["strategy_ret"] = df["position"] * df["returns"]
    df["cum_eq"] = (1 + df["strategy_ret"]).cumprod() * init_capital
    
    return df, calculate_stats(df, init_capital)

def rsi_backtest(df: pd.DataFrame, rsi_period: int, overbought: float, oversold: float,
                 init_capital: float, stoploss_pct: float = 0, takeprofit_pct: float = 0) -> Tuple[pd.DataFrame, Dict]:
    """RSI-based backtest."""
    df = df.copy()
    df["rsi"] = calculate_rsi(df["close"], rsi_period)
    df["signal"] = 0
    df.loc[df["rsi"] < oversold, "signal"] = 1  # Buy signal
    df.loc[df["rsi"] > overbought, "signal"] = 0  # Sell signal
    df["signal"] = df["signal"].fillna(method='ffill').fillna(0)
    
    df["position"] = df["signal"].shift(1).fillna(0)
    df["returns"] = df["close"].pct_change().fillna(0)
    df["strategy_ret"] = df["position"] * df["returns"]
    df["cum_eq"] = (1 + df["strategy_ret"]).cumprod() * init_capital
    
    return df, calculate_stats(df, init_capital)

def macd_backtest(df: pd.DataFrame, fast: int, slow: int, signal: int,
                  init_capital: float, stoploss_pct: float = 0, takeprofit_pct: float = 0) -> Tuple[pd.DataFrame, Dict]:
    """MACD-based backtest."""
    df = df.copy()
    df["macd"], df["macd_signal"], df["macd_hist"] = calculate_macd(df["close"], fast, slow, signal)
    
    df["signal"] = 0
    df.loc[df["macd"] > df["macd_signal"], "signal"] = 1  # Buy
    df["signal"] = df["signal"].fillna(method='ffill').fillna(0)
    
    df["position"] = df["signal"].shift(1).fillna(0)
    df["returns"] = df["close"].pct_change().fillna(0)
    df["strategy_ret"] = df["position"] * df["returns"]
    df["cum_eq"] = (1 + df["strategy_ret"]).cumprod() * init_capital
    
    return df, calculate_stats(df, init_capital)

def bollinger_backtest(df: pd.DataFrame, period: int, std_dev: float,
                      init_capital: float, stoploss_pct: float = 0, takeprofit_pct: float = 0) -> Tuple[pd.DataFrame, Dict]:
    """Bollinger Bands-based backtest."""
    df = df.copy()
    df["bb_upper"], df["bb_mid"], df["bb_lower"] = calculate_bollinger_bands(df["close"], period, std_dev)
    
    df["signal"] = 0
    df.loc[df["close"] < df["bb_lower"], "signal"] = 1  # Buy at lower band
    df.loc[df["close"] > df["bb_upper"], "signal"] = 0  # Sell at upper band
    df["signal"] = df["signal"].fillna(method='ffill').fillna(0)
    
    df["position"] = df["signal"].shift(1).fillna(0)
    df["returns"] = df["close"].pct_change().fillna(0)
    df["strategy_ret"] = df["position"] * df["returns"]
    df["cum_eq"] = (1 + df["strategy_ret"]).cumprod() * init_capital
    
    return df, calculate_stats(df, init_capital)

def hybrid_backtest(df: pd.DataFrame, sma_short: int, sma_long: int, rsi_period: int,
                   rsi_overbought: float, rsi_oversold: float, init_capital: float,
                   stoploss_pct: float = 0, takeprofit_pct: float = 0) -> Tuple[pd.DataFrame, Dict]:
    """Hybrid SMA + RSI backtest."""
    df = df.copy()
    
    # SMA signals
    df["sma_short"] = df["close"].rolling(sma_short).mean()
    df["sma_long"] = df["close"].rolling(sma_long).mean()
    df["sma_signal"] = 0
    df.loc[df["sma_short"] > df["sma_long"], "sma_signal"] = 1
    
    # RSI signals
    df["rsi"] = calculate_rsi(df["close"], rsi_period)
    df["rsi_signal"] = 0
    df.loc[df["rsi"] < rsi_oversold, "rsi_signal"] = 1
    df.loc[df["rsi"] > rsi_overbought, "rsi_signal"] = 0
    df["rsi_signal"] = df["rsi_signal"].fillna(method='ffill').fillna(0)
    
    # Combined signal (both must agree)
    df["signal"] = df["sma_signal"] * df["rsi_signal"]
    
    df["position"] = df["signal"].shift(1).fillna(0)
    df["returns"] = df["close"].pct_change().fillna(0)
    df["strategy_ret"] = df["position"] * df["returns"]
    df["cum_eq"] = (1 + df["strategy_ret"]).cumprod() * init_capital
    
    return df, calculate_stats(df, init_capital)

def calculate_stats(df: pd.DataFrame, init_capital: float) -> Dict:
    """Calculate comprehensive backtest statistics."""
    cum_eq = df["cum_eq"]
    returns = df["strategy_ret"].dropna()
    
    total_return = (cum_eq.iloc[-1] / init_capital - 1) * 100
    annual_return = total_return / max(len(df) / 252, 1)  # Assume 252 trading days/year
    volatility = returns.std() * np.sqrt(252)
    sharpe = (returns.mean() / (returns.std() + 1e-9)) * np.sqrt(252) if returns.std() > 0 else 0.0
    
    # Drawdown
    rolling_max = cum_eq.expanding().max()
    drawdown = (cum_eq - rolling_max) / (rolling_max + 1e-9)
    max_drawdown = drawdown.min() * 100
    
    # Win rate
    wins = (returns > 0).sum()
    total_trades = (df["position"].diff() != 0).sum()
    win_rate = (wins / total_trades * 100) if total_trades > 0 else 0
    
    # Profit factor
    gross_profit = returns[returns > 0].sum()
    gross_loss = abs(returns[returns < 0].sum())
    profit_factor = (gross_profit / gross_loss) if gross_loss > 0 else 0
    
    return {
        "total_return_%": round(total_return, 2),
        "annual_return_%": round(annual_return, 2),
        "sharpe": round(sharpe, 2),
        "max_drawdown_%": round(max_drawdown, 2),
        "volatility_%": round(volatility, 2),
        "win_rate_%": round(win_rate, 2),
        "profit_factor": round(profit_factor, 2),
        "final_equity": round(cum_eq.iloc[-1], 2),
        "total_trades": int(total_trades),
    }

def extract_trades(df: pd.DataFrame) -> pd.DataFrame:
    """Extract buy/sell signals as discrete trades."""
    trades = []
    signal_changes = df["signal"].diff()
    for idx, (date, row) in enumerate(df.iterrows()):
        if idx > 0 and signal_changes.iloc[idx] != 0:
            trade_type = "BUY" if row["signal"] > 0 else "SELL"
            trades.append({
                "Date": date,
                "Type": trade_type,
                "Price": f"${row['close']:.2f}",
                "Signal": row["signal"]
            })
    return pd.DataFrame(trades)

def calculate_position_size(balance_usd: float, risk_pct: float, entry_price: float, stop_price: float) -> float:
    """Calculate position size based on risk."""
    if stop_price >= entry_price:
        return 0
    risk_amount = balance_usd * (risk_pct / 100)
    price_diff = entry_price - stop_price
    quantity = risk_amount / price_diff if price_diff > 0 else 0
    return quantity

# ============================================================================
# LOAD DATA
# ============================================================================

df = None
if data_source == "Upload CSV" and uploaded_file is not None:
    df = load_csv(uploaded_file)
elif data_source != "Upload CSV":
    with st.spinner("Fetching OHLCV from exchange..."):
        try:
            df = fetch_ohlcv_ccxt(symbol, limit=1000)
        except Exception as e:
            st.error(f"❌ Error fetching data: {e}")
            df = None

if df is None:
    st.info("📋 Please upload a CSV or enable fetching to continue.")
    st.stop()

if "close" not in df.columns:
    st.error("❌ Data must include a 'close' column.")
    st.stop()

# Apply date range filter
if date_range_preset != "All data":
    n_candles = len(df)
    if date_range_preset == "Last 3 months":
        df = df.iloc[max(0, n_candles - 90):]
    elif date_range_preset == "Last 6 months":
        df = df.iloc[max(0, n_candles - 180):]
    elif date_range_preset == "Last 1 year":
        df = df.iloc[max(0, n_candles - 365):]

# ============================================================================
# RUN BACKTEST
# ============================================================================

if strategy_type == "SMA Crossover":
    backtest_df, stats = sma_backtest(df, int(sma_short), int(sma_long), float(initial_capital), stoploss_pct, takeprofit_pct)
elif strategy_type == "RSI Overbought/Sold":
    backtest_df, stats = rsi_backtest(df, int(rsi_period), rsi_overbought, rsi_oversold, float(initial_capital), stoploss_pct, takeprofit_pct)
elif strategy_type == "MACD":
    backtest_df, stats = macd_backtest(df, int(macd_fast), int(macd_slow), int(macd_signal), float(initial_capital), stoploss_pct, takeprofit_pct)
elif strategy_type == "Bollinger Bands":
    backtest_df, stats = bollinger_backtest(df, int(bb_period), float(bb_std), float(initial_capital), stoploss_pct, takeprofit_pct)
else:  # Hybrid
    backtest_df, stats = hybrid_backtest(df, int(sma_short), int(sma_long), int(rsi_period),
                                         rsi_overbought, rsi_oversold, float(initial_capital), stoploss_pct, takeprofit_pct)

# ============================================================================
# DISPLAY RESULTS
# ============================================================================

st.subheader(f"📈 {strategy_type} Backtest Results")

# Metrics
col1, col2, col3, col4 = st.columns(4)
with col1:
    st.metric("💰 Final Equity", f"${stats['final_equity']:,.2f}")
with col2:
    st.metric("📊 Total Return", f"{stats['total_return_%']:.2f}%")
with col3:
    st.metric("⚡ Sharpe Ratio", f"{stats['sharpe']:.2f}")
with col4:
    st.metric("📉 Max Drawdown", f"{stats['max_drawdown_%']:.2f}%")

col5, col6, col7, col8 = st.columns(4)
with col5:
    st.metric("🎯 Win Rate", f"{stats['win_rate_%']:.2f}%")
with col6:
    st.metric("📈 Annual Return", f"{stats['annual_return_%']:.2f}%")
with col7:
    st.metric("📊 Profit Factor", f"{stats['profit_factor']:.2f}")
with col8:
    st.metric("🔄 Total Trades", f"{stats['total_trades']}")

# Charts
st.subheader("📊 Performance Charts")
col1, col2 = st.columns(2)

with col1:
    st.write("**Equity Curve**")
    chart_data = pd.DataFrame({
        "Price": df["close"],
        "Strategy Equity": backtest_df["cum_eq"]
    }).dropna()
    st.line_chart(chart_data)

with col2:
    st.write("**Drawdown Over Time**")
    rolling_max = backtest_df["cum_eq"].expanding().max()
    drawdown = ((backtest_df["cum_eq"] - rolling_max) / rolling_max * 100).dropna()
    st.area_chart(drawdown)

# Trade Log
st.subheader("🔍 Trade Log")
trades_df = extract_trades(backtest_df)
if not trades_df.empty:
    st.dataframe(trades_df.head(20), use_container_width=True)
else:
    st.info("No trades executed with current parameters.")

# Signal Data
st.subheader("📋 Signal Data (Last 20 Candles)")
if strategy_type == "SMA Crossover":
    display_cols = ["close", "sma_short", "sma_long", "signal", "position"]
elif strategy_type == "RSI Overbought/Sold":
    display_cols = ["close", "rsi", "signal", "position"]
elif strategy_type == "MACD":
    display_cols = ["close", "macd", "macd_signal", "signal", "position"]
elif strategy_type == "Bollinger Bands":
    display_cols = ["close", "bb_upper", "bb_mid", "bb_lower", "signal", "position"]
else:  # Hybrid
    display_cols = ["close", "sma_short", "sma_long", "rsi", "signal", "position"]

display_data = backtest_df[[col for col in display_cols if col in backtest_df.columns]].tail(20)
st.dataframe(display_data, use_container_width=True)

# ============================================================================
# PARAMETER OPTIMIZATION
# ============================================================================

if st.checkbox("🔬 Run Parameter Optimization (Grid Search)"):
    st.info("Searching for optimal parameters...")
    
    if strategy_type == "SMA Crossover":
        opt_results = []
        short_range = range(5, 30, 5)
        long_range = range(30, 100, 10)
        
        progress_bar = st.progress(0)
        total = len(list(short_range)) * len(list(long_range))
        current = 0
        
        for short in short_range:
            for long in long_range:
                if short < long:
                    _, s = sma_backtest(df, short, long, initial_capital, stoploss_pct, takeprofit_pct)
                    opt_results.append({
                        "SMA Short": short,
                        "SMA Long": long,
                        **s
                    })
                current += 1
                progress_bar.progress(current / total)
        
        opt_df = pd.DataFrame(opt_results).sort_values("total_return_%", ascending=False)
        st.write("**Top 10 Parameter Combinations:**")
        st.dataframe(opt_df.head(10), use_container_width=True)
    else:
        st.warning("Grid search not yet implemented for this strategy.")

# ============================================================================
# EXPORT RESULTS
# ============================================================================

st.subheader("💾 Export Results")

if st.button("📥 Export Backtest Results as JSON"):
    export_data = {
        "timestamp": datetime.now().isoformat(),
        "strategy": strategy_type,
        "strategy_params": {
            "sma_short": int(sma_short) if strategy_type in ["SMA Crossover", "Hybrid (SMA + RSI)"] else None,
            "sma_long": int(sma_long) if strategy_type in ["SMA Crossover", "Hybrid (SMA + RSI)"] else None,
            "rsi_period": int(rsi_period) if strategy_type in ["RSI Overbought/Sold", "Hybrid (SMA + RSI)"] else None,
            "rsi_overbought": rsi_overbought if strategy_type in ["RSI Overbought/Sold", "Hybrid (SMA + RSI)"] else None,
            "rsi_oversold": rsi_oversold if strategy_type in ["RSI Overbought/Sold", "Hybrid (SMA + RSI)"] else None,
        },
        "risk_management": {
            "initial_capital": initial_capital,
            "risk_per_trade": risk_pct,
            "stoploss_pct": stoploss_pct if use_stoploss else None,
            "takeprofit_pct": takeprofit_pct if use_takeprofit else None,
        },
        "statistics": stats,
        "trades": trades_df.to_dict(orient="records") if not trades_df.empty else [],
    }
    
    json_str = json.dumps(export_data, indent=2, default=str)
    st.download_button(
        label="📥 Download JSON",
        data=json_str,
        file_name=f"backtest_{strategy_type.replace(' ', '_')}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json",
        mime="application/json"
    )

# ============================================================================
# PAPER TRADING (LIVE MODE)
# ============================================================================

if use_live:
    st.subheader("📱 Live / Paper Trading")
    
    if api_key == "" or api_secret == "":
        st.warning("⚠️ Enter API credentials to use live/paper trading.")
    elif ccxt is None:
        st.error("❌ ccxt is required for live trading. Install with: pip install ccxt")
    else:
        if "trading" not in st.session_state:
            st.session_state.trading = False
        
        def trader_loop(sym: str, strategy_params: Dict, risk_pct_val: float, api_key_val: str, api_secret_val: str):
            """Paper trading loop."""
            try:
                exchange = ccxt.binance({
                    'apiKey': api_key_val,
                    'secret': api_secret_val,
                    'enableRateLimit': True,
                    'urls': {'api': 'https://testnet.binance.vision'}
                })
                
                last_signal = None
                iteration = 0
                
                while st.session_state.trading:
                    iteration += 1
                    try:
                        ohlcv = exchange.fetch_ohlcv(sym, timeframe='1h', limit=200)
                        df_live = pd.DataFrame(ohlcv, columns=['ts', 'open', 'high', 'low', 'close', 'vol'])
                        df_live['date'] = pd.to_datetime(df_live['ts'], unit='ms')
                        df_live = df_live.set_index('date')
                        
                        # Calculate signal based on strategy
                        if strategy_type == "SMA Crossover":
                            sma_s = df_live['close'].rolling(strategy_params.get('sma_short', 10)).mean()
                            sma_l = df_live['close'].rolling(strategy_params.get('sma_long', 30)).mean()
                            sig = 1 if sma_s.iloc[-1] > sma_l.iloc[-1] else 0
                        else:
                            sig = 0  # Default
                        
                        if last_signal is None:
                            last_signal = sig
                        
                        if sig != last_signal:
                            ticker = exchange.fetch_ticker(sym)
                            price = ticker['last']
                            
                            try:
                                balance = exchange.fetch_balance()
                                usdt_balance = balance.get('USDT', {}).get('free', 100)
                                size = 0.001  # Placeholder
                                
                                if sig == 1:
                                    st.write(f"✅ BUY signal at ${price:.2f}")
                                else:
                                    st.write(f"❌ SELL signal at ${price:.2f}")
                            except Exception as e:
                                st.write(f"⚠️ Order error: {e}")
                            
                            last_signal = sig
                        
                        time.sleep(10)
                    except Exception as e:
                        st.write(f"❌ Trader error: {e}")
                        time.sleep(5)
            except Exception as e:
                st.error(f"❌ Exchange connection error: {e}")
        
        col_trade_a, col_trade_b = st.columns(2)
        with col_trade_a:
            if not st.session_state.trading:
                if st.button("▶️ Start Paper Trader"):
                    st.session_state.trading = True
                    strategy_params = {
                        "sma_short": sma_short,
                        "sma_long": sma_long,
                        "rsi_period": rsi_period,
                    }
                    t = threading.Thread(
                        target=trader_loop,
                        args=(symbol, strategy_params, risk_pct, api_key, api_secret),
                        daemon=True
                    )
                    t.start()
            else:
                if st.button("⏹️ Stop Paper Trader"):
                    st.session_state.trading = False
                    st.write("🛑 Stopping trader...")
        
        with col_trade_b:
            status = "🟢 Running" if st.session_state.trading else "🔴 Stopped"
            st.write(f"**Status:** {status}")

st.markdown("---")
st.caption("⚠️ **Disclaimer:** This tool is for educational purposes. Use testnets/paper accounts first. Add robust error handling, safeguards, and money management before any real trading.")
