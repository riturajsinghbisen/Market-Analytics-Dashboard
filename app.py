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

# --- quick presets ---
st.sidebar.markdown("**Quick Presets**")
preset_cols = st.sidebar.columns(2)
if preset_cols[0].button("🇺🇸 US Tech", use_container_width=True):
    st.session_state["symbols_input"] = "AAPL, MSFT, GOOGL, NVDA"
if preset_cols[1].button("🇮🇳 Nifty 50", use_container_width=True):
    st.session_state["symbols_input"] = "RELIANCE.NS, TCS.NS, INFY.NS, HDFCBANK.NS"

st.sidebar.markdown("---")

symbols_input = st.sidebar.text_input(
    "Enter stock tickers (comma separated)",
    value=st.session_state.get("symbols_input", "AAPL, MSFT, GOOGL"),
    key="symbols_input"
)

period = st.sidebar.selectbox(
    "Time period",
    options=["6mo", "1y", "2y", "5y"],
    index=1
)

st.sidebar.markdown("---")
st.sidebar.markdown("""
**Indian Stock Examples (.NS suffix)**
- `RELIANCE.NS` — Reliance Industries
- `TCS.NS` — Tata Consultancy
- `INFY.NS` — Infosys
- `HDFCBANK.NS` — HDFC Bank
- `ICICIBANK.NS` — ICICI Bank
- `WIPRO.NS` — Wipro
- `BAJFINANCE.NS` — Bajaj Finance
- `MARUTI.NS` — Maruti Suzuki
""")

#parse tickers
symbols = [s.strip().upper() for s in symbols_input.split(",") if s.strip()]


#fetch all data once and reuse
stock_data = {}
invalid_symbols = []

for symbol in symbols:
    df = fetch_stock_data(symbol, period)
    if df is None or df.empty:
        invalid_symbols.append(symbol)
        st.sidebar.error(f"⚠️ {symbol} not found or no data returned.")
    else:
        stock_data[symbol] = df

valid_symbols = [s for s in symbols if s in stock_data]

if not valid_symbols:
    st.error("No valid tickers found. Please check your input.")
    st.stop()

#fundamentals
st.subheader("Fundamentals")

@st.cache_data(ttl=3600)
def get_fundamentals(symbol):
    ticker = yf.Ticker(symbol)
    info = ticker.info

    # compute Free Cash Flow
    try:
        cf = ticker.cashflow
        fcf = None
        if cf is not None and not cf.empty:
            op_cf_key = [k for k in cf.index if "Operating" in k and "Cash" in k]
            capex_key  = [k for k in cf.index if "Capital" in k]
            if op_cf_key and capex_key:
                op_cf = cf.loc[op_cf_key[0]].iloc[0]
                capex = cf.loc[capex_key[0]].iloc[0]
                fcf   = op_cf + capex
    except Exception:
        fcf = None

    return {
        "Ticker":          symbol,
        "Sector":          info.get("sector", "N/A"),
        "Market Cap":      info.get("marketCap", "N/A"),
        "P/E Ratio":       info.get("trailingPE", "N/A"),
        "PEG Ratio":       info.get("pegRatio", "N/A"),
        "EPS (TTM)":       info.get("trailingEps", "N/A"),
        "ROE":             info.get("returnOnEquity", "N/A"),
        "ROA":             info.get("returnOnAssets", "N/A"),
        "Debt/Equity":     info.get("debtToEquity", "N/A"),
        "Free Cash Flow":  fcf,
        "Revenue Growth":  info.get("revenueGrowth", "N/A"),
        "Earnings Growth": info.get("earningsGrowth", "N/A"),
        "Dividend Yield":  info.get("dividendYield", "N/A"),
        "52w High":        info.get("fiftyTwoWeekHigh", "N/A"),
        "52w Low":         info.get("fiftyTwoWeekLow", "N/A"),
    }


fund_data = []
for symbol in valid_symbols:
    with st.spinner(f"Fetching fundamentals for {symbol}..."):
        try:
            fund_data.append(get_fundamentals(symbol))
        except Exception:
            st.warning(f"⚠️ Could not fetch fundamentals for {symbol} — Yahoo Finance rate limit. Try again in a moment.") 


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

