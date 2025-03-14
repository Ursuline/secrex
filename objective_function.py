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
    The objective function object encapsulates the relationship bw period and gains.
    """
    def __init__(self, conf:config.Config, frm:frame.Frame, req:request.Request):
        self._frame_obj = frm # Frame object
        self._data_frame = self._frame_obj.get_data_frame() # time series in Frame object
        self._config = conf
        self._req = req
        self._strategy = self._config.get_strategy()
        self._period = self._config.get_periods()
        # Set various configuration parameters as variables
        self._o_function = None # Objective function
        self._max_df = None # Dataframe of local maxima in _o_function < 1 sdev from max
        self._global_max = None  # maximum gains
        self._period_at_global_max = None  # period at max gain
        self._n_local_max = None  # number of local maxima
        self._nmax_1std = None  # number of local maxima 1 standard deviation from global max (incl. global max)
        self._std_of_local_max = None  # Standard deviation of local maxima
        # Call constructors
        self._build_objective_function()
        self._build_maxima()
        self._extract_max()


    #--- GETTERS ---#
    def get_objective_function(self):
        return self._o_function


    def get_local_maxima(self):
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
        """Return period at global max and global max as a tuple"""
        return self._period_at_global_max, self._global_max


    #--- CONSTRUCTORS ---#
    @time_util.timing_decorator
    def _build_objective_function(self):
        """
        Builds the objective function from the data frame and the strategy
        So far only a long strategy is considered
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
        for per in range (self._period['min'], self._period['max'] + 1):
            initial_buy = self._data_frame.loc[self._data_frame[f'R_{per}_{self._strategy}'] == 'B', 'adj_close'].iloc[0]
            # Compute $ amounts bought and sold
            buys, sells = _sum_tx(self._data_frame, f'R_{per}_{self._strategy}')
            # Add a row for the current period / gains to the objective function
            of_list.append([int(per), (sells - buys)/initial_buy])
        # Build the objective function DataFrame from the list of lists
        self._o_function = pd.DataFrame(of_list, columns = OF_COLUMNS).set_index(OF_COLUMNS[0])


    def _build_maxima(self):
        """Build max column from gains column"""
        gains_col = self._o_function["gains"].values
        local_max = (gains_col[1:-1] >= gains_col[:-2]) & (gains_col[1:-1] >= gains_col[2:])
        maxima = np.zeros_like(gains_col, dtype=bool)
        maxima[1:-1] = local_max
        self._o_function["max"] = np.where(maxima, gains_col, np.nan)


    def _extract_max(self):
        """Compute maxima and standard deviations """
        #1. Compute standard deviation of local maxima (must run prior to max)
        self._max_df = self._o_function.dropna(subset=["max"]).copy()
        self._std_of_local_max = self._max_df["max"].std()
        self._global_max = self._max_df["max"].max()
        self._period_at_global_max = self._max_df["max"].idxmax()
        self._max_df = self._max_df[self._max_df["max"] > (self._global_max - self._std_of_local_max)]
        self._n_local_max = len(self._max_df)
        self._nmax_1std = self._n_local_max


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
    def save_data(self, directory:str):
        """Save data to csv file"""
        prefix = f'{self._req.get_ticker()}_of'
        io_util.dataframe_to_csv(self._o_function, self._config.get_config_parameters()['data_dir'], prefix)
