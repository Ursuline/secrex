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
        self._buffer = self._config.get_buffer()
        self._period_range = self._config.get_periods()
        self._ema = self._config.get_ema()
        self._sma = self._config.get_sma()
        self._mad = self._config.get_mad()
        self._mad_buy_signals = None
        self._mad_sell_signals = None

        self._strategy = self._config.get_strategy()
        assert self._strategy == "long", (
            f"Only long strategy implemented | Class {self.__class__.__name__}"
        )

        self._build_derived_data()
        # Perform MAD analysis if requested
        if self._mad:
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


    def _build_MAD(self):
        """Perform MAD analysis"""
        symbol = self._request.get_ticker()
        short_window = self._config.get_short_MAD()
        long_window = self._config.get_long_MAD()
        assert (
            short_window < long_window
        ), f"Short MAD window {short_window} >= long MAD window {long_window}"
        # Calculate the 21-day and 200-day moving averages
        ts = pd.DataFrame(index = self._time_series.index)
        ts["SHORT_MAD"] = (
            self._time_series["adj_close"].rolling(window = short_window).mean()
        )
        ts["LONG_MAD"] = (
            self._time_series["adj_close"].rolling(window = long_window).mean()
        )
        # Calculate the Moving Average Distance (MAD)
        ts["MAD"] = ts["SHORT_MAD"] - ts["LONG_MAD"]
        #Implement a basic trading strategy based on MAD
        #Buy signal: When the 21-day MA crosses above the 200-day MA ("Golden Cross").
        #Sell signal: When the 21-day MA crosses below the 200-day MA ("Death Cross").
        # Create buy and sell signals
        ts["MAD_Signal"] = np.where(ts["SHORT_MAD"] > ts["LONG_MAD"], 1, 0)
        ts["MAD_Position"] = ts["MAD_Signal"].diff()  # 1 indicates buy, -1 indicates sell

        # Filter buy and sell signals
        self._mad_buy_signals = ts[ts["MAD_Position"] == 1]
        self._mad_sell_signals = ts[ts["MAD_Position"] == -1]


        # backtest the strategy by calculating cumulative returns based on the buy and sell signals.
        # Assume starting capital of $1000
        initial_capital = 1000
        ts["Daily_Return"] = self._time_series["adj_close"].pct_change()
        ts["Strategy_Return"] = ts["Daily_Return"] * ts["MAD_Signal"].shift(1)

        # Calculate cumulative returns for strategy and buy-and-hold
        ts["Cumulative_Strategy_Return"] = (
            1 + ts["Strategy_Return"]
        ).cumprod() * initial_capital
        ts["Cumulative_Buy_Hold_Return"] = (
            1 + ts["Daily_Return"]
        ).cumprod() * initial_capital

        # Prepare traces for the strategy and buy-and-hold performance
        strategy_trace = go.Scatter(
            x=ts.index,
            y=ts["Cumulative_Strategy_Return"],
            mode="lines",
            name="MAD Strategy",
            line=dict(color="blue"),
        )

        buy_hold_trace = go.Scatter(
            x=ts.index,
            y=ts["Cumulative_Buy_Hold_Return"],
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

        return ts


    @time_util.timing_decorator
    def _build_derived_data(self):
        """
        Builds and joins moving averages, buffers, zones, positions, and recommendations
        1. build_moving_average MA
        2. build_buffers around MA
        3. build_zone: determine the zone in which the close is located
        4. build_positions to determine required position in the zone
        5. build recommendations to determine recommended action to hold position
        """

        def _build_moving_average(col_name:str, ma_type:str, per:int):
            """
            Builds moving average column for a given period per
            Input:
                - col_name: required MA column name
                - ma_type (str) : exponential MA / exponential or simple or both
                                simple MA / False (change this)
                - per (int) : MA period/span
            """
            # Instantiate a dataframe with the same date indices as the original dataframe
            assert (ma_type.lower() in MOVING_AVGS), f'MA type {ma_type} not in {MOVING_AVGS}'
            ts = pd.DataFrame(index = self._time_series.index)

            if ma_type in [MOVING_AVGS[0], MOVING_AVGS[2]]: # Exponential MA
                # Build exponential moving average column
                ts[col_name] = self._time_series['adj_close'].ewm(span = per,
                                                                  adjust = False).mean()
            elif ma_type in [MOVING_AVGS[1], MOVING_AVGS[2]]: # Simple MA
                # Build simple moving average column
                ts[col_name] = self._time_series['adj_close'].rolling(window = per,
                                                                      min_periods = 1).mean()
            return ts


        def _build_ma_differential(col_name:str, per:int):
            """Builds EMA-SMA column

            Args:
                col_name (str): output column name
                per (int): period
            """
            ts = pd.DataFrame(index = self._time_series.index)
            ts[col_name] = self._time_series[f'EMA_{per}'] - self._time_series[f'SMA_{per}']
            return ts


        def _build_buffers(root_name:str):
            """
            Build EMA column with buffers :
            Root name should be EMA_period
            Nomenclature:
            EMA_i_+ = EMA_i + buffer
            EMA_i_- = EMA_i - buffer
            REM: the buffer is a %age of the adjusted_close
            """
            # Instantiate a dataframe with the same date indices as the original dataframe
            ts = pd.DataFrame(index = self._time_series.index)

            # Create column with added buffer
            ts[f'{root_name}_+'] = (1 + self._buffer) * self._time_series[root_name]

            # Create column with subtracted buffer
            ts[f'{root_name}_-'] = (1 - self._buffer) * self._time_series[root_name]
            return ts


        def _build_zone(period:int):
            """
            Build zone column where close is :
                - Above buffer+ : ZONES[0] = High
                - Beneath buffer- : ZONES[1] = Low
                - In buffer zone: ZONES[2] = Mid
            NB: the zone column is strategy-independent
            """
            ts = self._time_series
            rec_frame = pd.DataFrame(index = ts.index)

            conditions = [(ts['adj_close'] >= ts[f'EMA_{period}_+']),
                          (ts['adj_close'] <= ts[f'EMA_{period}_-']),
                          ]
            options = [ZONES[0], ZONES[1]]
            rec_frame[f'Z_{period}'] = np.select(conditions, options, ZONES[2])
            return rec_frame


        def _build_position(period:int):
            """
            Build required position column given the zone and the strategy
            Long position -> POSITIONS[0] = Long
            Short position -> POSITIONS[1] = Shrt
            Sideline -> POSITIONS[2] = Side
            """
            ts = self._time_series
            rec_frame = pd.DataFrame(index = ts.index)
            conditions = [(ts[f'Z_{period}'] == ZONES[0]),
                          (ts[f'Z_{period}'] == ZONES[1]),
                          ]
            if self._strategy == 'long':
                options = [POSITIONS[0], POSITIONS[2]]
            elif self._strategy == 'short':
                options = [POSITIONS[1], POSITIONS[2]]
            else:
                sys_util.terminate(f'strategy {self._strategy} not implemented',
                                   None, self.__class__, sys._getframe()
                                   )

            rec_frame[f'Pos_{period}_{self._strategy}'] = np.select(conditions, options, '')

            # Set first value to side (ie sitting out)
            rec_frame.iat[0, 0] = POSITIONS[2]

            #Loop over rows
            for row in range(1, rec_frame.shape[0]):
                if rec_frame.iat[row, 0] == '':
                    rec_frame.iat[row, 0] = rec_frame.iat[row - 1, 0]
            return rec_frame


        def _build_recommendation(period:int):
            """
            Build recommendation column from position column
            Strategy-independent
            """
            ts = self._time_series
            rec_frame = pd.DataFrame(columns = [f'R_{period}_{self._strategy}'],
                                     index = ts.index
                                     )
            #First day is Hold
            rec_frame.iat[0, 0] = RECOMMENDATIONS[2]
            for row in range(1, rec_frame.shape[0]):
                previous_pos = ts.loc[ts.index[row - 1], f'Pos_{period}_{self._strategy}']
                current_pos = ts.loc[ts.index[row], f'Pos_{period}_{self._strategy}']

                if previous_pos == current_pos:
                    # If position hasn't changed, recommend to Hold
                    rec_frame.iat[row, 0] = RECOMMENDATIONS[2]
                else:
                    # previous 'Side', current 'Long': Buy
                    if previous_pos == POSITIONS[2] and current_pos == POSITIONS[0]:
                        rec_frame.iat[row, 0] = RECOMMENDATIONS[0]
                    # previous 'Short', current 'Long': Buy
                    elif previous_pos == POSITIONS[1] and current_pos == POSITIONS[0]:
                        rec_frame.iat[row, 0] = RECOMMENDATIONS[0]
                    # previous 'Side', current 'Short': Buy
                    elif previous_pos == POSITIONS[2] and current_pos == POSITIONS[1]:
                        rec_frame.iat[row, 0] = RECOMMENDATIONS[1]
                    # previous 'Short', current 'Side': Buy
                    elif previous_pos == POSITIONS[1] and current_pos == POSITIONS[2]:
                        rec_frame.iat[row, 0] = RECOMMENDATIONS[2]
                    # previous 'Log', current 'Short': Sell
                    elif previous_pos == POSITIONS[0] and current_pos == POSITIONS[1]:
                        rec_frame.iat[row, 0] = RECOMMENDATIONS[1]
                    # previous 'Log', current 'Side': Sell
                    elif previous_pos == POSITIONS[0] and current_pos == POSITIONS[2]:
                        rec_frame.iat[row, 0] = RECOMMENDATIONS[1]
                    else:
                        sys_util.terminate(f'Logic error row {row}', None, self.__class__, sys._getframe())

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
        # Build a scaled spread column
        try:
            factor = ts['adjusted_close'].median() / ts['spread'].median()
        except ZeroDivisionError as e:
            sys_util.terminate('median spread is zero',
                                e, self.__class__, sys._getframe()
                                )
        else:
            ts['scaled_spread'] = ts['spread'] * factor

        # Build a scaled volume column
        try:
            factor = ts['volume'].median() / ts['adjusted_close'].median()
            assert factor != 0, "median volume is zero"
        except ZeroDivisionError as e:
            sys_util.terminate('median close is zero',
                                e, self.__class__, sys._getframe()
                                )
        else:
            ts['scaled_volume'] = ts['volume'] / factor


    def _cleanup(self):
        """
        Removes unnecessary columns from dataframe
        """
        # remove all Z columns:
        z_cols = [ f'Z_{per}' for per in range(self._period_range['min'], self._period_range['max'] + 1) ]
        try:
            self._time_series.drop(columns = z_cols, inplace = True)
        except BaseException as e:
            sys_util.warning(f'Could not drop columns {z_cols}', e, self.__class__.__func__, sys._getframe())


    def _reorder(self):
        """Utility to reverse dataframe order (start-to-end)"""
        self._time_series = self._time_series.iloc[::-1]
