#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
request.py

@author: charles mégnin

Request is a lightweight class that encapsulates the data requested from the financial data server:
- ticker symbol
- requested start & end dates
- actual start and end dates returned from finance server

NB: all dates are stored in datetime format
"""
import sys
from datetime import datetime
import config
import utilities.system_utilities as sys_util


class Request:
    """
    Input:
        - the ticker requested
        - requested start and end dates
    """

    def __init__(
        self, conf: config.Config, ticker: str, start: datetime, end: datetime
    ):
        self._date_format = conf.get_date_format()
        self._company_info = {}
        self._date_range = {
            "requested": {},
            "actual": {},
        }
        self._company_info["ticker"] = ticker
        self._date_range["requested"]["start_date"] = start
        self._date_range["requested"]["end_date"] = end

    # --- GETTERS ---#
    def get_ticker(self):
        """Getter for the requested ticker symbol"""
        return self._company_info["ticker"]

    def get_company_info(self):
        """Return company info dictionary"""
        return self._company_info

    def get_dates(self, date_type: str):
        """Getter for start & end - 'actual' and 'requested' dates"""
        assert date_type.lower() in [
            "requested",
            "actual",
        ], f'date type {date_type} should be "requested" or "actual"'
        return self._date_range[date_type.lower()]

    # --- SETTERS ---#
    def set_actual_dates(self, start_date, end_date):
        """Setter for the date range returned by the finance server"""
        try:
            if isinstance(start_date, datetime):
                self._date_range["actual"]["start_date"] = start_date
            elif isinstance(start_date, str):
                self._date_range["actual"]["start_date"] = datetime.strptime(
                    start_date, self._date_format
                )
            else:
                raise TypeError(
                    f"Start date {start_date} ({type(start_date)}) must be a datetime.datetime or a str object"
                )
            if isinstance(end_date, datetime):
                self._date_range["actual"]["end_date"] = end_date
            elif isinstance(end_date, str):
                self._date_range["actual"]["end_date"] = datetime.strptime(
                    end_date, self._date_format
                )
            else:
                raise TypeError(
                    f"End date {end_date} ({type(end_date)}) must be a datetime.datetime or a str object"
                )
        except BaseException as e:
            sys_util.terminate(
                f"Could not set actual dates {start_date} {end_date}",
                e,
                self.__class__.__name__,
                sys._getframe(),
            )


    def set_company_data():
        """Set additional company data"""


    def set_company_name(self, name: str):
        """Setter for company name"""
        self._company_info["name"] = name


    def set_company_currency(self, currency: str):
        """Setter for company currency"""
        self._company_info["currency"] = currency


    def set_company_currency_symbol(self):
        """Setter for company currency symbol"""
        if self._company_info["currency"] == "USD":
            self._company_info["currency-symbol"] = "US $"
        elif self._company_info["currency"] == "EUR":
            self._company_info["currency-symbol"] = "€"
        elif self._company_info["currency"] == "GBP":
            self._company_info["currency-symbol"] = "£"
        elif self._company_info["currency"] == "YEN":
            self._company_info["currency-symbol"] = "¥"
        else:
            self._company_info["currency-symbol"] = self._company_info["currency"]

    def set_company_exchange(self, exchange: str):
        """Setter for company exchange"""
        self._company_info["exchange"] = exchange
