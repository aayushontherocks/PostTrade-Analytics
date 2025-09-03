import streamlit as st
import pandas as pd
import psycopg2
import matplotlib.pyplot as plt

st.set_page_config(page_title="Trade Monitor", layout="wide")
st.title("🚨Post-Trade Dashboard")

@st.cache_resource
def init_connection():
    return psycopg2.connect(
        host="localhost",        # Changed from "localhost" to Docker service name
        port=5435,            
        dbname="trading_db",
        user="trader",         # Changed from "jupyter" to "trader"
        password="securepass123"  # Changed from "simplepass"
    )

conn = init_connection()

def get_high_risk_failures():
    return pd.read_sql("""
        SELECT trade_id, symbol, quantity, price, value_at_risk, failure_reason
        FROM trades 
        WHERE status = 'FAILED' AND value_at_risk > 1000
        ORDER BY value_at_risk DESC
    """, conn)

def get_settlement_delays():
    return pd.read_sql("""
        SELECT 
            symbol,
            AVG(EXTRACT(DAY FROM (actual_settlement_date - settlement_date))) AS avg_delay_days
        FROM trades
        WHERE actual_settlement_date > settlement_date
        GROUP BY symbol
    """, conn)

st.header("📉 High-Risk Failed Trades")
failures = get_high_risk_failures()
st.dataframe(failures)

st.header("⏰ Settlement Delays by Symbol")
delays = get_settlement_delays()
st.bar_chart(delays.set_index("symbol"))

st.header("📊 Summary Metrics")
col1, col2, col3 = st.columns(3)
col1.metric("Total Failed Trades", len(failures))
col2.metric("Total Value at Risk", f"${failures['value_at_risk'].sum():,.2f}")
col3.metric("Worst Symbol", delays.loc[delays['avg_delay_days'].idxmax()]['symbol'] if not delays.empty else "N/A")

import joblib

@st.cache_resource
def load_model():
    return joblib.load('failure_predictor.pkl')

model = load_model()

st.header("🤖 AI Failure Predictor")
col1, col2, col3, col4 = st.columns(4)

with col1:
    quantity = st.number_input("Quantity", value=100.0, step=50.0)
with col2:
    price = st.number_input("Price", value=150.0, step=10.0)
with col3:
    trade_hour = st.slider("Trade Hour", 0, 23, 9)
with col4:
    trade_dow = st.slider("Day of Week", 0, 6, 0)

# Collect user inputs
quantity = st.number_input("Quantity", min_value=1.0, value=100.0)
price = st.number_input("Price", min_value=1.0, value=150.0)
trade_hour = st.slider("Trade Hour", 0, 23, 10)
trade_dow = st.selectbox("Day of Week", [0,1,2,3,4,5,6])  # 0=Mon

# New input for margin trade (binary)
is_margin_trade = st.selectbox("Is Margin Trade?", [0, 1])

# Match training feature order
features = [[quantity, price, is_margin_trade, trade_hour, trade_dow]]

# Prediction
prediction_proba = model.predict_proba(features)[0][1]
st.metric("Failure Probability", f"{prediction_proba:.2%}")

st.metric("Failure Probability", f"{prediction_proba:.2%}")

if prediction_proba > 0.7:
    st.error("🚨 High failure risk! Consider manual review")
elif prediction_proba > 0.3:
    st.warning("⚠️ Moderate failure risk")
else:
    st.success("✅ Low failure risk")

# Add to your dashboard.py
from trade_analysis import TradeAnalyzer

def show_advanced_analysis():
    analyzer = TradeAnalyzer()
    st.header("📊 Advanced Trade Analysis")
    
    # Show basic stats
    stats = analyzer.basic_stats()
    col1, col2, col3 = st.columns(3)
    col1.metric("Total Trades", stats['total_trades'])
    col2.metric("Failure Rate", f"{stats['failure_rate']:.2%}")
    col3.metric("Total VaR", f"${stats['total_value']:,.2f}")
    
    # Show symbol analysis
    st.subheader("Failure Rates by Symbol")
    symbol_analysis = analyzer.failure_analysis_by_symbol()
    st.dataframe(symbol_analysis.head(10))