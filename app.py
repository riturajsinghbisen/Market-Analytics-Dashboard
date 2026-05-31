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

#fundamentals
st.subheader("Fundamentals")

def get_fundamentals(symbol):
    ticker = yf.Ticker(symbol)
    info = ticker.info
    return {
        "Ticker": symbol,
        "Market Cap": info.get("marketCap", "N/A"),
        "P/E Ratio": info.get("trailingPE", "N/A"),
        "Revenue Growth": info.get("revenueGrowth", "N/A"),
        "Earnings Growth": info.get("earningsGrowth", "N/A"),
        "Dividend Yield": info.get("dividendYield", "N/A"),
        "52w High": info.get("fiftyTwoWeekHigh", "N/A"),
        "52w Low": info.get("fiftyTwoWeekLow", "N/A"),
        "Sector": info.get("sector", "N/A"),
    }

fund_data = []
for symbol in symbols:
    with st.spinner(f"Fetching fundamentals for {symbol}..."):
        fund_data.append(get_fundamentals(symbol))

fund_df = pd.DataFrame(fund_data)

def format_market_cap(val):
    if val == "N/A":
        return val
    if val >= 1e12:
        return f"${val/1e12:.2f}T"
    if val >= 1e9:
        return f"${val/1e9:.2f}B"
    return f"${val/1e6:.2f}M"

def format_pct(val):
    if val == "N/A" or val is None:
        return "N/A"
    return f"{round(val * 100, 2)}%"

fund_df["Market Cap"] = fund_df["Market Cap"].apply(format_market_cap)
fund_df["Revenue Growth"] = fund_df["Revenue Growth"].apply(format_pct)
fund_df["Earnings Growth"] = fund_df["Earnings Growth"].apply(format_pct)
fund_df["Dividend Yield"] = fund_df["Dividend Yield"].apply(format_pct)
fund_df["P/E Ratio"] = fund_df["P/E Ratio"].apply(
    lambda x: round(x, 2) if x != "N/A" and x is not None else "N/A"
)

st.dataframe(fund_df, use_container_width=True)
st.caption("Source: Yahoo Finance via yfinance. Data may be delayed.")

#cumulative return chart
st.subheader("Cumulative Return Over Time")

fig = go.Figure()
for symbol in symbols:
    with st.spinner(f"Fetching {symbol}..."):
        df = fetch_stock_data(symbol, period)
        fig.add_trace(go.Scatter(
            x=df.index,
            y=(df["Cumulative Return"] * 100).round(2),
            name=symbol,
            mode="lines"
        ))

fig.update_layout(
    yaxis_title="Cumulative Return (%)",
    xaxis_title="Date",
    hovermode="x unified",
    height=450
)
st.plotly_chart(fig, use_container_width=True)

#summary table
st.subheader("Summary")
summary = []
for symbol in symbols:
    df = fetch_stock_data(symbol, period)
    summary.append({
        "Ticker": symbol,
        "Final Return (%)": round(df["Cumulative Return"].iloc[-1] * 100, 2),
        "Avg Daily Return (%)": round(df["Daily Return"].mean() * 100, 4),
        "Volatility (std %)": round(df["Daily Return"].std() * 100, 4),
    })

st.dataframe(pd.DataFrame(summary), use_container_width=True)

