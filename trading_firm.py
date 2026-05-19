import os
import time
from datetime import datetime
import pandas as pd
import streamlit as st
import plotly.graph_objects as go
from alpaca.trading.client import TradingClient
from alpaca.trading.requests import MarketOrderRequest
from alpaca.trading.enums import OrderSide, TimeInForce
import yfinance as yf

# ==========================================
# 1. PREMIUM STYLING & TERMINAL CONFIG
# ==========================================
st.set_page_config(page_title="Hedge Terminal v2.0", layout="wide")

# Custom CSS to inject a clean dark trading desk aesthetic
st.markdown("""
    <style>
        .block-container {padding-top: 1.5rem; padding-bottom: 0rem;}
        div[data-testid="stMetricValue"] {font-size: 24px; font-weight: bold; color: #00ffcc;}
        div[data-testid="stMetricLabel"] {font-size: 14px; color: #9aa0a6;}
        .stButton>button {background-color: #00ffcc; color: #0c1017; font-weight: bold; width: 100%; border-radius: 6px;}
        .stButton>button:hover {background-color: #00cc99; color: white;}
    </style>
""", unsafe_allow_html=True)

st.title("⚡ QUANTUM: Autonomous Trading Desk")
st.markdown("---")

# Secure Cloud Credentials Mapping
openai_key_found = False
if "OPENAI_API_KEY" in st.secrets:
    os.environ["OPENAI_API_KEY"] = st.secrets["OPENAI_API_KEY"]
    openai_key_found = True

try:
    ALPACA_KEY = st.secrets["alpaca"]["api_key"]
    ALPACA_SECRET = st.secrets["alpaca"]["api_secret"]
    BASE_URL = st.secrets["alpaca"]["base_url"]
    is_paper = "paper" in BASE_URL.lower()
    connection_status = "🟢 OPERATIONAL"
except Exception:
    connection_status = "🔴 OFFLINE (Check Secrets)"
    is_paper = True

# Initialize Alpaca client data behind the scenes
portfolio_value, account_cash = 100000.00, 100000.00
positions_data = []

if "🟢" in connection_status:
    try:
        client = TradingClient(api_key=ALPACA_KEY, secret_key=ALPACA_SECRET, paper=is_paper)
        account = client.get_account()
        portfolio_value, account_cash = float(account.equity), float(account.cash)
        
        alpaca_positions = client.get_all_positions()
        for pos in alpaca_positions:
            if pos.symbol in ["TSLA", "ARKX"]:
                positions_data.append({
                    "Asset": pos.symbol,
                    "Shares": pos.qty,
                    "Entry Price": f"${float(pos.avg_entry_price):.2f}",
                    "Market Price": f"${float(pos.current_price):.2f}",
                    "Total Value": f"${float(pos.market_value):.2f}",
                    "P&L": f"${float(pos.unrealized_pl):+.2f}"
                })
    except Exception as err:
        st.sidebar.error(f"Alpaca Sync Error: {err}")

# ==========================================
# 2. SIDEBAR CONFIGURATION (SLIDERS & WIDGETS)
# ==========================================
st.sidebar.subheader("🛡️ SYSTEM SECURITY")
st.sidebar.markdown(f"Core Broker Link: **{connection_status}**")
if openai_key_found:
    st.sidebar.markdown("AI Target Engine: **🟢 ACTIVE**")
else:
    st.sidebar.warning("⚠️ OpenAI Key Missing in Secrets")

st.sidebar.markdown("---")
st.sidebar.subheader("⚙️ CONTROL PROTOCOLS")

# Dynamic Funds Slider: Cap your trading based on your live account balance
max_allocatable_funds = float(portfolio_value)
allocated_trading_limit = st.sidebar.slider(
    "Max Fund Trading Limit ($ USD):",
    min_value=10.0,
    max_value=max_allocatable_funds,
    value=min(2000.0, max_allocatable_funds),
    step=10.0,
    help="Set the absolute maximum ceiling of your cash balance the bot is allowed to access."
)

trade_allocation_usd = st.sidebar.number_input("Per-Order Size ($ USD):", min_value=5.0, max_value=500.0, value=21.50, step=1.0)
ma_trigger_drop = st.sidebar.slider("Trigger Buy Drop (% below MA):", min_value=0.1, max_value=5.0, value=0.5, step=0.1)
trigger_multiplier = 1 - (ma_trigger_drop / 100)

# ==========================================
# 3. LIVE POSITION DASHBOARD (MAIN ROW)
# ==========================================
col1, col2, col3 = st.columns(3)
col1.metric("Live Portfolio Equity", f"${portfolio_value:,.2f}")
col2.metric("Available Cash Liquidity", f"${account_cash:,.2f}")
col3.metric("Bot Capital Ceiling", f"${allocated_trading_limit:,.2f}")

