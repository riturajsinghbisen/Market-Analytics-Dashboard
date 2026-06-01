# 📈 Market Analytics Dashboard

A professional-grade stock analytics dashboard built with **Streamlit**, **yfinance**, **Plotly**, and **Statsmodels**.

> **Live Demo:** https://market-analytics-dashboard-springg.streamlit.app/

---

## Features

### 📊 Charts & Price Analysis
- Candlestick chart with volume bars
- Cumulative return comparison across multiple stocks

### 🧮 Technical Indicators
- Bollinger Bands (20-day MA ± 2σ)
- RSI (14-day) with overbought/oversold signals
- MACD (12/26/9) with coloured histogram

### 📋 Fundamental Metrics
- Market Cap, P/E, PEG Ratio, EPS
- ROE, ROA, Debt/Equity
- Free Cash Flow, Revenue Growth, Dividend Yield

### 📉 Risk Metrics
- Sharpe Ratio, Max Drawdown
- Best and Worst single day return

### 🏦 Portfolio Analysis
- Custom weights per ticker
- Portfolio return, volatility, Sharpe, Max Drawdown
- Portfolio vs individual stocks chart
- Allocation pie chart

### 📐 Factor Analysis (CAPM / OLS)
- Alpha, Beta, R², p-value vs SPY
- Auto switches to Nifty 50 benchmark for Indian stocks

### 📈 Momentum Analysis
- MA20 and MA50 crossover signals
- Bullish/Bearish badge per stock

### 🇮🇳 Indian Stock Support
- Use `.NS` for NSE and `.BO` for BSE
- One-click Nifty 50 preset in sidebar

### ⬇️ Downloads
- CSV export for all major tables

---

## Setup

```bash
git clone https://github.com/riturajsinghbisen/Market-Analytics-Dashboard.git
cd Market-Analytics-Dashboard
pip install -r requirements.txt
streamlit run app.py
```

---

*Data sourced from Yahoo Finance via yfinance. May be delayed.*