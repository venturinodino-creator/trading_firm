import os
import time
from datetime import datetime
import pandas as pd
import streamlit as st
import plotly.graph_objects as go
from alpaca.trading.client import TradingClient
from alpaca.trading.requests import MarketOrderRequest, ClosePositionRequest
from alpaca.trading.enums import OrderSide, TimeInForce
import yfinance as yf

# ==========================================
# 1. PREMIUM STYLING & TERMINAL CONFIG
# ==========================================
st.set_page_config(page_title="Hedge Terminal v2.1", layout="wide")

st.markdown("""
    <style>
        .block-container {padding-top: 1.5rem; padding-bottom: 0rem;}
        div[data-testid="stMetricValue"] {font-size: 24px; font-weight: bold; color: #00ffcc;}
        div[data-testid="stMetricLabel"] {font-size: 14px; color: #9aa0a6;}
        .deploy-btn>button {background-color: #00ffcc; color: #0c1017; font-weight: bold; width: 100%; border-radius: 6px;}
        .deploy-btn>button:hover {background-color: #00cc99; color: white;}
        .emergency-btn>button {background-color: #ff3366; color: white; font-weight: bold; width: 100%; border-radius: 6px;}
        .emergency-btn>button:hover {background-color: #cc0033; color: white;}
    </style>
""", unsafe_allow_html=True)

st.title("⚡ QUANTUM: Autonomous Trading Desk")
st.markdown("---")

# Setup state variables
if 'bot_running' not in st.session_state:
    st.session_state.bot_running = False
if 'trade_logs' not in st.session_state:
    st.session_state.trade_logs = []

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

# Initialize Alpaca Client & Metrics
portfolio_value, account_cash = 100000.00, 100000.00
positions_data = []
client = None

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
# 2. SIDEBAR CONFIGURATION
# ==========================================
st.sidebar.subheader("🛡️ SYSTEM SECURITY")
st.sidebar.markdown(f"Core Broker Link: **{connection_status}**")

st.sidebar.markdown("---")
st.sidebar.subheader("⚙️ CONTROL PROTOCOLS")
trade_allocation_usd = st.sidebar.number_input("Per-Order Size ($ USD):", min_value=5.0, max_value=500.0, value=21.50, step=1.0)
ma_trigger_drop = st.sidebar.slider("Trigger Buy Drop (% below MA):", min_value=0.1, max_value=5.0, value=0.5, step=0.1)
trigger_multiplier = 1 - (ma_trigger_drop / 100)

# ==========================================
# 3. MAIN DASHBOARD LIVE METRICS
# ==========================================
col1, col2, col3 = st.columns(3)
col1.metric("Live Portfolio Equity", f"${portfolio_value:,.2f}")
col2.metric("Available Cash Liquidity", f"${account_cash:,.2f}")
col3.metric("Bot Run Status", "RUNNING ALGORITHMS" if st.session_state.bot_running else "SYSTEMS IDLE")

st.markdown("---")

# ==========================================
# 4. STARTING CAPITAL INPUT BAR & ACTIONS
# ==========================================
st.subheader("🛠️ Run Execution Settings")

# Input bar to type exactly how much money you want to hand to the bot
starting_funds_input = st.number_input(
    "Enter Starting Capital Limit for Trading ($ USD):",
    min_value=10.0,
    max_value=float(account_cash),
    value=min(1000.0, float(account_cash)),
    step=50.0,
    help="Type the exact maximum cash balance size you want this session to allocate to your bot."
)

st.write("") # Formatting spacer

# Styled Button Layout Row
c1, c2, c3 = st.columns(3)

with c1:
    st.markdown('<div class="deploy-btn">', unsafe_allow_html=True)
    if st.button("🚀 DEPLOY BOT ENGINE"):
        if "🟢" in connection_status:
            st.session_state.bot_running = True
            st.success(f"Engine locked. Trading allocated up to ${starting_funds_input:.2f}")
            time.sleep(1)
            st.rerun()
        else:
            st.error("Cannot deploy. Link offline.")
    st.markdown('</div>', unsafe_allow_html=True)

