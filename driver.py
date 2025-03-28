#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
@author: charles mégnin

The Driver class runs a single call for a ticker
"""
import pandas as pd
from dateutil.relativedelta import relativedelta
from datetime import datetime
import downloader
import frame
import config
import request
import objective_function
import objective_function_plotter as of_plotter
import time_series_plotter as ts_plotter

class Driver():
    def __init__(self, conf:config.Config, ticker:str, end_date:str, nmonths:int, plot_of:bool, plot_ts:bool):
        self._conf = conf
        self._ticker = ticker
        self._end_date = end_date
        self._nmonths = nmonths
        self._plot_of = plot_of
        self._plot_ts = plot_ts
        self._of = None


    def get_of(self):
        """Getter for the objective function"""
        return self._of


    def get_results(self):
        """Getter for the optima"""
        return self._of.get_global_max()


    def drive(self) -> None:
        # Build the request object
        try:
            self._req = request.Request(
                conf=self._conf,
                ticker=self._ticker,
                start=datetime.strptime(self._end_date, self._conf.get_date_format())
                - relativedelta(months=self._nmonths),
                end=datetime.strptime(self._end_date, self._conf.get_date_format()),
            )

            self._download = downloader.Downloader(self._conf, self._req)
            raw, _ = self._download.get_time_series()
            ts_frame = frame.Frame(self._conf, raw, self._req)
            self._of = objective_function.ObjectiveFunction(
                conf=self._conf,
                frm=ts_frame,
                req=self._req,
            )

            if self._conf.get_config_parameters()["save_data"]:
                # Write frame time series to csv file
                ts_frame.to_csv(self._conf.get_config_parameters()["data_dir"])
                # Write objective function to csv file
                self._of.save_data(self._conf.get_config_parameters()["data_dir"])

            with pd.option_context(
                "display.max_rows",
                self._conf.get_pandas_display()["max_rows"],
                "display.max_columns",
                self._conf.get_pandas_display()["max_columns"],
                "display.width",
                self._conf.get_pandas_display()["width"],
                "display.precision",
                self._conf.get_pandas_display()["precision"],
                "display.colheader_justify",
                self._conf.get_pandas_display()["colheader_justify"],
            ):
                date_range = self._req.get_dates('actual')
                if self._conf.get_debug():
                    print(f"\nSecurity: {self._ticker}")
                    print(f'Date range: {date_range["start_date"].date()} -> {date_range["end_date"].date()}')

            if self._plot_of:
                plot_instance = of_plotter.ObjectiveFunctionPlotter(
                    conf=self._conf, req=self._req, of=self._of
                )
                plot_instance.plot()

            if self._plot_ts:
                plot_instance = ts_plotter.TimeSeriesPlotter(
                    conf=self._conf, req=self._req, of=self._of, frm=ts_frame
                )
                plot_instance.plot()
        except Exception as e:
            print(f"error: {e}")
            raise