def fmt_ratio(val):
    if val in ("N/A", None): return "N/A"
    try: return round(float(val), 2)
    except: return "N/A"

fund_df["Market Cap"]      = fund_df["Market Cap"].apply(format_market_cap)
fund_df["Free Cash Flow"]  = fund_df["Free Cash Flow"].apply(format_market_cap)
fund_df["Revenue Growth"]  = fund_df["Revenue Growth"].apply(format_pct)
fund_df["Earnings Growth"] = fund_df["Earnings Growth"].apply(format_pct)
fund_df["Dividend Yield"]  = fund_df["Dividend Yield"].apply(format_pct)
fund_df["ROE"]             = fund_df["ROE"].apply(format_pct)
fund_df["ROA"]             = fund_df["ROA"].apply(format_pct)
fund_df["P/E Ratio"]       = fund_df["P/E Ratio"].apply(fmt_ratio)
fund_df["PEG Ratio"]       = fund_df["PEG Ratio"].apply(fmt_ratio)
fund_df["EPS (TTM)"]       = fund_df["EPS (TTM)"].apply(fmt_ratio)
fund_df["Debt/Equity"]     = fund_df["Debt/Equity"].apply(fmt_ratio)

st.dataframe(fund_df, use_container_width=True)
st.caption("Source: Yahoo Finance via yfinance. Data may be delayed.")


# --- candlestick chart ---
st.subheader("Price Chart (Candlestick)")

candle_symbol = st.selectbox("Select ticker for candlestick chart", valid_symbols, key="candle_select")
df_candle = stock_data[candle_symbol]

candle_fig = go.Figure()

candle_fig.add_trace(go.Candlestick(
    x=df_candle.index,
    open=df_candle["Open"],
    high=df_candle["High"],
    low=df_candle["Low"],
    close=df_candle["Close"],
    name="Price",
    increasing_line_color="#26a69a",
    decreasing_line_color="#ef5350",
))

candle_fig.add_trace(go.Bar(
    x=df_candle.index,
    y=df_candle["Volume"],
    name="Volume",
    marker_color="rgba(100,100,200,0.3)",
    yaxis="y2"
))

candle_fig.update_layout(
    height=500,
    xaxis_title="Date",
    yaxis_title="Price",
    yaxis2=dict(
        title="Volume",
        overlaying="y",
        side="right",
        showgrid=False
    ),
    xaxis_rangeslider_visible=False,
    hovermode="x unified",
    title=f"{candle_symbol} — Candlestick Chart"
)

st.plotly_chart(candle_fig, use_container_width=True)


#cumulative return chart
st.subheader("Cumulative Return Over Time")

fig = go.Figure()
for symbol in valid_symbols:
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
for symbol in valid_symbols:
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
for symbol in valid_symbols:
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
for symbol in valid_symbols:
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


#technical indicators
st.subheader("Technical Indicators")

tech_symbol = st.selectbox("Select ticker for technical analysis", valid_symbols, key="tech_select")
df_tech = stock_data[tech_symbol].copy()

#RSI
def compute_rsi(series, window=14):
    delta = series.diff()
    gain = delta.clip(lower=0)
    loss = -delta.clip(upper=0)
    avg_gain = gain.ewm(com=window - 1, min_periods=window).mean()
    avg_loss = loss.ewm(com=window - 1, min_periods=window).mean()
    rs = avg_gain / avg_loss
    return 100 - (100 / (1 + rs))

#MACD
def compute_macd(series, fast=12, slow=26, signal=9):
    ema_fast = series.ewm(span=fast, adjust=False).mean()
    ema_slow = series.ewm(span=slow, adjust=False).mean()
    macd_line = ema_fast - ema_slow
    signal_line = macd_line.ewm(span=signal, adjust=False).mean()
    histogram = macd_line - signal_line
    return macd_line, signal_line, histogram

df_tech["RSI"] = compute_rsi(df_tech["Close"])
df_tech["BB_Mid"] = df_tech["Close"].rolling(20).mean()
df_tech["BB_Upper"] = df_tech["BB_Mid"] + 2 * df_tech["Close"].rolling(20).std()
df_tech["BB_Lower"] = df_tech["BB_Mid"] - 2 * df_tech["Close"].rolling(20).std()
df_tech["MACD"], df_tech["MACD_Signal"], df_tech["MACD_Hist"] = compute_macd(df_tech["Close"])

