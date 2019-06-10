from math import isnan
from numpy import reciprocal
from oeda.log import *
import itertools


def take_inverse(x):
    print("x", x)
    if x == 0 or isnan(float(x)) or x == "0":
        error("Division by zero or NaN, returning 0")
        return 0
    else:
        if isinstance(x, int):
            return 1./x
        elif isinstance(x, float):
            return reciprocal(x)
        elif isinstance(x, str):
            return reciprocal(float(x))
        else:
            error("Type is not supported, returning 0")
            return 0


def get_cartesian_product(knobs):
    keys, values = knobs.keys(), knobs.values()
    opts = [dict(zip(keys, items)) for items in itertools.product(*values)]
    return opts


def change_in_percentage(optimized_value, default_value):
    if default_value != 0:
        return float(optimized_value - default_value) / abs(default_value) * 100
    else:
        return "undefined"


def convert_time_difference_to_mins(tstamp1, tstamp2):
    if tstamp1 > tstamp2:
        td = tstamp1 - tstamp2
    else:
        td = tstamp2 - tstamp1
    td_mins = int(round(td.total_seconds() / 60))
    return td_mins
