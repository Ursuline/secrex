#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import functools
import time
import logging

# Configure logging (optional, for more detailed tracking)
logging.basicConfig(level=logging.ERROR, filename="app.log")


def timing_decorator(func):
    """Timer as a decorator with exception handling"""

    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        t0 = time.perf_counter()
        try:
            result = func(*args, **kwargs)  # Call the decorated function
        except Exception as e:
            t1 = time.perf_counter()
            logging.error(
                f"Exception in {func.__name__} after {t1 - t0:.2f} s", exc_info=True
            )
            print(f"Error in {func.__name__}: {e}")
            raise  # Optionally re-raise the exception if needed
        else:
            t1 = time.perf_counter()
            print(f"{func.__name__} running time: {t1 - t0:.2f} s")
            return result

    return wrapper
