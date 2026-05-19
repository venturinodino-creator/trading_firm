import os
import time
from datetime import datetime
import pandas as pd
import streamlit as st
import alpaca_trade_api as tradeapi
import yfinance as yf

# ==========================================
# 1. PAGE SETUP & SECURE CLOUD LOADING
# ==========================================
st.set_page_config(page_title="24/7 Cloud Trading Bot", layout="wide")
st.title("🤖 Autonomous AI Trading Desk")
st.markdown("This terminal runs entirely in the cloud, monitoring and executing trades safely.")

# Check for OpenAI key in secrets FIRST
openai_key_found = False
OPENAI_API_KEY = ""

if "OPENAI_API_KEY" in st.secrets:
    OPENAI_API_KEY = st.secrets["OPENAI_API_KEY"]
    os.environ["OPENAI_API_KEY"] = OPENAI_API_KEY
    openai_key_found = True
elif "openai" in st.secrets and "api_key" in st.secrets["openai"]:
    OPENAI_API_KEY = st.secrets["openai"]["api_key"]
    os.environ["OPENAI_API_KEY"] = OPENAI_API_KEY
    openai_key_found = True

# Syncing Alpaca credentials securely
try:
    ALPACA_KEY = st.secrets["alpaca"]["api_key"]
    ALPACA_SECRET = st.secrets["alpaca"]["api_secret"]
    BASE_URL = st.secrets["alpaca"]["base_url"]
    connection_status = "🟢 Connected Live to Broker Vault"
except Exception:
    connection_status = "🔴 Missing Cloud Secrets Configuration"
    BASE_URL = "https://paper-api.alpaca.markets"

# ==========================================
# SIDEBAR CONFIGURATION & BACKUP API FIELDS
# ==========================================
st.sidebar.markdown(f"**System Status:** {connection_status}")
st.sidebar.markdown("---")
st.sidebar.header("⚙️ Configuration Hub")

# BACKUP INPUT: If secrets fail, let you paste it directly into the UI safely
if not openai_key_found:
    st.sidebar.warning("⚠️ OpenAI Key not found in background Secrets vault.")
    user_pasted_key = st.sidebar.text_input("Enter OpenAI API Key manually:", type="password")
    if user_pasted_key:
        OPENAI_API_KEY = user_pasted_key
        os.environ["OPENAI_API_KEY"] = user_pasted_key
        openai_key_found = True
else:
    st.sidebar.success("🔮 OpenAI Core Engine: Active")

# Strategy Controls
trade_allocation_usd = st.sidebar.number_input("Order Limit ($ USD):", min_value=5.0, max_value=500.0, value=21.50, step=1.0)
ma_trigger_drop = st.sidebar.slider("Trigger Buy Drop (% below MA):", min_value=0.1, max_value=5.0, value=0.5, step=0.1)
trigger_multiplier = 1 - (ma_trigger_drop / 100)

# ==========================================
# 2. STATE STORAGE & LIVE POSITION SYNC
# ==========================================
if 'trade_logs' not in st.session_state:
    st.session_state.trade_logs = []
if 'last_trade_time' not in st.session_state:
    st.session_state.last_trade_time = {}

portfolio_value, account_cash = 100000.00, 100000.00
positions_data = []

if "🟢" in connection_status:
    try:
        api = tradeapi.REST(key_id=ALPACA_KEY, secret_key=ALPACA_SECRET, base_url=BASE_URL, api_version='v2')
        account = api.get_account()
        portfolio_value, account_cash = float(account.equity), float(account.cash)
        
        alpaca_positions = api.list_positions()
        for pos in alpaca_positions:
            if pos.symbol in ["TSLA", "ARKX"]:
                positions_data.append({
                    "Asset": pos.symbol,
                    "Shares Held": pos.qty,
                    "Avg Entry": f"${float(pos.avg_entry_price):.2f}",
                    "Live Market Price": f"${float(pos.current_price):.2f}",
                    "Current Value": f"${float(pos.market_value):.2f}",
                    "P&L": f"${float(pos.unrealized_pl):+.2f}"
                })
    except Exception as err:
        st.sidebar.error(f"Sync Issue: {err}")

# Dashboard Top-level KPI block
m1, m2 = st.columns(2)
m1.metric("Cloud Account Equity", f"${portfolio_value:,.2f}")
m2.metric("Available Liquidity (Cash)", f"${account_cash:,.2f}")

# ==========================================
# 3. LIVE STRATEGY MONITOR LOOP
# ==========================================
st.markdown("---")
st.subheader("⏱️ Live Strategy Monitor Loop")

# Verification Barrier Check
if not openai_key_found:
    st.error("🔒 Target verification paused: Please provide your OpenAI API Key in the sidebar or setup Secrets to re-verify targets.")
else:
    bot_active = st.checkbox("Activate Live Market Scanning Loop", value=False)

    if bot_active and "🟢" in connection_status:
        status_box = st.empty()
        status_box.info("🤖 Bot initialized. Streaming dual data feeds for TSLA & ARKX...")
        
        targets = ["TSLA", "ARKX"]
        card_cols = st.columns(len(targets))
        
        for i, ticker_symbol in enumerate(targets):
            with card_cols[i]:
                try:
                    ticker = yf.Ticker(ticker_symbol)
                    hist = ticker.history(period="5d", interval="1d")
                    
                    if not hist.empty:
                        current_price = float(hist['Close'].iloc[-1])
                        moving_avg = float(hist['Close'].mean())
                        
                        st.markdown(f"### Asset Profile: **{ticker_symbol}**")
                        st.metric(label="Current Price", value=f"${current_price:.2f}", delta=f"5-Day MA: ${moving_avg:.2f}", delta_color="off")
                        
                        now = datetime.now()
                        last_buy = st.session_state.last_trade_time.get(ticker_symbol)
                        cooldown_ok = last_buy is None or (now - last_buy).total_seconds() > 300
                        
                        if current_price < (moving_avg * trigger_multiplier):
                            if cooldown_ok:
                                status_box.warning(f"🚨 {ticker_symbol} threshold breached! Purchasing...")
                                api.submit_order(
                                    symbol=ticker_symbol,
                                    notional=trade_allocation_usd,  
                                    side='buy',
                                    type='market',
                                    time_in_force='day'
                                )
                                st.session_state.last_trade_time[ticker_symbol] = now
                                log_entry = f"[{now.strftime('%H:%M:%S')}] Automated Cloud Buy: Allocated ${trade_allocation_usd:.2f} to {ticker_symbol} at ${current_price:.2f}"
                                st.session_state.trade_logs.append(log_entry)
                                st.success(f"🎯 {ticker_symbol} order securely processed!")
                                time.sleep(1)
                                st.rerun()
                            else:
                                st.info(f"⏳ {ticker_symbol} matches criteria, holding on cooldown.")
                                
                except Exception as loop_error:
                    st.error(f"Error scanning {ticker_symbol}: {loop_error}")
                    
        status_box.success("⚖️ Market Scan Complete: Assets tracking within balanced parameters. Standing by...")
    else:
        st.info("System idling. Check the scanning loop box to start live tracking streams.")

# Displays active holdings
st.markdown("---")
st.subheader("💼 Current Cloud Positions")
if positions_data:
    st.dataframe(pd.DataFrame(positions_data), use_container_width=True)
else:
    st.info("No active TSLA or ARKX holdings tracked currently.")

# Display historical action logs
st.subheader("📜 Bot Activity History Log")
if st.session_state.trade_logs:
    for log in reversed(st.session_state.trade_logs):
        st.text(log)
else:
    st.write("No trade actions executed during this session.")
    