#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
config.py

@author: charles mégnin

The Config object encapsulates the configuration data contained in the yaml file
The configuration data is stored in the dictionary self._parameters and *each* element
can be accessed separately via getters.

- debug boolean to turn printing of some variables on/off
- date_format is the expected date format according to the datetime.datetime nomenclature
- periods tuple is min & max periodicity values for the moving averages (min, max)
- buffer is the tolerance around the adjusted close for an event to qualify as a change.
- T/F flags for EMA and SMA
"""
import sys
import utilities.system_utilities as sys_util
import utilities.io_utilities as io_util

class Config:
    """
    This class encapsulates the configuration parameters loaded from the config.yaml file
    Input:
        - the yaml filename where the parameters are stored
    """

    def __init__(self, config_filename:str):
        self._parameters = {} # dictionary of configuration variables
        self._load_configuration_file(config_filename)
        self._load_parameters()

    # --- GETTERS --- #
    def get_config_parameters(self):
        """return all parameters as a dictionary"""
        return self._parameters


    def get_pandas_display(self):
        """Returns pandas display parameters as a dictionary"""
        return self._parameters['pandas_display']


    def get_plot_parameters(self, plot_type:str):
        """Return plot parameters as a dictionary"""
        if plot_type not in ["of_plot", "ts_plot"]:
            raise ValueError(f'plot type {plot_type} should be "of_plot" or "ts_plot"')
        return self._parameters[plot_type]

    def get_debug(self):
        """Getter for the boolean debug parameter"""
        return self._parameters['debug']


    def get_date_format(self):
        """Getter for the date_format parameter"""
        return self._parameters['date_format']


    def get_periods(self):
        """Returns the min/max period parameter as a dictionary"""
        return self._parameters['period']


    def get_ema(self):
        """Returns True / False value for exponential moving average"""
        return self._parameters['moving_averages']['ema']


    def get_sma(self):
        """Returns True False value for simple moving average"""
        return self._parameters['moving_averages']['sma']


    def get_mad(self):
        """Returns True/False value for MAD analysis"""
        return self._parameters["mad"]["compute"]


    def get_long_MAD(self):
        """Return the long-period MAD"""
        return self._parameters['mad']["long_period"]


    def get_short_MAD(self):
        """Return the short-period MAD"""
        return self._parameters["mad"]["short_period"]


    def get_buffer(self):
        """Getter for the buffer parameter"""
        return self._parameters['buffer']


    def get_strategy(self):
        """Getter for the strategy parameter"""
        return self._parameters['strategy']


    def get_years(self):
        """Getter for the number of years of data required"""
        return self._parameters['years']


    def _load_parameters(self):
        """Constructor"""
        try:
            self._parameters = self._config.copy()
        except Exception as e:
            sys_util.terminate('Failed to load configuration parameters', e, self.__class__.__name__, sys._getframe())


    #--- IO ---#
    def _load_configuration_file(self, config_filepath:str):
        """
        Loads the yaml data from file into the _config variable.

        Input:
            - yaml filepath
        """
        self._config = io_util.load_yaml_file(config_filepath)


    def print_parameters(self):
        """Output all config parameters to stdout"""
        io_util.pretty_print(self._parameters)
