#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
io_utilities.py

@author: charles mégnin
I/O utilities

"""
import sys
import os
import pandas as pd
import pprint
import yaml
import plotly.graph_objects as go
import utilities.system_utilities as sys_util


def save_figure(figure:go.Figure, directory:str, fileprefix:str, extension:str):
    """Save figure as jpeg"""
    os.makedirs(directory, exist_ok = True)
    filename = fileprefix + '.' + extension
    filepath = os.path.join(directory, filename)
    try:
         figure.write_image(filepath)
    except BaseException as e:
         sys_util.warning(f'Could not write to {filepath}', e, None, sys._getframe())


def dataframe_to_csv(dataframe:pd.DataFrame, directory:str, fileprefix:str):
    """
    Write a pandas dataframe to csv file.
    Adds a csv extension to the file prefix if necessary
    """
    os.makedirs(directory, exist_ok = True)
    if fileprefix.endswith(".csv"):
         filename = fileprefix
    else:
         filename = f'{fileprefix}.csv'
         filepath = os.path.join(directory, filename)
    try:
         dataframe.to_csv(filepath,
                           sep = ',',
                           index = True,
                           header = True,
                           )
    except BaseException as e:
         sys_util.warning(f'Could not write to {filepath}', e, None, sys._getframe())
    else:
         print(f'dataframe saved as {filepath}')


def pretty_print(data_structure):
    """utility to pretty print any Python data structure

    Args:
    data_structure: the data structure to be printed
    """
    if pprint.isreadable(data_structure):
         pprint.pprint(data_structure)
    else:
         sys_util.warning(f'Could not pretty print {data_structure}', None, None, sys._getframe())


def load_yaml_file(yaml_filename:str):
    """
    Loads a yaml file.
    Input:
        - yaml filename
    Return
        - the yaml file contents as a dictionary
    """
    try:
         with open(yaml_filename, mode = 'r', encoding = 'utf-8') as c_file :
              return yaml.safe_load(c_file)
    except FileNotFoundError as e:
         sys_util.terminate(f'yaml file "{yaml_filename}" does not exist',
                            e, None, sys._getframe()
                            )
    except BaseException as e:
         sys_util.terminate('Error loading existing yaml file',
                            e, None, sys._getframe()
                            )


def load_csv_file(directory:str, csv_filename:str):
    """
    Loads a csv file.
    Input:
         -  filename

    Return
      - the csv file contents as a pandas DataFrame
    """
    filepath = os.path.join(directory, csv_filename)
    try:
         return pd.read_csv(filepath)
    except FileNotFoundError as e:
         sys_util.terminate(f'Could not find {filepath}', e, None, sys._getframe())
    except pd.errors.EmptyDataError as e:
         sys_util.terminate(f'No data in {filepath}', e, None, sys._getframe())
    except pd.errors.ParserError as e:
         sys_util.terminate(f'Parse error in {filepath}', e, None, sys._getframe())
    except BaseException as e:
         sys_util.terminate(f'Undetermined error loading {filepath}', e, None, sys._getframe())
