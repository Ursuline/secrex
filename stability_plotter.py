#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
@author: charles mégnin

Plotter class for the stability analysis
"""
import pandas as pd
from plotly.subplots import make_subplots
import plotly.graph_objects as go
import config

NUM_COLS = 2
FILENAME = 'TSLA_roller.csv'
CONFIGURATION_FILE = 'config.yaml'
TITLE_X_OFFSET = .5
TITLE_Y_OFFSET = 1.0
HOR_SPACING = .05

class StabilityPlotter():
    def __init__(self, conf:config.Config, result_list:list=None):
        self._config = conf.get_config_parameters()
        self._plot_type = "stability_plot"
        self._root_conf = self._config[self._plot_type]
        self._stats = {}
        if result_list is None: # load data from file
            self._df = pd.read_csv(FILENAME, header=0)
        else: #load from caller
            print(f"result_list type: {type(result_list)}")
            for result in result_list:
                print(
                    f"{result.end_date} | {result.passive_gains:.1%} | {result.metrics['maximum']:.1%} | {result.results_data}"
                )
        self._df["difference"] = self._df["maximum"] - self._df["passive_gains"]


    def _extract_stats(self) -> None:
        self._stats['median'] = self._df['data_points'].median()
        self._stats['mode'] = self._df['data_points'].mode()
        self._stats['stdev'] = self._df['data_points'].std()
        self._stats['min'] = self._df['data_points'].min()
        self._stats['max'] = self._df['data_points'].max()
        print(f"mode = {self._stats['mode']} type {type(self._stats['mode'])}")


    def plot(self):
        fig = make_subplots(
            rows=1,
            cols=2,
            horizontal_spacing=HOR_SPACING,  # space bw subplots
        )
        # Add centered main plot title
        fig.update_layout(
            title_text=f"<b>{self._root_conf['plot_title']}</b>",  # Main title
            title_font_size=self._root_conf["plot_title_font"]["size"],
            title_font_color=self._root_conf["plot_title_font"]["color"],
            title_x=0.5,  # Center title
            showlegend=False,
            height=self._root_conf["subplot_height"],
        )
        # build period over time subplot
        self._build_T_over_t_subplot(figure=fig, row=1, column=1)
        # build histogram
        self._build_histogram_subplot(figure=fig, row=1, column=2)
        fig.show()


    def _add_subplot_title(self, figure:go.Figure, conf:dict, row:int, column:int) -> None:
        """Add a centered title and axes titles to the figure"""
        axis_index = (row - 1) * NUM_COLS + column
        figure.add_annotation(
            text=conf["subplot_title"],
            x=TITLE_X_OFFSET,
            y=TITLE_Y_OFFSET,
            xref=f"x{'' if axis_index == 1 else axis_index} domain",
            yref=f"y{'' if axis_index == 1 else axis_index} domain",
            showarrow=True,
            font=dict(
                size=self._root_conf["subplot_title_font"]["size"],
                color=self._root_conf["subplot_title_font"]["color"],
            ),
            xanchor="center",
        )
        figure.update_xaxes(
            title_text=conf["x_axis_title"],
            row=row,
            col=column,
        )
        figure.update_yaxes(
            title_text=conf["y_axis_title"],
            row=row,
            col=column,
        )


    def _build_T_over_t_subplot(self, figure: go.Figure, row, column) -> None:
        """Builds the optimal period over time stability plot"""
        subplot_type = 'T_over_t_subplot'
        conf = self._root_conf[subplot_type]
        # Add period vs time trace
        figure.add_trace(
            go.Scatter(
                x=self._df["date"],
                y=self._df["data_points"],
                mode="lines",
                line={
                    "color": conf["trace"]["color"],
                    "width": conf["trace"]["width"],
                },
                connectgaps=True,
            ),
            row=row,
            col=column,
        )
        """Add the title and axes titles to the figure"""
        self._add_subplot_title(figure=figure, conf=conf, row=row,column=column)


    def _build_histogram_subplot(self, figure:go.Figure, row:int, column:int) -> None:
        """Histogram of period at maximum"""
        subplot_type = "histogram_subplot"
        conf = self._root_conf[subplot_type]
        # Add histogram trace
        figure.add_trace(
            go.Histogram(
                x=self._df["data_points"],
                nbinsx=self._config["n_months"] * 30,  # One bin/day
                marker_color=conf["marker_color"],  # Bar color
                opacity=conf["marker_opacity"],  # Bar opacity,
            ),
            row=row,
            col=column,
        )
        self._add_subplot_title(figure=figure, conf=conf, row=row, column=column)


if __name__ == "__main__":
    conf = config.Config(CONFIGURATION_FILE)

    plotter = StabilityPlotter(conf=conf)
    plotter._extract_stats()
    plotter.plot()
