#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import logging
import traceback
import functools
import sys

logging.basicConfig(level = logging.INFO)

def terminate(msg: str, exception: Exception, cls_name: str, function_name: str):
    """
    Build and output an exit message that includes exception, class, and function
    from where the exception originated, then terminate the execution.

    Args:
        msg (str): The custom message.
        exception (Exception): The exception that was raised.
        cls_name (str): The class name where the exception occurred.
        function_name (str): The function name where the exception occurred.
    """
    # Log the termination message
    logging.basicConfig(
        level=logging.ERROR, format="%(asctime)s - %(levelname)s - %(message)s"
    )

    # Create the termination message
    terminate_message = (
        f"{msg}\n"
        f"Exception: {exception}\n"
        f"Class: {cls_name}\n"
        f"Function: {function_name}\n"
        f"Traceback:\n{traceback.format_exc()}"
    )

    logging.error(terminate_message)

    # Gracefully terminate with error code 1
    sys.exit(1)


def warning(msg: str, exception: Exception, cls_name: str, function_name: str):
    """
    Build and output a warning message that includes exception, class, and function
    from where the exception originated.

    Args:
        msg (str): The custom warning message.
        exception (Exception): The exception that was raised.
        cls_name (str): The class name where the exception occurred.
        function_name (str): The function name where the exception occurred.
    """
    # Log the warning
    logging.basicConfig(
        level=logging.WARNING, format="%(asctime)s - %(levelname)s - %(message)s"
    )

    # Create the formatted warning message
    warning_message = (
        f"{msg}\n"
        f"Exception: {exception}\n"
        f"Class: {cls_name}\n"
        f"Function: {function_name}\n"
        f"Traceback:\n{traceback.format_exc()}"
    )

    logging.warning(warning_message)


def log_execution(log_level=logging.INFO):
    """Decorator to log functions with enhanced details."""

    def decorator(func):
        @functools.wraps(func)
        def inner(*args, **kwargs):
            # Log the function name and arguments
            logging.log(
                log_level,
                f"Executing {func.__name__} with arguments {args} and keyword arguments {kwargs}",
            )

            try:
                result = func(*args, **kwargs)
                # Log the result of the function call
                logging.log(
                    log_level, f"Finished executing {func.__name__}, result: {result}"
                )
                return result
            except Exception as e:
                # Log exception if one occurs
                logging.error(f"Exception in {func.__name__}: {e}")
                raise  # Re-raise the exception to preserve the original behavior

        return inner

    return decorator


def cache(func):
    """
    Cache via decorator.

    Args:
        func (callable): The function to be cached.

    Returns:
        callable: The wrapped function with caching behavior.

    """
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        # Create a key from args and kwargs
        key = (args, frozenset(kwargs.items()))
        if key in wrapper.cache:
            print("Retrieving result from cache...")
            return wrapper.cache[key]

        result = func(*args, **kwargs)
        wrapper.cache[key] = result
        return result

    wrapper.cache = {}
    return wrapper
