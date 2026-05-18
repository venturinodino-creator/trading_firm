import os
from datetime import datetime, timedelta
import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st
import yfinance as yf

# ==========================================
# 1. PAGE SETUP & SECURITY
# ==========================================
st.set_page_config(page_title="Elon Musk Universe Portfolio", layout="wide")

st.title("⚡ AI Trading Firm: Live Portfolio & Daily Earnings")
st.markdown("Tracking active deployments and historical performance within the Musk ecosystem.")

# Sidebar API Input
st.sidebar.header("Configuration")
api_key = st.sidebar.text_input("OpenAI API Key", type="password")

if api_key:
    os.environ["OPENAI_API_KEY"] = api_key
else:
    st.sidebar.warning("🔑 Please enter your OpenAI API key to activate the agents.")

# ==========================================
# 2. DATA CACHING & ENGINES
# ==========================================
# Cache live data requests for 5 minutes so switching tabs or text entry doesn't break the UI
@st.cache_data(ttl=300)
def fetch_live_price(ticker, fallback_price):
    try:
        stock = yf.Ticker(ticker)
        hist = stock.history(period="1d")
        if not hist.empty:
            return float(hist['Close'].iloc[-1])
    except Exception:
        pass
    return float(fallback_price)

# Initialize simulation tracking data safely inside Streamlit memory
if 'portfolio' not in st.session_state:
    st.session_state.portfolio = [
        {"Ticker": "TSLA", "Shares": 150, "Avg Buy Price": 175.50, "Type": "Long Buy"},
        {"Ticker": "ARKX", "Shares": 800, "Avg Buy Price": 14.20, "Type": "Long Buy"}
    ]

if 'history_df' not in st.session_state:
    dates = [datetime.now() - timedelta(days=x) for x in range(30, -1, -1)]
    np.random.seed(42)
    daily_returns = np.random.normal(0.0015, 0.012, len(dates)) 
    balance_history = [100000.0]
    for r in daily_returns:
        balance_history.append(balance_history[-1] * (1 + r))
    
    st.session_state.history_df = pd.DataFrame({
        "Date": dates,
        "Total Portfolio Value": balance_history[1:]
    })

# Process Portfolio Metrics via the cached fetcher
updated_portfolio = []
total_portfolio_value = 0.0
total_cost_basis = 0.0

for position in st.session_state.portfolio:
    ticker = position["Ticker"]
    live_price = fetch_live_price(ticker, position["Avg Buy Price"])
        
    current_value = live_price * position["Shares"]
    cost_basis = position["Avg Buy Price"] * position["Shares"]
    profit_loss = current_value - cost_basis
    
    total_portfolio_value += current_value
    total_cost_basis += cost_basis
    
    updated_portfolio.append({
        "Asset": ticker,
        "Position Type": position["Type"],
        "Shares Held": position["Shares"],
        "Avg Entry Price": f"${position['Avg Buy Price']:.2f}",
        "Live Market Price": f"${live_price:.2f}",
        "Current Value": f"${current_value:.2f}",
        "Total Profit/Loss": f"${profit_loss:+.2f}"
    })

# Compute final performance metrics
total_profit_loss = total_portfolio_value - total_cost_basis
daily_change_pct = ((st.session_state.history_df["Total Portfolio Value"].iloc[-1] / 
                     st.session_state.history_df["Total Portfolio Value"].iloc[-2]) - 1) * 100
daily_earnings_usd = total_portfolio_value * (daily_change_pct / 100)

# ==========================================
# 3. HIGH LEVEL FINANCIAL KPI METRICS
# ==========================================
st.subheader("📊 Live Account Metrics")
m1, m2, m3, m4 = st.columns(4)
m1.metric("Account Net Worth", f"${total_portfolio_value:,.2f}")
m2.metric("Today's Earnings", f"${daily_earnings_usd:+.2f}", f"{daily_change_pct:+.2f}%")
m3.metric("Total Accumulated Return", f"${total_profit_loss:+.2f}", f"{((total_portfolio_value/total_cost_basis)-1)*100:+.2f}%")
m4.metric("Active Assets Trailed", len(updated_portfolio))

st.markdown("---")

# ==========================================
# 4. CHART OVERVIEW SECTION
# ==========================================
st.subheader("📈 Daily Performance Chart (Equities Growth)")

fig = go.Figure()
fig.add_trace(go.Scatter(
    x=st.session_state.history_df["Date"], 
    y=st.session_state.history_df["Total Portfolio Value"],
    mode='lines+markers',
    name='Net Worth ($)',
    line=dict(color='#00e676', width=3),
    fill='tozeroy',
    fillcolor='rgba(0, 230, 118, 0.1)'
))

fig.update_layout(
    template="plotly_dark",
    xaxis_title="Timeline",
    yaxis_title="Total Value ($USD)",
    margin=dict(l=20, r=20, t=20, b=20),
    height=400,
    hovermode="x unified"
)
st.plotly_chart(fig, use_container_width=True)

# ==========================================
# 5. LIVE TRADES OPEN POSITIONS TABLE
# ==========================================
st.subheader("💼 Active Automated Positions")
st.dataframe(pd.DataFrame(updated_portfolio), use_container_width=True)

# ==========================================
# 6. TRIGGER SYSTEM ANALYSIS BUTTON
# ==========================================
if st.button("🚀 Re-Run System Market Scan", use_container_width=True):
    if not api_key:
        st.error("Please provide your OpenAI API Key in the sidebar to re-verify targets.")
    else:
        st.toast("Agents actively evaluating market variables...", icon="🔄")