#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
frame.py

@author: charles mégnin

The Frame class encapsulates the raw data, ema/sma as required, zones,
positions and recommendations
as well as various other columns for machine learning as necessary
- spread & volume scaled to close for machine learning (unused)
"""
import sys
import numpy as np
import pandas as pd
import config
import request
import utilities.system_utilities as sys_util
import utilities.time_utilities as time_util
import utilities.io_utilities as io_util
#debug
import plotly.graph_objs as go
import plotly.io as pio

ZONES = ['High', 'Low', 'Mid'] # close is above, below or within buffer zone
POSITIONS = ['Long', 'Short', 'Side'] # position to take as a function of the strategy
RECOMMENDATIONS = ['B', 'S', ''] # recommendation necessary to be in required position
MOVING_AVGS = ['exponential', 'simple', 'both']
INITIAL_CAPITAL = 1000 #for back-testing

@time_util.timing_decorator
class Frame:
    """
    The Frame encapsulates the original data from source
    It adds a number of columns to the raw data:
    - moving averages / prefix EMA or SMA
    - buffers around moving average / suffix + or -
    - a zone column Z_period that flags the close as being above, below or within the buffer zone
    - a position column that flags whether the strategy requires a long, short or side position on a given day
    - a recommendation column that flags the action to take on any given day to achieve the position
    - spread and volume scaled to close (not implemented)

    Input:
    - the Config object
    - the original pandas.DataFrame with the filtered raw data

    The constructor _build_derived_data() calls methods to build the data described above
    """
    def __init__(self, conf:config.Config, df:pd.DataFrame, req:request.Request):
        self._config = conf
        self._time_series = df
        self._request = req
        # Set various configuration parameters as variables
        self._debug = self._config.get_debug()
        self._buffers = self._config.get_buffers()
        self._period_range = self._config.get_periods()
        self._ema = self._config.get_ema()
        self._sma = self._config.get_sma()

        self._strategy = self._config.get_strategy()
        assert self._strategy == "long", "Only long strategy implemented"

        self._build_derived_data()
        # Perform MAD analysis if requested
        if self._config.get_mad():
            self._build_MAD()

        self._cleanup()


    #--- GETTERS ---#
    def get_data_frame(self):
        """Return the time series dataframe """
        return self._time_series


    def get_buy_signals(self):
        """Return the buy signals dataframe"""
        return self._mad_buy_signals


    #--- I/O ---#
    def to_csv(self, data_dir:str):
        """Write dataframe to csv file"""
        filename = f'{self._request.get_ticker()}_frame'
        io_util.dataframe_to_csv(self._time_series, data_dir, filename)


    def print_time_series(self):
        """Output time series to stdout"""
        p_display = self._config.get_pandas_display()
        with pd.option_context('display.max_rows', p_display['max_rows'],
                                'display.max_columns', p_display['max_columns'],
                                'display.width', p_display['width'],
                                'display.precision', p_display['precision'],
                                'display.colheader_justify', p_display['colheader_justify']):
            print(self._time_series)


    def _build_MAD(self) -> pd.DataFrame:
        """Perform Moving Average Distance (MAD) analysis and backtest the strategy."""
        symbol = self._request.get_ticker()
        short_window, long_window = self._config.get_short_MAD(), self._config.get_long_MAD()

        # Calculate moving averages
        adj_close = self._time_series["adj_close"]
        ts = pd.DataFrame(index=self._time_series.index)
        ts["SHORT_MAD"] = adj_close.rolling(window=short_window).mean()
        ts["LONG_MAD"] = adj_close.rolling(window=long_window).mean()

        # Calculate MAD and trading signals
        ts["MAD"] = ts["SHORT_MAD"] - ts["LONG_MAD"]
        ts["MAD_Signal"] = (ts["SHORT_MAD"] > ts["LONG_MAD"]).astype(int)
        ts["MAD_Position"] = ts["MAD_Signal"].diff()

        # Identify buy and sell signals
        self._mad_buy_signals = ts.loc[ts["MAD_Position"] == 1]
        self._mad_sell_signals = ts.loc[ts["MAD_Position"] == -1]

        # Backtest strategy
        ts["Daily_Return"] = adj_close.pct_change()
        ts["Strategy_Return"] = ts["Daily_Return"] * ts["MAD_Signal"].shift(1)

        # Compute cumulative returns
        ts["Cumulative_Strategy_Return"] = (1 + ts["Strategy_Return"]).cumprod() * INITIAL_CAPITAL
        ts["Cumulative_Buy_Hold_Return"] = (
            1 + ts["Daily_Return"]
        ).cumprod() * INITIAL_CAPITAL

        # Plot performance
        traces = [
            go.Scatter(x=ts.index, y=ts[col], mode="lines", name=name, line=dict(color=color))
            for col, name, color in [
                ("Cumulative_Strategy_Return", "MAD Strategy", "blue"),
                ("Cumulative_Buy_Hold_Return", "Buy and Hold", "green")
            ]
        ]

        layout = go.Layout(
            title=f"Moving Average Distance Strategy vs Buy and Hold: {symbol}",
            xaxis_title="Date", yaxis_title="Cumulative Returns",
            legend=dict(x=0, y=1), hovermode="x"
        )

        pio.show(go.Figure(data=traces, layout=layout))
        return ts


    @time_util.timing_decorator
    def _build_derived_data(self):
        """
        Builds and joins moving averages, buffers, zones, positions, and recommendations.
        1. build_moving_average MA
        2. build_buffers around MA
        3. build_zone: determine the zone in which the close is located
        4. build_positions to determine required position in the zone
        5. build recommendations to determine recommended action to hold position
        """

        def _build_moving_average(col_name: str, ma_type: str, per: int) -> pd.DataFrame:
            """
            Builds a moving average column for a given period.

            Args:
                col_name (str): Name of the moving average column to create.
                ma_type (str): Type of moving average ('exponential', 'simple', or 'both').
                per (int): Period or span for the moving average.

            Returns:
                pd.DataFrame: DataFrame with the moving average column added.
            """
            ts = pd.DataFrame(index=self._time_series.index)
            # Validate moving average type
            ma_type = ma_type.lower() #??? why remove
            # Handle Exponential Moving Average (EMA) and Simple Moving Average (SMA)
            if ma_type in ["exponential", "both"]:
                ts[col_name] = (self._time_series["adj_close"].ewm(span=per, adjust=False).mean())
            if ma_type in ["simple", "both"]:
                ts[col_name] = (self._time_series["adj_close"].rolling(window=per, min_periods=1).mean())

            return ts


        def _build_ma_differential(col_name: str, per: int) -> pd.DataFrame:
            """Builds EMA-SMA differential column.

            Args:
                col_name (str): Output column name.
                per (int): Period for the moving averages.

            Returns:
                pd.DataFrame: DataFrame with the EMA-SMA differential column.
            """
            ema_col = f"EMA_{per}"
            sma_col = f"SMA_{per}"
            # Ensure both EMA and SMA columns exist before calculating the differential
            if ema_col not in self._time_series or sma_col not in self._time_series:
                raise KeyError(f"Columns '{ema_col}' or '{sma_col}' are missing.")
            ts = pd.DataFrame(index=self._time_series.index)
            ts[col_name] = self._time_series[ema_col] - self._time_series[sma_col]
            return ts


        def _build_buffers(root_name:str) -> pd.DataFrame:
            """
            Build EMA columns with buffers:
            - Root name should be in the format 'EMA_period'.
            - Nomenclature:
                - EMA_i_+ = EMA_i + buffer
                - EMA_i_- = EMA_i - buffer
            REM: the buffer is a %age of the adjusted_close.

            Args:
                root_name (str): The root name for the EMA column (e.g., 'EMA_5').

            Returns:
                pd.DataFrame: DataFrame with EMA columns adjusted by the buffer.
            """
            # Instantiate a dataframe with the same date indices as the original dataframe
            ts = pd.DataFrame(index = self._time_series.index)
            if self._buffers['fixed']:
                # Create the EMA column with the added buffer (EMA_i_+)
                ts[f'{root_name}_+'] = (1 + self._buffers["buffer"]) * self._time_series[root_name]
                # Create the EMA column with the subtracted buffer (EMA_i_-)
                ts[f'{root_name}_-'] = (1 - self._buffers["buffer"]) * self._time_series[root_name]
            else:
                # Handle case where the buffer is not fixed
                sys_util.terminate("3D OF not implemented", None, self.__class__, sys._getframe())
            return ts


        def _build_zone(period: int) -> pd.DataFrame:
            """
            Build zone column where close is:
                - Above buffer+ : ZONES[0] = High
                - Beneath buffer- : ZONES[1] = Low
                - In buffer zone: ZONES[2] = Mid

            Note: The zone column is strategy-independent and is built based on the
                  relationship between the adjusted close and the EMA with buffer.

            Args:
                period (int): The period used for the EMA calculation.

            Returns:
                pd.DataFrame: DataFrame with the zone column.
            """
            ts = self._time_series
            rec_frame = pd.DataFrame(index = ts.index)

            # Define conditions for determining the zone
            conditions = [(ts['adj_close'] >= ts[f'EMA_{period}_+']),
                          (ts['adj_close'] <= ts[f'EMA_{period}_-']),
                          ]
            # Define corresponding zone options
            options = [ZONES[0], ZONES[1]]
            # If neither condition is met, assign Mid zone
            rec_frame[f'Z_{period}'] = np.select(conditions, options, ZONES[2])
            return rec_frame


        def _build_position(period: int) -> pd.DataFrame:
            """
            Build the required position column based on the zone and strategy.

            - Long position -> POSITIONS[0] = Long
            - Short position -> POSITIONS[1] = Shrt
            - Sideline -> POSITIONS[2] = Side

            The position is determined based on whether the close price falls within the
            defined zone and the specified strategy ('long' or 'short').

            Args:
                period (int): The period for which the position is being calculated.

            Returns:
                pd.DataFrame: DataFrame containing the position column.
            """
            ts = self._time_series
            rec_frame = pd.DataFrame(index = ts.index)
            # Define conditions for determining the position based on the zone
            conditions = [(ts[f'Z_{period}'] == ZONES[0]),
                          (ts[f'Z_{period}'] == ZONES[1]),
                          ]
            # Determine position options based on the strategy
            if self._strategy == 'long':
                options = [POSITIONS[0], POSITIONS[2]]  # Long or Sideline
            elif self._strategy == 'short':
                options = [POSITIONS[1], POSITIONS[2]]  # S~hort or Sideline
            else:
                raise ValueError(f"Strategy {self._strategy} not implemented.")
            # Assign position values based on the conditions and strategy
            rec_frame[f'Pos_{period}_{self._strategy}'] = np.select(conditions, options, '')
            # Set first value to 'Sideline' (default state)
            rec_frame.iat[0, 0] = POSITIONS[2]
            # Loop over the rows to propagate the previous row's position where needed
            for row in range(1, rec_frame.shape[0]):
                if rec_frame.iat[row, 0] == '':
                    rec_frame.iat[row, 0] = rec_frame.iat[row - 1, 0]
            return rec_frame


        def _build_recommendation(period: int) -> pd.DataFrame:
            """
            Build recommendation column based on the position column.
            This is strategy-independent and provides recommendations for trading actions:
            - Buy
            - Sell
            - Hold

            Args:
                period (int): The period for which the recommendation is being calculated.

            Returns:
                pd.DataFrame: DataFrame containing the recommendation column.
            """
            ts = self._time_series  # Assuming _time_series is accessible in the context
            rec_frame = pd.DataFrame(columns = [f'R_{period}_{self._strategy}'],
                                     index = ts.index
                                     )
            # The first day is set to 'Hold' (no action taken)
            rec_frame.iat[0, 0] = RECOMMENDATIONS[2]  # 'Hold' recommendation

            long_pos_changes = [ # Logic for Long strategy
                (POSITIONS[2], POSITIONS[0], RECOMMENDATIONS[0]),  # Side -> Long: Buy
                (POSITIONS[2], POSITIONS[1], RECOMMENDATIONS[1]),  # Side -> Short: Sell
                (POSITIONS[2], POSITIONS[2], RECOMMENDATIONS[2]),  # Side -> Side: Hold
                (POSITIONS[1], POSITIONS[0], RECOMMENDATIONS[0]),  # Short -> Long: Buy
                (POSITIONS[1], POSITIONS[1], RECOMMENDATIONS[2]),  # Short -> Short: Hold
                (POSITIONS[1], POSITIONS[2], RECOMMENDATIONS[2]),  # Short -> Side: Hold
                (POSITIONS[0], POSITIONS[0], RECOMMENDATIONS[2]),  # Long -> Long: Hold
                (POSITIONS[0], POSITIONS[1], RECOMMENDATIONS[1]),  # Long -> Short: Sell
                (POSITIONS[0], POSITIONS[2], RECOMMENDATIONS[1]),  # Long -> Side: Sell
            ]

            # Loop through the time series to build the recommendation
            for row in range(1, rec_frame.shape[0]):
                previous_pos = ts.loc[ts.index[row - 1], f'Pos_{period}_{self._strategy}']
                current_pos = ts.loc[ts.index[row], f'Pos_{period}_{self._strategy}']

                for prev, curr, rec in long_pos_changes:
                    if previous_pos == prev and current_pos == curr:
                        rec_frame.iat[row, 0] = rec
                        break
                else:
                    raise ValueError(f"Logic error in recommendation calculation at row {row}")

            # Shift recommendation 1 day (recommendation for the day after close)
            rec_frame[f'R_{period}_{self._strategy}'] = rec_frame[f'R_{period}_{self._strategy}'].shift(1)

            return rec_frame

        # Loop through moving average periodicities:
        for per in range(self._period_range['min'], self._period_range['max'] + 1):
            if self._ema: # Exponential moving average
                # Column names derive from root_name
                root_name = f'EMA_{per}'

                # Aggregate the exponential moving average column to existing dataframe
                self._time_series = self._time_series.join(_build_moving_average(col_name = root_name,
                                                                                 ma_type = MOVING_AVGS[0],
                                                                                 per = per,
                                                                                 ))
                # Build buffers around moving average and aggregate
                self._time_series = self._time_series.join(_build_buffers(root_name = root_name))
                # Aggregate the zone column to existing dataframe
                self._time_series = self._time_series.join(_build_zone(period = per))
                #Aggregate the positio column to existing dataframe
                self._time_series = self._time_series.join(_build_position(period = per))
                #Build recommendation and aggregate
                self._time_series = self._time_series.join(_build_recommendation(period = per))
            if self._sma: # Simple moving average
                col_name = f'SMA_{per}'
                # Aggregate the simple moving average column to existing dataframe
                self._time_series = self._time_series.join(_build_moving_average(col_name = col_name,
                                                                                 ma_type = MOVING_AVGS[1],
                                                                                 per = per))
                col_name = f'EMA-SMA_{per}'
                self._time_series = self._time_series.join(_build_ma_differential(col_name = col_name,
                                                                                  per = per))


    def _engineer(self):
        """
        Perform various post-processing operations:
        - spread scaled to close for ML
        - volume scaled to close for ML
        """
        ts = self._time_series

        def compute_scaled_feature(numerator, denominator, col_name, error_msg):
            """Helper function to compute scaled features safely."""
            median_num, median_den = ts[numerator].median(), ts[denominator].median()

            if median_den == 0:
                sys_util.terminate(error_msg, ValueError(f"{denominator} median is zero"), self.__class__, sys._getframe())

            ts.loc[:, col_name] = ts[numerator] / median_den if "volume" in col_name else ts[numerator] * (median_den / median_num)
        # Build a scaled spread column
        compute_scaled_feature("spread", "adjusted_close", "scaled_spread", "median spread is zero")
        compute_scaled_feature("volume", "adjusted_close", "scaled_volume", "median adjusted_close is zero")


    def _cleanup(self):
        """Remove unnecessary 'Z_*' columns from the dataframe."""
        z_cols = [f'Z_{per}' for per in range(self._period_range['min'], self._period_range['max'] + 1)]
        existing_cols = set(z_cols) & set(self._time_series.columns)

        if existing_cols:
            self._time_series.drop(columns=list(existing_cols), inplace=True)
        else:
            sys_util.warning(
                f"Could not drop columns {z_cols} (some or all do not exist)",
                KeyError(z_cols),
                self.__class__,
                getattr(self, '_cleanup', None)
            )


    def _reorder(self):
        """Utility to reverse dataframe order (start-to-end)"""
        self._time_series = self._time_series.iloc[::-1]