st.markdown("---")

# ==========================================
# 4. CHARTING ENGINE (CANDLESTICK TIMEFRAMES)
# ==========================================
st.subheader("📊 Interactive Market Technical Matrix")

# Multi-timeframe selector buttons
timeframe = st.radio("Select Analytical Timeframe Interval:", ["Daily (24h Window)", "Monthly View", "Yearly View"], horizontal=True)

# Map human selections to precise financial intervals
if timeframe == "Daily (24h Window)":
    yf_period, yf_interval = "1d", "5m"
elif timeframe == "Monthly View":
    yf_period, yf_interval = "1mo", "1h"
else:
    yf_period, yf_interval = "1y", "1d"

selected_chart_ticker = st.selectbox("Select Target Chart Asset:", ["TSLA", "ARKX"])

try:
    chart_data = yf.Ticker(selected_chart_ticker).history(period=yf_period, interval=yf_interval)
    if not chart_data.empty:
        fig = go.Figure(data=[go.Candlestick(
            x=chart_data.index,
            open=chart_data['Open'],
            high=chart_data['High'],
            low=chart_data['Low'],
            close=chart_data['Close'],
            increasing_line_color='#00ffcc', 
            decreasing_line_color='#ff3366'
        )])
        fig.update_layout(
            title=f"Live {selected_chart_ticker} {timeframe} Performance Feed",
            template="plotly_dark",
            xaxis_rangeslider_visible=False,
            height=380,
            paper_bgcolor='rgba(0,0,0,0)',
            plot_bgcolor='rgba(0,0,0,0)'
        )
        st.plotly_chart(fig, use_container_width=True)
except Exception as e:
    st.error(f"Error drawing chart data vectors: {e}")

st.markdown("---")

# ==========================================
# 5. EXECUTION & ACTIVATION CORE BUTTONS
# ==========================================
st.subheader("⚙️ Mainframe Executive Commands")

if 'bot_running' not in st.session_state:
    st.session_state.bot_running = False

c1, c2 = st.columns(2)
with c1:
    if st.button("🚀 DEPLOY BOT ENGINE"):
        if "🟢" in connection_status:
            st.session_state.bot_running = True
            st.success("Mainframe execution sequence locked. Loop initialized.")
        else:
            st.error("Cannot deploy. Connection offline.")

with c2:
    if st.button("🛑 TERMINATE ALL ENGINE LOOPS"):
        st.session_state.bot_running = False
        st.warning("All automated algorithms systematically paused.")

# Active Execution Core Loop Block
if st.session_state.bot_running:
    status_box = st.empty()
    status_box.info("🤖 Executing sequence... Analyzing market standard indices.")
    
    # Check if total position valuation exceeds your custom Slider limit
    current_used_funds = 0.0
    try:
        current_positions = client.get_all_positions()
        for p in current_positions:
            current_used_funds += float(p.market_value)
    except Exception:
        pass
        
    if current_used_funds >= allocated_trading_limit:
        status_box.warning(f"🛑 Safe Cap Triggered: Total used funds (${current_used_funds:.2f}) equal or exceed slider safety ceiling (${allocated_trading_limit:.2f}). Orders paused.")
    else:
        targets = ["TSLA", "ARKX"]
        for ticker_symbol in targets:
            try:
                hist = yf.Ticker(ticker_symbol).history(period="5d", interval="1d")
                if not hist.empty:
                    current_price = float(hist['Close'].iloc[-1])
                    moving_avg = float(hist['Close'].mean())
                    
                    if current_price < (moving_avg * trigger_multiplier):
                        # Final protection check before making the trade
                        if (current_used_funds + trade_allocation_usd) <= allocated_trading_limit:
                            order_data = MarketOrderRequest(
                                symbol=ticker_symbol,
                                notional=trade_allocation_usd,
                                side=OrderSide.BUY,
                                time_in_force=TimeInForce.DAY
                            )
                            client.submit_order(order_data=order_data)
                            st.session_state.trade_logs.append(f"[{datetime.now().strftime('%H:%M:%S')}] Bought {ticker_symbol} at ${current_price:.2f}")
                            st.rerun()
            except Exception as loop_err:
                st.error(f"Execution Error: {loop_err}")
                
        status_box.success("🟢 Monitoring Streams: Target variables balanced within optimal safety levels.")

# ==========================================
# 6. PORTFOLIO DATA TABLES
# ==========================================
st.markdown("---")
st.subheader("💼 Active Asset Holdings")
if positions_data:
    st.dataframe(pd.DataFrame(positions_data), use_container_width=True)
else:
    st.info("No active open stock positions tracked currently.")

if 'trade_logs' in st.session_state and st.session_state.trade_logs:
    st.subheader("📜 Terminal Command History Log")
    for log in reversed(st.session_state.trade_logs):
        st.text(log)