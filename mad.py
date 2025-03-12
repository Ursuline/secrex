#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""ChatGPT Code"""
import numpy as np
from alpha_vantage.timeseries import TimeSeries
import plotly.graph_objs as go
import plotly.io as pio

API_KEY = "your_alpha_vantage_api_key"
symbol = "AAPL"  # Example: Apple stock
ts = TimeSeries(key=API_KEY, output_format="pandas")

# Fetch daily adjusted stock data (this includes adjusted close prices)
data, meta_data = ts.get_daily_adjusted(symbol=symbol, outputsize="full")

# Select the adjusted close price
data = data["5. adjusted close"]
#data = data.sort_index(ascending=True)  # Sort data by date

# Calculate the 21-day and 200-day moving averages
data["SHORT_MAD"] = data.rolling(window=21).mean()
data["LONG_MAD"] = data.rolling(window=200).mean()

# Calculate the Moving Average Distance (MAD)
data["MAD"] = data["SHORT_MAD"] - data["LONG_MAD"]

#Implement a basic trading strategy based on MAD
#Buy signal: When the 21-day MA crosses above the 200-day MA ("Golden Cross").
#Sell signal: When the 21-day MA crosses below the 200-day MA ("Death Cross").
# Create buy and sell signals
data["Signal"] = np.where(data["SHORT_MAD"] > data["LONG_MAD"], 1, 0)
data["Position"] = data["Signal"].diff()  # 1 indicates buy, -1 indicates sell

# Filter buy and sell signals
buy_signals = data[data["Position"] == 1]
sell_signals = data[data["Position"] == -1]

# backtest the strategy by calculating cumulative returns based on the buy and sell signals.
# Assume starting capital of $1000
initial_capital = 1000
data["Daily_Return"] = data["5. adjusted close"].pct_change()
data["Strategy_Return"] = data["Daily_Return"] * data["Signal"].shift(1)

# Calculate cumulative returns for strategy and buy-and-hold
data["Cumulative_Strategy_Return"] = (
    1 + data["Strategy_Return"]
).cumprod() * initial_capital
data["Cumulative_Buy_Hold_Return"] = (
    1 + data["Daily_Return"]
).cumprod() * initial_capital



# Prepare traces for the strategy and buy-and-hold performance
strategy_trace = go.Scatter(
    x=data.index,
    y=data["Cumulative_Strategy_Return"],
    mode="lines",
    name="MAD Strategy",
    line=dict(color="blue"),
)

buy_hold_trace = go.Scatter(
    x=data.index,
    y=data["Cumulative_Buy_Hold_Return"],
    mode="lines",
    name="Buy and Hold",
    line=dict(color="green"),
)

# Create layout
layout = go.Layout(
    title=f"Moving Average Distance Strategy vs Buy and Hold: {symbol}",
    xaxis_title="Date",
    yaxis_title="Cumulative Returns",
    legend=dict(x=0, y=1),
    hovermode="x",
)

# Create the figure
fig = go.Figure(data=[strategy_trace, buy_hold_trace], layout=layout)

# Render the plot
pio.show(fig)
