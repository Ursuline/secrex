#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
request.py

@author: charles mégnin

Request is a lightweight class that encapsulates the data requested from the financial data server:
- ticker symbol
- requested start & end dates

NB: - actual start and end dates returned from finance server
    - all dates are stored in datetime format
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

    def __init__(self, conf: config.Config, ticker: str, start: datetime, end: datetime):
        self._date_format = conf.get_date_format()
        self._company_info = {"ticker": ticker}
        self._date_range = {
            "requested": {"start_date": start, "end_date": end},
            "actual": {},
        }


    # --- GETTERS ---#
    def get_ticker(self):
        """Getter for the requested ticker symbol"""
        return self._company_info.get("ticker")


    def get_company_info(self):
        """Return company info dictionary"""
        return self._company_info


    def get_dates(self, date_type: str):
        """Getter for start & end - 'actual' and 'requested' dates"""
        if date_type.lower() not in ["requested", "actual"]:
            raise ValueError(f"date type {date_type} should be 'requested' or 'actual'")
        return self._date_range[date_type.lower()]


    # --- SETTERS ---#
    def set_actual_dates(self, start_date, end_date):
        """Setter for the date range returned by the finance server"""
        try:
            for date_type, date_value in zip(
                ["start_date", "end_date"], [start_date, end_date]
            ):
                if isinstance(date_value, datetime):
                    self._date_range["actual"][date_type] = date_value
                elif isinstance(date_value, str):
                    self._date_range["actual"][date_type] = datetime.strptime(
                        date_value, self._date_format
                    )
                else:
                    raise TypeError(
                        f"{date_type} {date_value} ({type(date_value)}) must be a datetime or str object"
                    )
        except Exception as e:
            sys_util.terminate(
                f"Could not set actual dates {start_date} {end_date}",
                e,
                self.__class__.__name__,
                sys._getframe(),
            )


    def set_company_name(self, name: str):
        """Setter for company name"""
        self._company_info["name"] = name


    def set_company_currency(self, currency: str):
        """Setter for company currency"""
        self._company_info["currency"] = currency
        self._set_company_currency_symbol()


    def _set_company_currency_symbol(self):
        """Setter for company currency symbol"""
        currency_symbols = {"USD": "US $",
                            "EUR": "€",
                            "GBP": "£",
                            "YEN": "¥",
                            }
        self._company_info["currency-symbol"] = currency_symbols.get(
            self._company_info["currency"], self._company_info["currency"]
        )


    def set_company_exchange(self, exchange: str):
        """Setter for company exchange"""
        self._company_info["exchange"] = exchange
