import yfinance as yf
import pandas as pd
import streamlit as st
import plotly.graph_objects as go
import statsmodels.api as sm
import numpy as np

#data fetching
def fetch_stock_data(ticker_symbol, period="1y"):
    ticker = yf.Ticker(ticker_symbol)
    df = ticker.history(period=period)
    df["Daily Return"] = df["Close"].pct_change()
    df["Cumulative Return"] = (1 + df["Daily Return"]).cumprod() - 1
    return df

#page config
st.set_page_config(page_title="Stock Dashboard", layout="wide")
st.title("Stock Factor Dashboard")
st.caption("Analyse and compare global stock returns")

#sidebar
st.sidebar.header("Settings")
symbols_input = st.sidebar.text_input(
    "Enter stock tickers (comma separated)",
    value="AAPL, MSFT, GOOGL"
)
period = st.sidebar.selectbox(
    "Time period",
    options=["6mo", "1y", "2y", "5y"],
    index=1
)

#parse tickers
symbols = [s.strip().upper() for s in symbols_input.split(",") if s.strip()]