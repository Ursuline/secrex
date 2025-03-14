#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
@author: charles mégnin

Plotter class for the objective function
"""
import sys
import pandas as pd
import plotly.graph_objects as go
import inspect
import objective_function as obj_func
import config
import request
import utilities.system_utilities as sys_util
import utilities.io_utilities as io_util
from plotter import Plotter

class ObjectiveFunctionPlotter(Plotter):
    def __init__(self, conf:config.Config, req:request.Request, of:obj_func.ObjectiveFunction):
        super().__init__(conf=conf, req=req)
        self._of = of
        self._plot_type = 'of_plot'
        self._trace = {} # objective function trace
        self._local = {} # local maxima markers
        self._global = {} # global maximum marker


    def _extract_title_data(self):
            """Extract plot title information to build the title text"""
            # Get actual date range and convert values to string
            info = self._req.get_company_info()
            title = f'{info["name"]} '
            title += f'({self._req.get_ticker()} | {info["exchange"]})<br>'
            title += f'{self._of.get_global_max()[0]} days | {self._of.get_global_max()[1]:.1%} returns '
            title += f'({self._get_daterange()["start_date"]} -> {self._get_daterange()["end_date"]})'
            return (
                f"{info['name']} ({self._req.get_ticker()} | {info['exchange']})<br>"
                f"{self._of.get_global_max()[0]} days | {self._of.get_global_max()[1]:.1%} returns "
                f"({self._get_daterange()['start_date']} -> {self._get_daterange()['end_date']})"
            )


    def _extract_trace(self):
        """Extract information to build trace"""
        df = self._of.get_objective_function()
        self._trace.update({'period': df.index, 'gains': df.iloc[:, 0]})


    def _extract_local_max(self):
        """Extract information to build local max markers (local max are 1 stdev from global max)"""
        df = self._of.get_local_maxima()
        self._local.update({'period': df.index, 'gains': df.iloc[:, 0]})


    def _extract_global_max(self):
        """Extract information to build global max marker"""
        df = self._of.get_global_max()
        self._global = {"period": pd.Series([df[0]]), "gains": pd.Series([df[1]])}


    def plot(self):
        def _build_of_trace(figure:go.Figure):
            """Builds the trace of the objective function"""
            self._extract_trace()
            self._extract_local_max()
            self._extract_global_max()
            # base colors
            colors = [self._config[self._plot_type]['trace']['color']] * len(self._trace["period"])
            # Local minima colors
            for period in self._local["period"]:
                colors[period - self._trace["period"][0]] = self._config[self._plot_type]["markers"]["local-color"]
            # Global maximum color
            colors[self._global["period"][0] - self._trace["period"][0]] = self._config[self._plot_type]['markers']['global-color']
            figure.add_trace(go.Bar(x = self._trace['period'],
                                    y = self._trace['gains'],
                                    name = 'objective function',
                                    marker_color = colors,
                                    marker_line_color = self._config[self._plot_type]['trace']['line_color'],
                                    marker_line_width = self._config[self._plot_type]['trace']['line_width'],
                                    opacity  = self._config[self._plot_type]['trace']['opacity'],
                                    ))
            figure.update_layout(yaxis_tickformat=".1%")
        #--- plot() starts here ---#
        if self._config[self._plot_type]['display'] or self._config[self._plot_type]['save']:
            try:
                fig = go.Figure()
                _build_of_trace(fig)
                # Add title and legend using the parent class
                super()._build_title(fig, {'x': self._config[self._plot_type]['x_axis_title'],
                                           'y': self._config[self._plot_type]['y_axis_title'] + " ",
                                           })
                super()._build_legend(fig)

                # Display or save the plot based on configuration
                if self._config[self._plot_type]['display']:
                    fig.show()
                if self._config[self._plot_type]['save']:
                    io_util.save_figure(fig, self._config['image_dir'], super()._build_fileprefix(), 'jpg')

            except Exception as e:
                sys_util.warning('Cannot generate objective function plot', e, self.__class__.__name__, sys._getframe())
        else: # Stop here if both display/save flags switched off
            print(f'Obj func plot turned off in yaml config file ({self.__class__.__name__}.{inspect.stack()[0][3]}())')
