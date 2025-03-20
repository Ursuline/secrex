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
        self._debug = conf.get_debug()
        self._trace = {} # objective function trace
        self._local = {} # local maxima markers


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
        if self._debug:
            print(f"Received global max dataframe from obj func: {df}")
        self._global = df[0]
        if self._debug:
            print(f"Built self._global: {self._global}")


    def plot(self):
        def _build_of_trace(figure:go.Figure):
            """Builds the trace of the objective function"""
            self._extract_trace()
            self._extract_local_max()
            self._extract_global_max()

            # Merge periods from trace and local maxima
            trace_periods = set(self._trace["period"])
            local_periods = set(self._local["period"])
            all_periods = sorted(trace_periods.union(local_periods))

            # Initialize colors with the default trace color
            colors = [self._config[self._plot_type]["trace"]["color"]] * len(all_periods)
            # Create a set to track updated periods
            updated_periods = set()

            # Assign local minima colors
            for period in self._local["period"]:
                if period not in updated_periods:
                    index = all_periods.index(period)
                    colors[index] = self._config[self._plot_type]["markers"]["local-color"]
                    updated_periods.add(period)

            # Assign global maximum color
            global_max_periods = self._global
            if self._debug:
                print(f"All periods: {all_periods}")
                print(f"Global max periods: {global_max_periods}")

            for global_period in global_max_periods:
                print(f"Processing global max {global_period}")
                if global_period in all_periods:  # Check to prevent errors
                    print(f"Setting color for global max {global_period}")
                    index = all_periods.index(global_period)
                    colors[index] = self._config[self._plot_type]['markers']['global-color']
                    updated_periods.add(global_period)

            figure.add_trace(
                go.Bar(x=all_periods,
                       y=self._trace["gains"],
                       name="objective function",
                       marker_color=colors,
                       marker_line_color=self._config[self._plot_type]["trace"]["line_color"],
                       marker_line_width=self._config[self._plot_type]["trace"]["line_width"],
                       opacity=self._config[self._plot_type]["trace"]["opacity"],
                       ))
            figure.update_layout(yaxis_tickformat=".1%")
            if self._debug:
                print("Global Period:", self._global)
                print("Trace Period:", self._trace["period"])

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
