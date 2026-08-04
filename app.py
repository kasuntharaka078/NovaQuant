import streamlit as st
import pandas as pd
import numpy as np
import threading
import time
import os

# Optional: CCXT for live/paper trading
try:
    import ccxt
except Exception:
    ccxt = None

st.set_page_config(page_title="Streamlit Trading Bot (SMA)", layout="wide")

st.title("Simple SMA Trading Bot — Streamlit")

# -- Data input --
st.sidebar.header("Data / Source")
data_source = st.sidebar.selectbox("Data source", ["Upload CSV", "Fetch from Binance testnet (CCXT)"])
uploaded_file = None
symbol = "BTC/USDT"
if data_source == "Upload CSV":
    uploaded_file = st.sidebar.file_uploader("Upload OHLC CSV (columns: date, open, high, low, close, volume)", type=["csv"])
else:
    symbol = st.sidebar.text_input("Symbol (CCXT format)", value="BTC/USDT")

# -- Strategy params --
st.sidebar.header("Strategy params")
sma_short = st.sidebar.number_input("SMA short period", min_value=1, value=10)
sma_long = st.sidebar.number_input("SMA long period", min_value=1, value=30)
initial_capital = st.sidebar.number_input("Initial capital (USD)", min_value=1.0, value=10000.0)
risk_pct = st.sidebar.number_input("Risk per trade (% equity)", min_value=0.0, value=1.0)

# -- Live trading credentials (use testnet) --
st.sidebar.header("Live / Paper trading (optional)")
use_live = st.sidebar.checkbox("Enable live/paper trading")
api_key = st.sidebar.text_input("API Key", type="password")
api_secret = st.sidebar.text_input("API Secret", type="password")
exchange_choice = st.sidebar.selectbox("Exchange", ["binance"])  # extend later

# -- Helper: load data --
@st.cache_data(show_spinner=False)
def load_csv(file) -> pd.DataFrame:
    df = pd.read_csv(file)
    # basic normalization
    if "date" in df.columns:
        df["date"] = pd.to_datetime(df["date"])
        df = df.set_index("date").sort_index()
    elif "time" in df.columns:
        df["time"] = pd.to_datetime(df["time"], unit='s', errors='ignore')
        df = df.set_index("time").sort_index()
    return df

def fetch_ohlcv_ccxt(sym, limit=500):
    if ccxt is None:
        raise RuntimeError("ccxt not installed")
    ex = ccxt.binance({
        'enableRateLimit': True,
        # For testnet use: 'urls': {'api': 'https://testnet.binance.vision'}
    })
    timeframe = '1h'
    data = ex.fetch_ohlcv(sym, timeframe=timeframe, limit=limit)
    df = pd.DataFrame(data, columns=['timestamp','open','high','low','close','volume'])
    df['date'] = pd.to_datetime(df['timestamp'], unit='ms')
    df = df.set_index('date')
    return df

# -- Load data frame --
df = None
if data_source == "Upload CSV" and uploaded_file is not None:
    df = load_csv(uploaded_file)
elif data_source != "Upload CSV":
    with st.spinner("Fetching OHLCV from exchange..."):
        try:
            df = fetch_ohlcv_ccxt(symbol, limit=1000)
        except Exception as e:
            st.error(f"Error fetching data: {e}")
            df = None

if df is None:
    st.info("Please upload a CSV or enable fetching to continue.")
    st.stop()

# Require close column
if "close" not in df.columns:
    st.error("Data must include a 'close' column.")
    st.stop()

# -- Vectorized SMA backtest --
def sma_backtest(df, short, long, init_capital):
    df = df.copy()
    df["sma_short"] = df["close"].rolling(short).mean()
    df["sma_long"] = df["close"].rolling(long).mean()
    df["signal"] = 0
    df.loc[df["sma_short"] > df["sma_long"], "signal"] = 1
    df["signal"] = df["signal"].fillna(0)
    # positions are previous signal (enter at next candle open) — shift to avoid lookahead
    df["position"] = df["signal"].shift(1).fillna(0)
    df["returns"] = df["close"].pct_change().fillna(0)
    df["strategy_ret"] = df["position"] * df["returns"]
    df["cum_eq"] = (1 + df["strategy_ret"]).cumprod() * init_capital
    stats = {
        "final_equity": float(df["cum_eq"].iloc[-1]),
        "total_return_%": float((df["cum_eq"].iloc[-1] / init_capital - 1) * 100),
        "sharpe_approx": float(df["strategy_ret"].mean() / (df["strategy_ret"].std() + 1e-9) * np.sqrt(252)) if df["strategy_ret"].std() != 0 else 0.0
    }
    return df, stats

