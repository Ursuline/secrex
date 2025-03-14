#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
frame_plotter.py

@author: charles mégnin

Super class for time series (TimeSeriesPlotter) and objective function (ObjectiveFunctionPlotter) plotters
"""
import plotly.graph_objects as go
import config
import request
import utilities.system_utilities as sys_util

class Plotter:
    def __init__(self, conf:config.Config, req:request.Request):
        self._config = conf.get_config_parameters()
        self._req = req


    def _build_title(self, figure: go.Figure, axis_titles: dict):
        """Add a title to the figure"""
        title_data = self._extract_title_data()
        font_config = self._config[self._plot_type]["font_title"]

        figure.update_layout(
            title={"text": title_data, "x": 0.5, "xanchor": "center"},
            font={
                "family": self._config[self._plot_type]["font_family"],
                "size": font_config["size"],
                "color": font_config["color"],
            },
            xaxis_title=axis_titles["x"],
            yaxis_title=axis_titles["y"],
        )


    def _build_legend(self, figure:go.Figure):
        """Build the figure legend"""
        font_config = self._config[self._plot_type]["font_legend"]

        figure.update_layout(
            legend={"x": 0.05, "y": 0.05},
            font={
                "family": self._config[self._plot_type]["font_family"],
                "size": font_config["size"],
                "color": font_config["color"],
            },
        )


    def _build_fileprefix(self):
        """Build prefix for image file name"""
        date_range = self._req.get_dates('actual')  # Call from the correct object
        return "_".join(
            [
                self._req.get_ticker(),
                date_range["start_date"].strftime("%Y-%m-%d"),
                date_range["end_date"].strftime("%Y-%m-%d"),
                self._plot_type[:-5], #remove the "_plot" from plot_type
            ]
        )


    def _get_daterange(self):
        """Return a dictionary with actual start & end dates"""
        dates = self._req.get_dates('actual')
        return {
            key: date.strftime(self._config["date_format"])
            for key, date in dates.items()
        }