tech_tab1, tech_tab2, tech_tab3 = st.tabs(["Bollinger Bands", "RSI", "MACD"])

with tech_tab1:
    bb_fig = go.Figure()
    bb_fig.add_trace(go.Scatter(x=df_tech.index, y=df_tech["Close"], name="Close", line=dict(color="#636EFA")))
    bb_fig.add_trace(go.Scatter(x=df_tech.index, y=df_tech["BB_Upper"], name="Upper Band", line=dict(color="#EF553B", dash="dot")))
    bb_fig.add_trace(go.Scatter(x=df_tech.index, y=df_tech["BB_Lower"], name="Lower Band", line=dict(color="#00CC96", dash="dot"), fill="tonexty", fillcolor="rgba(0,204,150,0.05)"))
    bb_fig.add_trace(go.Scatter(x=df_tech.index, y=df_tech["BB_Mid"], name="20-day MA", line=dict(color="gray", dash="dash")))
    bb_fig.update_layout(height=400, hovermode="x unified", yaxis_title="Price", title=f"{tech_symbol} — Bollinger Bands")
    st.plotly_chart(bb_fig, use_container_width=True)
    st.caption("Price touching upper band = potentially overbought. Lower band = potentially oversold.")

with tech_tab2:
    rsi_fig = go.Figure()
    rsi_fig.add_trace(go.Scatter(x=df_tech.index, y=df_tech["RSI"], name="RSI (14)", line=dict(color="#AB63FA")))
    rsi_fig.add_hline(y=70, line_dash="dash", line_color="red", annotation_text="Overbought (70)")
    rsi_fig.add_hline(y=30, line_dash="dash", line_color="green", annotation_text="Oversold (30)")
    rsi_fig.update_layout(height=350, yaxis_title="RSI", yaxis_range=[0, 100], hovermode="x unified", title=f"{tech_symbol} — RSI (14-day)")
    st.plotly_chart(rsi_fig, use_container_width=True)

    last_rsi = df_tech["RSI"].iloc[-1]
    if last_rsi > 70:
        st.error(f"RSI = {last_rsi:.1f} — Overbought zone")
    elif last_rsi < 30:
        st.success(f"RSI = {last_rsi:.1f} — Oversold zone")
    else:
        st.info(f"RSI = {last_rsi:.1f} — Neutral zone")

with tech_tab3:
    macd_fig = go.Figure()
    macd_fig.add_trace(go.Scatter(x=df_tech.index, y=df_tech["MACD"], name="MACD", line=dict(color="#636EFA")))
    macd_fig.add_trace(go.Scatter(x=df_tech.index, y=df_tech["MACD_Signal"], name="Signal", line=dict(color="#EF553B")))
    macd_fig.add_trace(go.Bar(x=df_tech.index, y=df_tech["MACD_Hist"], name="Histogram",
        marker_color=["#26a69a" if v >= 0 else "#ef5350" for v in df_tech["MACD_Hist"]]))
    macd_fig.update_layout(height=400, hovermode="x unified", yaxis_title="MACD", title=f"{tech_symbol} — MACD (12/26/9)")
    st.plotly_chart(macd_fig, use_container_width=True)
    st.caption("MACD crossing above signal line = bullish. Below = bearish.")


#portfolio analysis
st.subheader("Portfolio Analysis")
st.caption("Assign weights to each stock and analyse combined portfolio performance.")

