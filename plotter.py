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
        prefix = f'{self._req.get_ticker()}_'
        
        if self._plot_type == 'of_plot':
            prefix += f'{self._get_daterange()["start_date"]}_{self._get_daterange()["end_date"]}_of'
        elif self._plot_type == 'ts_plot':
            prefix += '_ts'
        else:
            raise ValueError(f'Could not build output file prefix {prefix}')
        return prefix
