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


def save_figure(
    figure: go.Figure, directory: str, fileprefix: str, extension: str
    ) -> None:
    """
    Save a Plotly figure to an image file.

    Args:
        figure (go.Figure): The Plotly figure to save.
        directory (str): The directory to save the file in.
        fileprefix (str): The filename prefix (without extension).
        extension (str): The file extension (e.g., 'jpeg', 'png', 'pdf').

    The function ensures the directory exists and handles potential exceptions
    when saving the figure.
    """
    func_name = sys._getframe().f_code.co_name  # Get function name
    os.makedirs(directory, exist_ok = True)

    filename = fileprefix + '.' + extension
    filepath = os.path.join(directory, filename)

    try:
        figure.write_image(filepath)
        print(f"[{func_name}] Figure saved as {filepath}")
    except PermissionError as e:
        sys_util.warning(f"[{func_name}] Permission denied: {filepath}", e)
    except OSError as e:  # Handles filesystem-related errors
        sys_util.warning(f"[{func_name}] OS error while writing {filepath}", e)
    except ValueError as e:  # Handles invalid file extensions
        sys_util.warning(f"[{func_name}] Invalid file extension '{extension}'", e)
    except Exception as e:
        sys_util.warning(f"[{func_name}] Unexpected error writing {filepath}", e)


def dataframe_to_csv(dataframe:pd.DataFrame, directory:str, fileprefix:str) -> None:
    """
    Write a pandas DataFrame to a CSV file.

    Args:
        dataframe (pd.DataFrame): The DataFrame to save.
        directory (str): The directory to save the file in.
        fileprefix (str): The filename prefix (without or with ".csv" extension).

    The function ensures the directory exists, adds a ".csv" extension if missing,
    and handles potential exceptions when saving the file.
    """
    func_name = sys._getframe().f_code.co_name  # Get function name

    os.makedirs(directory, exist_ok = True)
    filename = f"{fileprefix}.csv" if not fileprefix.endswith(".csv") else fileprefix
    filepath = os.path.join(directory, filename)

    try:
        dataframe.to_csv(filepath, sep=",", index=True, header=True)
        print(f"[{func_name}] DataFrame saved as {filepath}")
    except PermissionError as e:
        sys_util.warning(f"[{func_name}] Permission denied: {filepath}", e)
    except OSError as e:  # Covers file system-related errors
        sys_util.warning(f"[{func_name}] OS error while writing {filepath}", e)
    except Exception as e:
        sys_util.warning(f"[{func_name}] Unexpected error writing {filepath}", e)


def pretty_print(data_structure) -> None:
    """
    Utility to pretty print any Python data structure.

    Args:
        data_structure: The data structure to be printed.

    The function uses `pprint` for better readability. If the structure is not readable,
    it logs a warning.
    """
    func_name = sys._getframe().f_code.co_name  # Get function name

    try:
        if pprint.isreadable(data_structure):
            pprint.pprint(data_structure)
        else:
            sys_util.warning(
                f"[{func_name}] Could not pretty print data structure", None
            )
    except Exception as e:
        sys_util.warning(f"[{func_name}] Unexpected error during pretty printing", e)


def load_yaml_file(yaml_filename:str) -> dict:
    """
    Loads a YAML file and returns its contents as a dictionary.

    Args:
        yaml_filename (str): Path to the YAML file.

    Returns:
        dict: The contents of the YAML file.

     Raises:
        SystemExit: If the file is not found or another error occurs.
    """
    func_name = sys._getframe().f_code.co_name  # Get the current function name
    try:
         with open(yaml_filename, encoding = 'utf-8') as c_file :
              return yaml.safe_load(c_file) or {}
    except (FileNotFoundError, yaml.YAMLError) as e:
        sys_util.terminate(
            f'[{func_name}] Error loading YAML file "{yaml_filename}"', e
        )


def load_csv_file(directory: str, csv_filename: str) -> pd.DataFrame:
    """
    Loads a CSV file into a pandas DataFrame.

    Args:
        directory (str): The directory containing the CSV file.
        csv_filename (str): The name of the CSV file.

    Returns:
        pd.DataFrame: The contents of the CSV file.

    Raises:
        SystemExit: If the file is not found, empty, or has parsing errors.
    """
    func_name = sys._getframe().f_code.co_name  # Get function name
    filepath = os.path.join(directory, csv_filename)
    try:
        return pd.read_csv(filepath)
    except (FileNotFoundError, pd.errors.EmptyDataError, pd.errors.ParserError) as e:
        error_types = {
            FileNotFoundError: "Could not find",
            pd.errors.EmptyDataError: "No data in",
            pd.errors.ParserError: "Parse error in",
        }
        error_message = (
            f"[{func_name}] {error_types.get(type(e), 'Error loading')} {filepath}"
        )
        sys_util.terminate(error_message, e)
    except Exception as e:
        sys_util.terminate(f"[{func_name}] Undetermined error loading {filepath}", e)
