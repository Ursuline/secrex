#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
objective_function.py

@author: charles mégnin

The ObjectiveFunction object relates a set of parameters (periodicity / strategy) to an income (gains)

An optimal parameter is determined by exhaustive exploration but maxima are also calculated to quantify
the uniqueness (ie: stability) of the optimal solution.
"""
import sys
import pandas as pd
import numpy as np
import config
import frame
import request
import utilities.system_utilities as sys_util
import utilities.time_utilities as time_util
import utilities.io_utilities as io_util

OF_COLUMNS = ['period', 'gains']

@time_util.timing_decorator
class ObjectiveFunction:
    """
    The objective function object encapsulates the relationship bw period, optionally buffer, and gains.
    """
    def __init__(self, conf:config.Config, frm:frame.Frame, req:request.Request):
        self._frame_obj = frm # Frame object
        self._data_frame = self._frame_obj.get_data_frame() # time series in Frame object
        self._config = conf
        self._req = req
        self._strategy = self._config.get_strategy()
        self._period = self._config.get_periods()
        self._debug = conf.get_debug()
        # Set various configuration parameters as variables
        self._o_function = None # Objective function
        self._max_df = None # Dataframe of local maxima in _o_function < 1 sdev from max
        self._global_max = None  # maximum gains
        self._global_max_periods = None  # periods at max gain
        self._n_local_max = None  # number of local maxima
        self._nmax_1std = None  # number of local maxima 1 standard deviation from global max (incl. global max)
        self._std_of_local_max = None  # Standard deviation of local maxima
        self._build_objective_function()
        self._build_maxima()
        self._extract_max()

    #--- GETTERS ---#
    def get_objective_function(self) -> pd.DataFrame:
        return self._o_function


    def get_local_maxima(self) -> pd.DataFrame:
        return self._max_df


    def get_of_info(self) -> dict:
        return {'period_at_global_max': self._period_at_global_max,
                'global_max': self._global_max,
                'std_of_local_max': self._std_of_local_max,
                'number_of_periods': self._period['max'] - self._period['min'] + 1,
                'number_of_local_max': self._n_local_max,
                'number_of_max_within_1_sdev': self._nmax_1std,
                }


    def get_global_max(self):
        """Return periods at global max and global max as a tuple."""
        return self._global_max_periods, self._global_max


    #--- CONSTRUCTORS ---#
    @time_util.timing_decorator
    def _build_objective_function(self):
        """
        Builds the objective function from the data frame and the strategy
        So far only a long strategy is considered.
        """
        #--- method utility ---#
        def _sum_tx(df:pd.DataFrame, col:str):
            """Return the value of buys and sells"""
            buys = df.loc[df[col] == 'B', 'adj_close'].sum()
            sells = df.loc[df[col] == 'S', 'adj_close'].sum()
            # Count number of 'B' & 'S' & adds the value of the day's close if nB != nS
            if (df[col] == "B").sum() == (df[col] == "S").sum() + 1:
                # If more B than S (long), use today's close as last value for S
                sells += df["adj_close"].iloc[-1]
            elif (df[col] == "B").sum() + 1 == (df[col] == "S").sum():
                # If more S than B (short), use today's close as last value for B
                buys += df["adj_close"].iloc[-1]
            return buys, sells
        # _build_objective_function() starts here
        of_list = [
            (per,
                (_sum_tx(self._data_frame, f"R_{per}_{self._strategy}")[1] -
                 _sum_tx(self._data_frame, f"R_{per}_{self._strategy}")[0]
                ) / self._data_frame.loc[self._data_frame[f"R_{per}_{self._strategy}"] == "B", "adj_close"].iloc[0],
            )
            for per in range(self._period["min"], self._period["max"] + 1)
        ]
        if self._debug:
            for per in range(self._period["min"], self._period["max"] + 1):
                print(
                    f"sum_tx period {per} : {_sum_tx(self._data_frame, f'R_{per}_{self._strategy}')}"
                )
        # Build the objective function DataFrame from the list of lists
        self._o_function = pd.DataFrame(of_list, columns = OF_COLUMNS).set_index(OF_COLUMNS[0])
        if self._debug:
            print(f"Objective function:\n{self._o_function}")


    def _build_maxima(self):
        gains_col = self._o_function["gains"].values
        n = len(gains_col)
        maxima = np.zeros_like(gains_col, dtype=bool)

        # Handle edge cases first
        if n > 1:
            # First element check
            if gains_col[0] > gains_col[1]:
                print("Local maximum at index 0")
                maxima[0] = True

            # Last element check
            if gains_col[-1] > gains_col[-2]:
                print("Local maximum at last index")
                maxima[-1] = True

        # Interior single-point maxima (fully vectorized)
        if n > 2:
            # Create boolean mask for interior local maxima
            interior_maxima = np.zeros(n, dtype=bool)
            interior_maxima[1:-1] = (gains_col[1:-1] > gains_col[0:-2]) & (gains_col[1:-1] > gains_col[2:])

            # Apply the mask to maxima
            for i in np.where(interior_maxima)[0]:
                print(f"Local maximum at index {i}: {gains_col[i]}")

            maxima |= interior_maxima

        # Plateau detection (partially vectorized)
        if n > 1:
            # Find where values are the same as the next value
            same_as_next = np.zeros(n, dtype=bool)
            same_as_next[:-1] = (gains_col[:-1] == gains_col[1:])

            i = 0
            while i < n - 1:
                if same_as_next[i]:
                    start = i
                    # Find the end of this plateau
                    while i < n - 1 and same_as_next[i]:
                        i += 1
                    end = i

                    # Check if plateau is a local maximum
                    left_edge = start == 0 or gains_col[start] > gains_col[start - 1]
                    right_edge = end == n - 1 or gains_col[end] > gains_col[end + 1]

                    if left_edge and right_edge:
                        print(f"Plateau local maximum from index {start} to {end}")
                        maxima[start:end+1] = True
                i += 1

        # Set the max values
        self._o_function["max"] = np.where(maxima, gains_col, np.nan)


    def _build_maxima_old(self):
        gains_col = self._o_function["gains"].values
        maxima = np.zeros_like(gains_col, dtype=bool)

        i = 0
        while i < len(gains_col) - 1:
            # Plateau detection: check for flat sections
            if gains_col[i] == gains_col[i + 1]:
                start = i
                # Walk forward while the values are equal
                while i < len(gains_col) - 1 and gains_col[i] == gains_col[i + 1]:
                    i += 1
                end = i
                # Check plateau edges for local max condition
                if (start == 0 or gains_col[start] > gains_col[start - 1]) and (end == len(gains_col) - 1 or gains_col[end] > gains_col[end + 1]):
                    print(f"Plateau local maximum from index {start} to {end}")
                    maxima[start:end+1] = True
            else:
                # Regular local max detection
                if i > 0 and gains_col[i] > gains_col[i - 1] and gains_col[i] > gains_col[i + 1]:
                    print(f"Local maximum at index {i}: {gains_col[i]}")
                    maxima[i] = True
            i += 1

        # Check edge cases explicitly for row 0 and last row
        if len(gains_col) > 1:
            if gains_col[0] > gains_col[1]:
                print("Local maximum at index 0")
                maxima[0] = True
            if gains_col[-1] > gains_col[-2]:
                print("Local maximum at last index")
                maxima[-1] = True

        self._o_function["max"] = np.where(maxima, gains_col, np.nan)


    def _extract_max(self):
        """Extract global maxima and statistics for local maxima, ensuring periods are stored as integers."""
        # Rename the 'max' column to avoid conflict with the built-in function 'max'
        max_df = self._o_function.dropna(subset=["max"]).copy()
        max_df.rename(columns={"max": "max_column"}, inplace=True)
        if self._debug:
            print(f'max_df is:\n{max_df}')

        # Compute standard deviation and global maximum value
        self._std_of_local_max = max_df["max_column"].std()
        self._global_max = max_df["max_column"].max()

        # Find all periods where gains match the global max store them as integers
        self._global_max_periods = [int(period) for period in max_df[max_df["max_column"] == self._global_max].index]

        # Filter local maxima within 1 standard deviation of the global max and ensure integer indices
        self._max_df = max_df[max_df["max_column"] > self._global_max - self._std_of_local_max].copy()
        self._max_df.index = self._max_df.index.astype(int)  # Ensure period indices are integers

        # Count the number of local maxima
        self._n_local_max = len(max_df)
        self._nmax_1std = len(self._max_df)

        # Rename the column back for consistency
        self._max_df.loc[:, "max"] = self._max_df["max_column"]
        self._max_df.drop("max_column", axis=1, inplace=True)


    #--- POST-PROCESSING ---#
    def _cleanup(self):
        """Remove max column"""
        try:
            self._o_function.drop(['max'], axis = 1, inplace = True)
        except BaseException as e:
            sys_util.terminate('No column "max" in DataFrame ',
                               e, self.__class__.__name__, sys._getframe()
                               )


    #--- I/O ---#
    def save_data(self, output_dir:str = None) -> None:
        """Save data to csv file."""
        if output_dir is None:
            output_dir = self._config.get_config_parameters()['data_dir']

        date_range = self._req.get_dates("actual")  # Call from the correct object
        start_date = date_range["start_date"].strftime("%Y-%m-%d")
        end_date = date_range["end_date"].strftime("%Y-%m-%d")
        prefix = f"{self._req.get_ticker()}_{start_date}-{end_date}_of"
        io_util.dataframe_to_csv(self._o_function, output_dir, prefix)