if len(valid_symbols) >= 2:
    st.markdown("**Set portfolio weights (must sum to 100%)**")

    weight_cols = st.columns(len(valid_symbols))
    weights_input = {}
    default_weight = round(100 / len(valid_symbols), 1)

    for i, symbol in enumerate(valid_symbols):
        with weight_cols[i]:
            weights_input[symbol] = st.number_input(
                f"{symbol} (%)", min_value=0.0, max_value=100.0,
                value=default_weight, step=1.0, key=f"weight_{symbol}"
            )

    total_weight = sum(weights_input.values())
    st.caption(f"Total weight: **{total_weight:.1f}%** {'✅' if abs(total_weight - 100) < 0.1 else '⚠️ must equal 100%'}")

    if abs(total_weight - 100) < 0.1:
        weights = {s: weights_input[s] / 100 for s in valid_symbols}

        port_returns = pd.DataFrame({s: stock_data[s]["Daily Return"] for s in valid_symbols}).dropna()
        port_weights = np.array([weights[s] for s in valid_symbols])

        portfolio_daily_return = port_returns.values @ port_weights
        portfolio_series = pd.Series(portfolio_daily_return, index=port_returns.index)

        port_cumulative = (1 + portfolio_series).cumprod() - 1
        port_volatility = portfolio_series.std() * np.sqrt(252) * 100
        port_total_return = port_cumulative.iloc[-1] * 100
        port_sharpe = sharpe_ratio(portfolio_series)
        port_dd = max_drawdown(portfolio_series) * 100

        m1, m2, m3, m4 = st.columns(4)
        m1.metric("Total Return", f"{port_total_return:.2f}%")
        m2.metric("Annual Volatility", f"{port_volatility:.2f}%")
        m3.metric("Sharpe Ratio", f"{port_sharpe:.2f}")
        m4.metric("Max Drawdown", f"{port_dd:.2f}%")

        port_fig = go.Figure()
        port_fig.add_trace(go.Scatter(
            x=port_cumulative.index,
            y=(port_cumulative * 100).round(2),
            name="Portfolio",
            mode="lines",
            line=dict(color="white", width=2.5, dash="dash")
        ))

        for symbol in valid_symbols:
            df_s = stock_data[symbol]
            port_fig.add_trace(go.Scatter(
                x=df_s.index,
                y=(df_s["Cumulative Return"] * 100).round(2),
                name=f"{symbol} ({weights_input[symbol]:.0f}%)",
                mode="lines",
                line=dict(width=1.2)
            ))

        port_fig.update_layout(
            height=420,
            yaxis_title="Cumulative Return (%)",
            xaxis_title="Date",
            hovermode="x unified",
            title="Portfolio vs Individual Stocks"
        )
        st.plotly_chart(port_fig, use_container_width=True)

        pie_fig = go.Figure(go.Pie(
            labels=valid_symbols,
            values=[weights_input[s] for s in valid_symbols],
            hole=0.4
        ))
        pie_fig.update_layout(height=300, title="Portfolio Allocation")
        st.plotly_chart(pie_fig, use_container_width=True)
else:
    st.info("Add at least 2 tickers in the sidebar to use Portfolio Analysis.")


#factor analysis
st.subheader("Factor Analysis (OLS Regression)")

# use Indian market proxy if all stocks are Indian
if all(".NS" in s or ".BO" in s for s in valid_symbols):
    market_proxy = "^NSEI"  # Nifty 50 index
else:
    market_proxy = "SPY"

spy_df = fetch_stock_data(market_proxy, period)
if spy_df is None or spy_df.empty:
    spy_df = fetch_stock_data("SPY", period)
    market_proxy = "SPY"

spy_returns = spy_df["Daily Return"].dropna()

reg_results = []

for symbol in valid_symbols:
    try:
        stock_returns = stock_data[symbol]["Daily Return"].dropna()
        combined = pd.concat([stock_returns, spy_returns], axis=1).dropna()
        combined.columns = ["Stock", "Market"]
        if len(combined) < 10:
            st.warning(f"Not enough data for regression on {symbol}")
            continue
        X = sm.add_constant(combined["Market"])
        model = sm.OLS(combined["Stock"], X).fit()
        reg_results.append({
            "Ticker": symbol,
            "Alpha (daily %)": round(model.params["const"] * 100, 4),
            "Beta": round(model.params["Market"], 4),
            "R²": round(model.rsquared, 4),
            "p-value (beta)": round(model.pvalues["Market"], 4),
        })
    except Exception as e:
        st.warning(f"Regression failed for {symbol}: {e}")

st.dataframe(pd.DataFrame(reg_results), use_container_width=True)
if all(".NS" in s or ".BO" in s for s in valid_symbols):
    proxy_name = "^NSEI (Nifty 50)"
else:
    proxy_name = "SPY"
st.caption(f"Regresses each stock's daily return against market proxy ({proxy_name}). Beta > 1 = more volatile than market. Alpha > 0 = outperforming market.")


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
