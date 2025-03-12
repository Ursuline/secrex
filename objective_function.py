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
        self._o_function = None # Objective function
        self._max_df = None # Dataframe of local maxima in _o_function < 1 sdev from max
        # Set various configuration parameters as variables
        self._strategy = self._config.get_strategy()
        self._period = self._config.get_periods()
        self._global_max = None # maximum gains
        self._period_at_global_max = None # period at max gain
        self._n_local_max = None # number of local maxima
        self._nmax_1std = None # number of local maxima 1 standard deviation from global max (incl. global max)
        self._std_of_local_max = None # Standard deviation of local maxima
        # Call constructors
        self._build_objective_function()
        self._build_maxima()
        self._extract_max()
        self._cleanup()

    #--- GETTERS ---#
    def get_objective_function(self):
        """Returns objective function"""
        return self._o_function


    def get_local_maxima(self):
        """Return a DataFrame of local maxima 1 sdev from global max"""
        return self._max_df


    def get_of_info(self):
        """Returns objective function info as a dictionary"""
        return {'period_at_global_max': self._period_at_global_max,
                'global_max': self._global_max,
                'std_of_local_max': self._std_of_local_max,
                'number_of_periods': self._period['max'] - self._period['min'] + 1,
                'number_of_local_max': self._n_local_max,
                'number_of_max_within_1_sdev': self._nmax_1std,
                }


    def get_max_period(self):
        """Return period corresponding to the global max"""
        return self._period_at_global_max


    def get_max_gains(self):
        """Return max gains"""
        return self._global_max


    def get_global_max(self):
        """Return global maximum as a tuple"""
        return (self.get_max_period(), self.get_max_gains())


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
            try:
                buys = df.loc[df[col] == 'B', 'adj_close'].fillna(0).sum()
                sells = df.loc[df[col] == 'S', 'adj_close'].fillna(0).sum()
                # Count number of 'B' & 'S' & adds the value of the day's close if nB != nS
                if df.groupby(col).size()['B'] == df.groupby(col).size()['S'] + 1:
                    # If more B than S (long), use today's close as last value for S
                    sells += df['adj_close'].iat[-1]
                elif df.groupby(col).size()['B'] + 1 == df.groupby(col).size()['S']:
                    # If more S than B (short), use today's close as last value for B
                    buys += df['adj_close'].iat[-1]
            except BaseException as e:
                sys_util.terminate(f'Could not sum transactions in column {col}',
                                   e, self.__class__.__name__, sys._getframe()
                                   )
            else:
                return buys, sells
        #--- end method utility ---#

        # _build_objective_function() starts here
        try:
            of_list = [] # accumulate rows in this list
            for per in range (self._period['min'], self._period['max'] + 1):
                initial_buy = self._data_frame.loc[self._data_frame[f'R_{per}_{self._strategy}'] == 'B', 'adj_close'].iloc[0]
                # Compute $ amounts bought and sold
                buys, sells = _sum_tx(self._data_frame, f'R_{per}_{self._strategy}')
                # Add a row for the current period / gains to the objective function
                of_list.append([int(per), (sells - buys)/initial_buy])
            # Build the objective function DataFrame from the list of lists
            self._o_function = pd.DataFrame(of_list, columns = OF_COLUMNS).set_index(OF_COLUMNS[0])
        except BaseException as e:
            sys_util.terminate('Failed to build objective function',
                               e, self.__class__.__name__, sys._getframe()
                               )


    def _build_maxima(self):
        """Build max column from gains column"""
        try:
            gains_col = self._o_function.gains
            self._o_function['max'] = gains_col[(gains_col.shift(1) <= gains_col) & (gains_col.shift(-1) <= gains_col)]
        except BaseException as e:
            sys_util.terminate('Failed to build maxima',
                               e, self.__class__.__name__, sys._getframe()
                               )


    def _extract_max(self):
        """Compute maxima and standard deviations """
        #1. Compute standard deviation of local maxima (must run prior to max)
        try:
            self._max_df = self._o_function[self._o_function['max'].notna()].copy()
            self._max_df = self._max_df.drop('gains', axis = 1)
            self._std_of_local_max = self._max_df['max'].std()
        except BaseException as e:
            sys_util.terminate('Failed to compute std',
                               e, self.__class__.__name__, sys._getframe()
                               )

        # 2. extract global max
        # replace NaNs from max column with 0
        try:
            self._o_function['max'] = self._o_function['max'].fillna(0)
            # number of local maxima
            self._n_local_max = self._o_function['max'].astype(bool).sum(axis = 0)
            # (global) max gains
            self._global_max = self._o_function['max'].max()
            # period corresponding to max gains
            self._period_at_global_max = self._o_function['max'].idxmax()

            # 3. extract columns where local max is within one standard deviation from global max
            self._max_df = self._max_df[self._max_df['max'] > (self._global_max - self._std_of_local_max)]
            self._nmax_1std = self._max_df.shape[0]
        except BaseException as e:
            sys_util.terminate('Failed to extract global max',
                               e, self.__class__.__name__, sys._getframe()
                               )


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
        """Save data to xsl file"""
        prefix = f'{self._req.get_ticker()}_of'
        io_util.dataframe_to_csv(self._o_function, self._config.get_config_parameters()['data_dir'], prefix)