with c2:
    if st.button("🛑 PAUSE MONITOR LOOPS"):
        st.session_state.bot_running = False
        st.warning("Automated trading scans temporarily paused.")
        time.sleep(1)
        st.rerun()

with c3:
    st.markdown('<div class="emergency-btn">', unsafe_allow_html=True)
    if st.button("🚨 WITHDRAW & LIQUIDATE ALL"):
        st.session_state.bot_running = False
        if client:
            with st.spinner("Canceling active tracks and converting assets back to cash..."):
                try:
                    # Fetch all tracked open positions and close them immediately via market orders
                    active_positions = client.get_all_positions()
                    closed_count = 0
                    for pos in active_positions:
                        if pos.symbol in ["TSLA", "ARKX"]:
                            client.close_position(pos.symbol)
                            closed_count += 1
                    
                    st.session_state.trade_logs.append(f"[{datetime.now().strftime('%H:%M:%S')}] 🚨 EMERGENCY WITHDRAWAL EXECUTION: Closed {closed_count} tracking positions.")
                    st.success("Withdrawal Complete! All open market positions closed out back to cash.")
                    time.sleep(1.5)
                    st.rerun()
                except Exception as e:
                    st.error(f"Withdrawal Execution Error: {e}")
        else:
            st.error("Broker client connection missing. Unabled to send close trades sequence.")
    st.markdown('</div>', unsafe_allow_html=True)

# Active Strategy Processing Loop Block
if st.session_state.bot_running:
    status_box = st.empty()
    
    current_used_funds = 0.0
    if client:
        try:
            current_positions = client.get_all_positions()
            for p in current_positions:
                if p.symbol in ["TSLA", "ARKX"]:
                    current_used_funds += float(p.market_value)
        except Exception:
            pass
        
    if current_used_funds >= starting_funds_input:
        status_box.warning(f"🛑 Capital Cap Reached: Transacted asset value (${current_used_funds:.2f}) meets your entered input budget limit (${starting_funds_input:.2f}). Scans idling.")
    else:
        status_box.info("🤖 Scanning dual streaming structural targets (TSLA & ARKX)...")
        targets = ["TSLA", "ARKX"]
        for ticker_symbol in targets:
            try:
                hist = yf.Ticker(ticker_symbol).history(period="5d", interval="1d")
                if not hist.empty:
                    current_price = float(hist['Close'].iloc[-1])
                    moving_avg = float(hist['Close'].mean())
                    
                    if current_price < (moving_avg * trigger_multiplier):
                        if (current_used_funds + trade_allocation_usd) <= starting_funds_input:
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

st.markdown("---")

# ==========================================
# 5. CHARTING ENGINE (CANDLESTICK)
# ==========================================
st.subheader("📊 Interactive Market Technical Matrix")
timeframe = st.radio("Select Analytical Timeframe Interval:", ["Daily (24h Window)", "Monthly View", "Yearly View"], horizontal=True)

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
            height=340,
            paper_bgcolor='rgba(0,0,0,0)',
            plot_bgcolor='rgba(0,0,0,0)'
        )
        st.plotly_chart(fig, use_container_width=True)
except Exception as e:
    st.error(f"Error drawing chart components: {e}")

# ==========================================
# 6. PORTFOLIO DATA TABLES & LOGS
# ==========================================
st.markdown("---")
st.subheader("💼 Active Asset Holdings")
if positions_data:
    st.dataframe(pd.DataFrame(positions_data), use_container_width=True)
else:
    st.info("No open target positions currently held in your tracking broker folder.")

if st.session_state.trade_logs:
    st.subheader("📜 Terminal Command History Log")
    for log in reversed(st.session_state.trade_logs):
        st.text(log)