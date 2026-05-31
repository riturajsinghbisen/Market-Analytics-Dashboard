import yfinance as yf
import pandas as pd
import streamlit as st
import plotly.graph_objects as go
import statsmodels.api as sm
import numpy as np

#data fetching
@st.cache_data(ttl=3600)
def fetch_stock_data(ticker_symbol, period="1y"):
    ticker = yf.Ticker(ticker_symbol)
    df = ticker.history(period=period)
    if df.empty:
        return None
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

#risk metrics
st.subheader("Risk Metrics")

def max_drawdown(returns):
    cumulative = (1 + returns).cumprod()
    peak = cumulative.cummax()
    drawdown = (cumulative - peak) / peak
    return drawdown.min()

def sharpe_ratio(returns):
    mean = returns.mean()
    std = returns.std()
    if std == 0:
        return 0
    return round((mean / std) * (252 ** 0.5), 4)

metrics = []
for symbol in symbols:
    df = fetch_stock_data(symbol, period)
    returns = df["Daily Return"].dropna()
    metrics.append({
        "Ticker": symbol,
        "Sharpe Ratio": sharpe_ratio(returns),
        "Max Drawdown (%)": round(max_drawdown(returns) * 100, 2),
        "Best Day (%)": round(returns.max() * 100, 2),
        "Worst Day (%)": round(returns.min() * 100, 2),
    })

st.dataframe(pd.DataFrame(metrics), use_container_width=True)
st.caption("Sharpe > 1.0 is good. Max Drawdown shows worst peak-to-trough loss in the period.")


#correlation heatmap
st.subheader("Correlation Heatmap")
st.caption("How much each stock moves together. Lower correlation = better diversification.")

all_returns = pd.DataFrame()
for symbol in symbols:
    df = fetch_stock_data(symbol, period)
    all_returns[symbol] = df["Daily Return"]

corr_matrix = all_returns.corr().round(2)

heatmap_fig = go.Figure(data=go.Heatmap(
    z=corr_matrix.values,
    x=corr_matrix.columns.tolist(),
    y=corr_matrix.index.tolist(),
    colorscale="RdBu",
    zmid=0, zmin=-1, zmax=1,
    text=corr_matrix.values.round(2),
    texttemplate="%{text}",
    textfont={"size": 14},
    hoverongaps=False
))

heatmap_fig.update_layout(height=350, xaxis_title="", yaxis_title="")
st.plotly_chart(heatmap_fig, use_container_width=True)


#risk vs return scatter
st.subheader("Risk vs Return")

scatter_fig = go.Figure()
for row in summary:
    scatter_fig.add_trace(go.Scatter(
        x=[row["Volatility (std %)"]],
        y=[row["Final Return (%)"]],
        mode="markers+text",
        name=row["Ticker"],
        text=[row["Ticker"]],
        textposition="top center",
        marker=dict(size=14)
    ))

scatter_fig.update_layout(
    xaxis_title="Volatility (Daily Std Dev %)",
    yaxis_title="Total Return (%)",
    height=400,
    showlegend=False
)
scatter_fig.add_hline(y=0, line_dash="dash", line_color="gray", opacity=0.4)
scatter_fig.add_vline(x=0, line_dash="dash", line_color="gray", opacity=0.4)
st.plotly_chart(scatter_fig, use_container_width=True)

#factor analysis
st.subheader("Factor Analysis (OLS Regression)")
st.caption("Regresses each stock's daily return against market proxy (SPY) to estimate beta and alpha.")

spy_df = fetch_stock_data("SPY", period)
spy_returns = spy_df["Daily Return"].dropna()
reg_results = []

for symbol in symbols:
    df = fetch_stock_data(symbol, period)
    stock_returns = df["Daily Return"].dropna()
    combined = pd.concat([stock_returns, spy_returns], axis=1).dropna()
    combined.columns = ["Stock", "Market"]
    X = sm.add_constant(combined["Market"])
    model = sm.OLS(combined["Stock"], X).fit()
    reg_results.append({
        "Ticker": symbol,
        "Alpha (daily %)": round(model.params["const"] * 100, 4),
        "Beta": round(model.params["Market"], 4),
        "R²": round(model.rsquared, 4),
        "p-value (beta)": round(model.pvalues["Market"], 4),
    })

st.dataframe(pd.DataFrame(reg_results), use_container_width=True)
st.caption("Beta > 1 = more volatile than market. Alpha > 0 = outperforming market after adjusting for risk.")


#momentum
st.subheader("Momentum Analysis (Moving Averages)")
st.caption("20-day MA crossing above 50-day MA signals positive momentum.")

momentum_symbol = symbols[0]
df_mom = fetch_stock_data(momentum_symbol, period)
df_mom["MA20"] = df_mom["Close"].rolling(window=20).mean()
df_mom["MA50"] = df_mom["Close"].rolling(window=50).mean()

mom_fig = go.Figure()
mom_fig.add_trace(go.Scatter(
    x=df_mom.index,
    y=df_mom["Close"].round(2),
    name="Close Price",
    mode="lines",
    line=dict(color="#636EFA", width=1.5)
))
mom_fig.add_trace(go.Scatter(
    x=df_mom.index,
    y=df_mom["MA20"].round(2),
    name="20-day MA",
    mode="lines",
    line=dict(color="#EF553B", width=1.5, dash="dot")
))
mom_fig.add_trace(go.Scatter(
    x=df_mom.index,
    y=df_mom["MA50"].round(2),
    name="50-day MA",
    mode="lines",
    line=dict(color="#00CC96", width=1.5, dash="dash")
))

mom_fig.update_layout(
    yaxis_title="Price (USD)",
    xaxis_title="Date",
    hovermode="x unified",
    height=420,
    title=f"{momentum_symbol} — Price and Momentum Indicators"
)
st.plotly_chart(mom_fig, use_container_width=True)

last_ma20 = df_mom["MA20"].iloc[-1]
last_ma50 = df_mom["MA50"].iloc[-1]
if last_ma20 > last_ma50:
    st.success(f"{momentum_symbol}: Bullish — 20-day MA ({last_ma20:.2f}) above 50-day MA ({last_ma50:.2f})")
else:
    st.warning(f"{momentum_symbol}: Bearish — 20-day MA ({last_ma20:.2f}) below 50-day MA ({last_ma50:.2f})")