backtest_df, stats = sma_backtest(df, int(sma_short), int(sma_long), float(initial_capital))

# -- Show results --
st.subheader("Backtest results")
col1, col2 = st.columns([2,1])
with col1:
    st.line_chart(pd.DataFrame({
        "Price": df["close"],
        "Equity": backtest_df["cum_eq"]
    }).dropna())
with col2:
    st.metric("Final equity", f"${stats['final_equity']:.2f}")
    st.metric("Total return", f"{stats['total_return_%']:.2f}%")
    st.metric("Sharpe (approx)", f"{stats['sharpe_approx']:.2f}")

st.markdown("### Signals sample")
st.dataframe(backtest_df[["close","sma_short","sma_long","position"]].tail(20))

# -- Paper trader (simple) --
if use_live:
    if api_key == "" or api_secret == "":
        st.warning("Enter API credentials to use live/paper trading.")
    elif ccxt is None:
        st.error("ccxt is required for live trading (pip install ccxt).")
    else:
        # session control
        if "trading" not in st.session_state:
            st.session_state.trading = False
        def trader_loop(sym, short, long, risk_pct, api_key, api_secret):
            # Configure exchange (example: Binance testnet)
            exchange = ccxt.binance({
                'apiKey': api_key,
                'secret': api_secret,
                'enableRateLimit': True,
                'urls': {'api': 'https://testnet.binance.vision'}
            })
            last_signal = None
            while st.session_state.trading:
                try:
                    ohlcv = exchange.fetch_ohlcv(sym, timeframe='1h', limit=200)
                    df_live = pd.DataFrame(ohlcv, columns=['ts','open','high','low','close','vol'])
                    df_live['date'] = pd.to_datetime(df_live['ts'], unit='ms')
                    df_live = df_live.set_index('date')
                    df_live['sma_short'] = df_live['close'].rolling(short).mean()
                    df_live['sma_long'] = df_live['close'].rolling(long).mean()
                    sig = 1 if df_live['sma_short'].iloc[-1] > df_live['sma_long'].iloc[-1] else 0
                    # Place simple market orders on signal change
                    if last_signal is None:
                        last_signal = sig
                    if sig != last_signal:
                        # Example naive sizing: fixed percent of equity -> quantity calculation requires balances and price
                        ticker = exchange.fetch_ticker(sym)
                        price = ticker['last']
                        # Get USD balance (for spot on testnet this may vary) — this is simplified
                        # Place market buy/sell based on signal
                        size = 0.001  # placeholder: compute based on balance and risk_pct
                        if sig == 1:
                            # Buy market
                            try:
                                order = exchange.create_order(sym, 'market', 'buy', size)
                                st.write(f"Placed BUY order: {order}")
                            except Exception as e:
                                st.write(f"Order failed: {e}")
                        else:
                            try:
                                order = exchange.create_order(sym, 'market', 'sell', size)
                                st.write(f"Placed SELL order: {order}")
                            except Exception as e:
                                st.write(f"Order failed: {e}")
                        last_signal = sig
                    time.sleep(10)  # sleep between polls; adjust to timeframe
                except Exception as e:
                    st.write("Trader error:", e)
                    time.sleep(5)

        colA, colB = st.columns(2)
        with colA:
            if not st.session_state.trading:
                if st.button("Start paper trader"):
                    st.session_state.trading = True
                    t = threading.Thread(target=trader_loop, args=(symbol, int(sma_short), int(sma_long), float(risk_pct), api_key, api_secret), daemon=True)
                    t.start()
            else:
                if st.button("Stop paper trader"):
                    st.session_state.trading = False
                    st.write("Stopping trader...")
        with colB:
            st.write("Live trading status:", "Running" if st.session_state.trading else "Stopped")

st.markdown("---")
st.caption("This example is educational. Use testnets / paper accounts first and add robust error handling, size calculation, and safeguards before any real trading.")