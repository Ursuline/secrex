#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import pandas as pd
import plotly.graph_objects as go
from alpha_vantage.timeseries import TimeSeries


class MADAnalysis:
    def __init__(self, ticker, start_date, end_date, api_key):
        """
        Initialize the MADAnalysis class with a stock ticker, date range, and Alpha Vantage API key.
        """
        self.ticker = ticker
        self.start_date = pd.to_datetime(start_date)
        self.end_date = pd.to_datetime(end_date)
        self.api_key = api_key
        self.data = None
        self.moving_averages = {}
        self.mad_data = None

    def download_data(self):
        """
        Download historical stock data using Alpha Vantage.
        Alpha Vantage provides data in the form of a dictionary. We will retrieve the adjusted close prices.
        """
        ts = TimeSeries(key=self.api_key, output_format="pandas")
        # Fetch the daily adjusted stock price data
        data, _ = ts.get_daily_adjusted(symbol=self.ticker, outputsize="full")

        # Keep only the adjusted close price
        self.data = data[["5. adjusted close"]].rename(
            columns={"5. adjusted close": "Close"}
        )

        # Convert index to datetime and filter by start and end dates
        self.data.index = pd.to_datetime(self.data.index)
        self.data = self.data[
            (self.data.index >= self.start_date) & (self.data.index <= self.end_date)
        ]

        return self.data

    def calculate_moving_average(self, window):
        """
        Calculate the moving average for a given window.
        """
        self.data[f"MA_{window}"] = self.data["Close"].rolling(window=window).mean()
        return self.data[f"MA_{window}"]

    def calculate_mad(self, window):
        """
        Calculate the Moving Average Distance (MAD) for a given window.
        """
        self.data[f"MAD_{window}"] = self.data["Close"] - self.data[f"MA_{window}"]
        return self.data[f"MAD_{window}"]

    def calculate_all_mad(self, windows=[50, 100, 200]):
        """
        Calculate MAD for a list of moving average windows.
        """
        for window in windows:
            self.calculate_moving_average(window)
            self.calculate_mad(window)

    def plot_mad(self):
        """
        Plot the closing price and MAD for different windows using Plotly (graph_objects).
        """
        fig = go.Figure()

        # Add the original stock price line
        fig.add_trace(
            go.Scatter(
                x=self.data.index,
                y=self.data["Close"],
                mode="lines",
                name=f"{self.ticker} Close",
                line=dict(color="blue", width=2),
            )
        )

        # Add MAD lines for each window
        for column in self.data.columns:
            if "MAD_" in column:
                fig.add_trace(
                    go.Scatter(
                        x=self.data.index,
                        y=self.data[column],
                        mode="lines",
                        name=column,
                        line=dict(width=1),
                    )
                )

        # Update layout
        fig.update_layout(
            title=f"Moving Average Distance (MAD) for {self.ticker}",
            xaxis_title="Date",
            yaxis_title="Price / MAD",
            template="plotly_dark",
        )

        # Show the plot
        fig.show()

    def plot_correlation(self, window):
        """
        Plot the correlation between the MAD and future returns using Plotly (graph_objects).
        """
        # Calculate future returns (next 10 days as an example)
        self.data["Future Returns"] = self.data["Close"].shift(-10) - self.data["Close"]

        # Calculate correlation
        correlation = self.data[[f"MAD_{window}", "Future Returns"]].corr().iloc[0, 1]

        # Scatter plot for MAD vs. Future Returns
        fig = go.Figure()

        # Add scatter plot
        fig.add_trace(
            go.Scatter(
                x=self.data[f"MAD_{window}"],
                y=self.data["Future Returns"],
                mode="markers",
                name=f"MAD_{window} vs Future Returns",
                marker=dict(size=6, color="red", opacity=0.6),
            )
        )

        # Update layout
        fig.update_layout(
            title=f"MAD vs. Future Returns (Corr: {correlation:.2f})",
            xaxis_title=f"MAD_{window}",
            yaxis_title="Future Returns",
            template="plotly_dark",
        )

        # Show the plot
        fig.show()


if __name__ == "__main__":
    """_summary_
    """
    # Alpha Vantage API Key
    ALPHA_VANTAGE_API_KEY = "your_alpha_vantage_api_key"  # Replace with your API key

    # Instantiate the class
    mad_analysis = MADAnalysis(
        ticker="AAPL",
        start_date="2020-01-01",
        end_date="2024-01-01",
        api_key=ALPHA_VANTAGE_API_KEY,
    )

    # Download the data
    mad_analysis.download_data()

    # Calculate MAD for different windows (e.g., 50-day, 100-day, 200-day)
    mad_analysis.calculate_all_mad([50, 100, 200])

    # Plot the stock price and MAD values
    mad_analysis.plot_mad()

    # Plot the correlation between MAD and future returns for a specific window (e.g., 50-day)
    mad_analysis.plot_correlation(window=50)
