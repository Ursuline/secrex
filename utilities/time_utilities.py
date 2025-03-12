#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import time

def timing_decorator(func):
    """Timer as a decorator"""
    def wrapper(*args, **kwargs):
        t0 = time.perf_counter()
        result = func(*args, **kwargs)
        t1 = time.perf_counter()
        print(f'{func.__name__} running time: {t1 - t0:.2f} s')
        return result
    return wrapper
