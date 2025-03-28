#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
@author: charles mégnin

Time stability roller
"""
import time
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import List, Optional
import driver
import config

CONFIGURATION_FILE = "config.yaml"
MAX_RETRIES = 3
NDAYS = 180
INCREMENT = 2
PLOT_OF = False
PLOT_TS = False
TICKER = "TSLA"


@dataclass
class AnalysisResult:
    end_date: str
    driver_instance: driver.Driver
    results_data: Optional[List] = None
    metrics: Optional[dict] = None


def generate_date_range(start_date: str, days: int) -> List[str]:
    """Generate descending date range with YYYY-MM-DD format"""
    current = datetime.strptime(start_date, "%Y-%m-%d")
    return [(current - timedelta(days=i)).strftime("%Y-%m-%d") for i in range(days)]

# Constant parameters (adjust these to your needs)
CONSTANT_PARAMS = {
    "conf": config.Config(CONFIGURATION_FILE),
    "ticker": TICKER,
    "nmonths": 24,
    "plot_of": PLOT_OF,
    "plot_ts": PLOT_TS,
}

t0 = time.perf_counter()
# Generate date range
date_range = generate_date_range("2025-03-21", NDAYS)

# Run analysis for each date
analysis_results = []

retries = 0
while retries < MAX_RETRIES:
    try:
        for end_date in date_range:
            # Initialize driver with current parameters
            drv = driver.Driver(
                conf=CONSTANT_PARAMS["conf"],
                ticker=CONSTANT_PARAMS["ticker"],
                end_date=end_date,
                nmonths=CONSTANT_PARAMS["nmonths"],
                plot_of=CONSTANT_PARAMS["plot_of"],
                plot_ts=CONSTANT_PARAMS["plot_ts"],
            )
            # Execute the analysis
            drive_results = drv.drive()  # Assuming this returns some results
            print(f"periods={drv.get_results()} maximum={drv.get_results()[1]}")

            # Store the results
            analysis_results.append(
                AnalysisResult(
                    end_date=end_date,
                    driver_instance=drv,
                    results_data=drv.get_results()[0],
                    metrics=drv.get_results(),
                )
            )
    except ConnectionError as e:
        print(f"Retrying due to: {e}")
        retries += 1
        time.sleep(2 ** retries)  # Exponential backoff


# processing results
print(f"Completed {len(analysis_results)} runs")
for result in analysis_results:
    print(
        f"Date: {result.end_date} | "
        f"Metrics: {result.metrics} | "
        f"Data points: {len(result.results_data) if result.results_data else 0}"
    )
print(f"Total run: {time.perf_counter() - t0:.1f}s")