#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
@author: charles mégnin

Time stability roller
"""
import time
import csv
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import List, Optional
import driver
import config
import utilities.system_utilities as sys_util

CONFIGURATION_FILE = "config.yaml"
MAX_RETRIES = 3
NDAYS = 50
INCREMENT = 1
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


def save_results_to_csv(results: List[AnalysisResult], filename: str = None):
    """Save analysis results to a CSV file.

    Args:
        results: List of AnalysisResult objects
        filename: Output filename (defaults to ticker_results_YYYY-MM-DD.csv)
    """
    if filename is None:
        timestamp = datetime.now().strftime("%Y-%m-%d")
        filename = f"{TICKER}_results_{timestamp}.csv"

    with open(filename, "w", newline="") as csvfile:
        # Determine all possible metric keys for the header
        all_metric_keys = set()
        for result in results:
            if result.metrics:
                all_metric_keys.update(result.metrics.keys())

        # Create fieldnames with date first, then all metrics
        fieldnames = ["date"] + sorted(list(all_metric_keys)) + ["data_points"]

        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
        writer.writeheader()

        for result in results:
            row = {
                "date": result.end_date,
                "data_points": len(result.results_data) if result.results_data else 0,
            }

            # Add all metrics to the row
            if result.metrics:
                for key, value in result.metrics.items():
                    row[key] = value

            # Convert list to comma-separated string
            row["data_points"] = (
                ", ".join(map(str, result.results_data)) if result.results_data else ""
            )

            writer.writerow(row)

    print(f"Results saved to {filename}")


def save_results_to_csv_old(results: List[AnalysisResult], filename: str = None):
    """Save analysis results to a CSV file.

    Args:
        results: List of AnalysisResult objects
        filename: Output filename (defaults to ticker_results_YYYY-MM-DD.csv)
    """
    if filename is None:
        timestamp = datetime.now().strftime("%Y-%m-%d")
        filename = f"{TICKER}_results_{timestamp}.csv"

    with open(filename, "w", newline="") as csvfile:
        # Determine all possible metric keys for the header
        all_metric_keys = set()
        for result in results:
            if result.metrics:
                all_metric_keys.update(result.metrics.keys())

        # Create fieldnames with date first, then all metrics
        fieldnames = ["date"] + sorted(list(all_metric_keys)) + ["data_points"]

        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
        writer.writeheader()

        for result in results:
            row = {
                "date": result.end_date,
                "data_points": result.results_data if result.results_data else None,
            }

            # Add all metrics to the row
            if result.metrics:
                for key, value in result.metrics.items():
                    row[key] = value

            writer.writerow(row)

    print(f"Results saved to {filename}")

# Constant parameters
CONSTANT_PARAMS = {
    "conf": config.Config(CONFIGURATION_FILE),
    "ticker": TICKER,
    "nmonths": 24,
    "plot_of": PLOT_OF,
    "plot_ts": PLOT_TS,
}


if __name__ == "__main__":
    t0 = time.perf_counter()

    # Generate date range
    date_range = generate_date_range("2025-03-21", NDAYS)
    print(sys_util.get_caller_info(f"Date range: {date_range}"))

    # Run analysis for each end date
    analysis_results = []
    for end_date in date_range:
        retries = 0
        drv = driver.Driver(
            conf=CONSTANT_PARAMS["conf"],
            ticker=CONSTANT_PARAMS["ticker"],
            end_date=end_date,
            nmonths=CONSTANT_PARAMS["nmonths"],
            plot_of=CONSTANT_PARAMS["plot_of"],
            plot_ts=CONSTANT_PARAMS["plot_ts"],
        )
        while retries < MAX_RETRIES:
            try:
                # Execute the analysis
                results_data, metric_value = drv.get_results()  # Unpack tuple
                print(
                    f"Date: {end_date} | Maximum: {metric_value} | results_data: {results_data}"
                )
                # Store the results
                analysis_results.append(
                    AnalysisResult(
                        end_date=end_date,
                        driver_instance=drv,
                        results_data=results_data,  # First element of tuple
                        metrics={"maximum": metric_value},  # Store float inside dict
                    )
                )
                break  # If success, break out of the while retries loop
            except ConnectionError as e:
                print(f"Retrying due to: {e}")
                retries += 1
                time.sleep(2**retries)  # Exponential backoff
        else:
            # Error message if the while loop completes without a successful try
            print(f"Skipping {end_date} after {MAX_RETRIES} failed attempts.")

    # Processing results
    print(f"Completed {len(analysis_results)} runs")
    for result in analysis_results:
        print(
            f"Date: {result.end_date} | "
            f"Maximum: {result.metrics['maximum']} | "
            f"# Data points: {len(result.results_data) if result.results_data else 0} | "
            f"Data points: {result.results_data if result.results_data else 0}"
        )

    # Save results to CSV
    save_results_to_csv(analysis_results, f"{TICKER}_roller.csv")
    print(f"Total run: {time.perf_counter() - t0:.1f}s")
