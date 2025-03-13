#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
frame_plotter.py

@author: charles mégnin

Plotter class for the time series of the Frame class
"""
#import sys
import plotly.graph_objects as go
import frame
import config
import request
import objective_function as obj_func
from plotter import Plotter
import utilities.io_utilities as io_util

class TimeSeriesPlotter(Plotter):
    def __init__(self, conf:config.Config, req:request.Request, of:obj_func, frm:frame.Frame):
        super().__init__(conf=conf, req=req)
        self._data_frame = frm.get_data_frame()
        self._plot_type = 'ts_plot'
        self._period = of.get_max_period()


    # def _build_buffer(self, figure:go.Figure):
    #     """Builds the buffer around the ema"""
    #     figure.add_trace(go.Scatter(x = self._data_frame.index,
    #                                 y = self._data_frame['adj_close'],
    #                                 mode = 'lines',
    #                                 name = 'adjusted close',
    #                                 line = {'color': self._config[self._plot_type]['trace']['color'],
    #                                         'width': self._config[self._plot_type]['trace']['width'],
    #                                         },
    #                                 connectgaps = True,
    #                                 ))


    def _build_close(self, figure: go.Figure):
        """Builds the adjusted close trace"""
        figure.add_trace(go.Scatter(
            x = self._data_frame.index,
            y = self._data_frame['adj_close'],
            mode = 'lines',
            name = 'adjusted close',
            line = {'color': self._config[self._plot_type]['trace']['color'],
                    'width': self._config[self._plot_type]['trace']['width'],
                    },
            connectgaps = True,
            ))


    def _build_moving_average(self, figure:go.Figure, ma_type:str):
        """Build exponential or simple moving average trace as required

        Args:
            figure (go.Figure): _description_
            ma_type (str): can be either of 'sma' or 'ema'
        """
        assert ma_type in {"ema", "sma"}, (
            f"Invalid ma_type '{ma_type}'. Expected 'ema' or 'sma'."
        )
        figure.add_trace(go.Scatter(
            x = self._data_frame.index,
            y = self._data_frame[f'{ma_type.upper()}_{self._period}'],
            mode = 'lines',
            name = f'{ma_type.upper()} ({self._period} days)',
            line = {'color': self._config[self._plot_type][ma_type]['color'],
                    'width': self._config[self._plot_type][ma_type]['width'],
                    'dash': 'solid'
                    },
            connectgaps = True,
            ))


    def _build_buffer(self, figure:go.Figure):
        """Builds the buffer """
        for sign, showlegend in (('+', True), ('-', False)):
            figure.add_trace(go.Scatter(
                x=self._data_frame.index,
                y=self._data_frame.get(f'EMA_{self._period}_{sign}', []),
                mode='lines',
                name='buffer' if showlegend else '',
                line={
                    'color': self._config[self._plot_type]['ema']['color'],
                    'width': self._config[self._plot_type]['ema']['width'],
                    'dash': 'dash'
                },
                connectgaps=True,
                showlegend=showlegend,
            ))


    def _extract_title_data(self):
        """Extract plot title information to build the title text"""
        info = self._req.get_company_info()
        return f'{info["name"]} ({self._req.get_ticker()} | {info["exchange"]})'


    def _build_tx(self, figure:go.Figure):
        """Displays buy / sell recommendations on the trace"""
        column = f"R_{self._period}_{self._config['strategy']}"
        df = self._data_frame

        for tx in ['Buy', 'Sell']:
            filtered_df = df[df[column] == tx[0]]
            figure.add_trace(
                go.Scatter(
                    x=filtered_df.index,
                    y=filtered_df["adj_close"],
                    mode="markers",
                    name=tx,
                    marker={
                        "symbol": self._config[self._plot_type]["markers"][
                            f"{tx.lower()}_symbol"
                        ],
                        "size": self._config[self._plot_type]["markers"]["size"],
                        "color": self._config[self._plot_type]["markers"][
                            f"{tx.lower()}_color"
                        ],
                        "line_width": self._config[self._plot_type]["markers"][
                            "line_width"
                        ],
                    },
                )
            )


    def _build_ancillaries(self, figure:go.Figure):
        """Optionally add slider and selector"""
        # Add range selector buttons
        if self._config[self._plot_type]['range_selector']:
            figure.update_layout(
                xaxis = {
                    'rangeselector': {
                        'buttons': [
                            {'count': 1, 'label': "1m", 'step': "month", 'stepmode': "backward"},
                            {'count': 6, 'label': "6m", 'step': "month", 'stepmode': "backward"},
                            {'count': 1, 'label': "YTD", 'step': "year", 'stepmode': "todate"},
                            {'count': 1, 'label': "year", 'step': "year", 'stepmode': "backward"},
                            {'step': "all"}
                        ]
                    },
                    'type': "date",
                }
            )
        # Add range slider at the bottom
        figure.update_xaxes = dict(visible = self._config[self._plot_type]['range_slider']),


    def plot(self):
        """Main plotting method"""
        fig = go.Figure()
        self._build_close(fig)
        for ma_type in ['ema', 'sma']:
            self._build_moving_average(fig, ma_type)

        self._build_buffer(fig)
        self._build_tx(fig)
        self._build_ancillaries(fig)
        super()._build_title(
            fig,
            {
                "x": self._config[self._plot_type]["x_axis_title"],
                "y": self._config[self._plot_type]["y_axis_title"]
                + f" ({self._req.get_company_info().get('currency-symbol', '')})",
            },
        )

        # Output
        if self._config[self._plot_type]['display']:
            fig.show()
        if self._config[self._plot_type]['save']:
            io_util.save_figure(fig, self._config['image_dir'], self._build_fileprefix(), 'jpg')
