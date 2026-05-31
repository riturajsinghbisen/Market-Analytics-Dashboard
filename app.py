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