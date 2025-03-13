#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
downloader.py

@author: charles mégnin

The downloader module handles the
- raw data downloads from source (presently alpha vantage) https://www.alphavantage.co/
- pre-processing of data

returns the time series as a pandas data frame containing:
- date in datetime format
- split and dividend-adjusted close
- spread (max - min for the day)
- volume

API key from environment
"""
import os
import sys
from datetime import datetime
from alpha_vantage.timeseries import TimeSeries
from alpha_vantage.fundamentaldata import FundamentalData
import config
import request
import utilities.system_utilities as sys_util
import utilities.time_utilities as time_util
import utilities.io_utilities as io_util

@time_util.timing_decorator
class Downloader:
    """
    The Downloader extracts stock data from source and generates a 4-column
    DataFrame with the NA-and-duplicate-removed and date-filtered data:
    self._time_series consisting of:
        - date
        - adjusted close
        - spread (day max - min)
        - volume

    Input:
        - a Config object
        - a Request object
    """

    def __init__(self, conf:config.Config, req:request.Request):
        self._configuration = conf
        self._request = req
        self._time_series = None

        # Load data, preprocess, and filter based on request
        self._load_data()
        self._apply_date_window(*self._request.get_dates("requested").values())
        self._preprocess()
        self._postprocess()
        self._update_request()

    #--- Getter ---#
    def get_time_series(self):
        """Getter for the time series and its metadata"""
        return self._time_series, self._meta


    def get_actual_date_range(self):
        """Getter for the actual date range of the data downloaded"""
        return {"actual_start_date": self._time_series.index[0],
                "actual_end_date": self._time_series.index[-1],}


    # --- Data Loading ---#
    def _load_data(self):
        """Load stock and company data"""
        self._load_time_series()
        self._load_company()


    def _load_company(self):
        """Load fundamental company data"""
        fd = FundamentalData(key = os.getenv('ALPHAVANTAGE_API_KEY'))
        try:
            data = fd.get_company_overview(self._request.get_ticker())
        except ValueError as e:
            sys_util.warning(f'Could not get fundamental data for ticker {self._request.get_ticker()}',
                             e, self.__class__.__name__, sys._getframe())
            # Should handle the downloading of this data through other means here
        else:
            self._request.set_company_name(data[0]['Name'])
            self._request.set_company_exchange(data[0]['Exchange'])
            self._request.set_company_currency(data[0]['Currency'])
            self._request.set_company_currency_symbol()

    def _load_time_series(self):
        """
        Load time series from data source as a pandas DataFrame
        """
        # Instantiate a TimeSeries object
        try:
            ts = TimeSeries(key = os.getenv('ALPHAVANTAGE_API_KEY'),
                            output_format = 'pandas',
                            )
        except BaseException as e:
            sys_util.terminate('Could not instantiate TimeSeries object from alpha vantage',
                                e, self.__class__.__name__, sys._getframe()
                                )
        # API call to download data
        try:
            self._time_series, self._meta, *_ = ts.get_daily_adjusted(self._request.get_ticker(),
                                                                      outputsize = 'full'
                                                                      )
        except BaseException as e:
            sys_util.terminate('Could not download daily adjusted TimeSeries from alpha vantage',
                                e, self.__class__.__name__, sys._getframe()
                                )


    #--- Data processing ---#
    def _apply_date_window(self, start_date: str, end_date: str):
        """Filter rows according to specified date window"""
        date_format = self._configuration.get_date_format()

        # Check if start_date and end_date are datetime objects, if so, no need to convert
        if isinstance(start_date, datetime) and isinstance(end_date, datetime):
            t_start = start_date
            t_end = end_date
        else:
            # Only convert to datetime if they are string
            try:
                t_start = datetime.strptime(start_date, date_format)
                t_end = datetime.strptime(end_date, date_format)
            except ValueError as e:
                sys_util.terminate(f'Format error with start ({start_date}) or end ({end_date}) date',
                                e, self.__class__.__name__, sys._getframe())

        # Date window consistency check
        assert t_start <= t_end, f'Start date {start_date} after end date {end_date}'

        # Apply date window to initial time series
        self._time_series = self._time_series.sort_index().loc[t_start:t_end]



    def _preprocess(self):
        """
        Preprocess raw data:
        - rename data columns
        - compute spread column (day high - low)
        - extract columns adj close, spread & volume
        """
        try:
            # Rename columns
            self._time_series.rename(columns={
                '1. open':'open',
                '5. adjusted close': 'adj_close',
                '6. volume': 'volume',
                }, inplace=True)
            # Compute spread
            self._time_series['spread'] = self._time_series['2. high'] - self._time_series['3. low']
            # Retain only necessary columns
            self._time_series = self._time_series[['adj_close', 'spread', 'volume']]
        except Exception as e:
            sys_util.terminate(
                "Error during preprocessing of raw data", e, self.__class__.__name__, sys._getframe()
                )


    def _postprocess(self):
        """Post-processing: remove duplicates and null values"""
        self._time_series.drop_duplicates(inplace = True)
        self._time_series.dropna(inplace=True)


    def _update_request(self):
        """Update the request object with the actual start and end dates"""
        date_format = self._configuration.get_date_format()
        self._request.set_actual_dates(
            start_date=self._time_series.index[0].date().strftime(date_format),
            end_date=self._time_series.index[-1].date().strftime(date_format),
        )

    #--- I/O ---#
    def print_time_series(self):
        """Print the time series"""
        io_util.pretty_print(self.get_time_series())
