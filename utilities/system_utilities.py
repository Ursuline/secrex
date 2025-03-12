#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import logging
import functools

logging.basicConfig(level = logging.INFO)

def terminate(msg:str, exc:Exception, cls, frm):
    """
    1. Build and output an exit message that includes exception, and class and frame
    from where the exception originated from
    2. terminate run with error code 1 due to exception raised
    Input:
        - Header string (generated from caller method) / msg
        - Exception object / exc
        - class from where termination is requested / cls
        - frame from where termination is requested / frm
    """
    warning(msg, exc,  cls, frm)
    exit(1)


def warning(msg:str, exc:Exception, cls, frm):
    """
    Build and output a warning message that includes exception, and class and frame
    from where the exception originated
    """
    print(f'{msg}\nException: {exc}\nClass: {cls}\nFunction: {frm}')


def log_execution(func):
    """Decorator to log functions"""
    @functools.wraps(func)
    def inner(*args, **kwargs):
        logging.info(f"Executing {func.__name__}")
        result = func(*args, **kwargs)
        logging.info(f"Finished executing {func.__name__}")
        return result
    return inner


def cache(func):
    """Cache via decorator

    Args:
        func (_type_): _description_

    Returns:
        _type_: _description_
    """
    cache = {}

    def wrapper(*args, **kwargs):
        key = (*args, *kwargs.items())

        if key in cache:
            print("Retrieving result from cache...")
            return cache[key]

        result = func(*args, **kwargs)
        cache[key] = result

        return result

    return wrapper
