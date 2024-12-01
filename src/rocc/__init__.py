from collections import namedtuple

from .calculation import Rocc

Threshold = namedtuple("Threshold", ["delta_t", "allowed_diff"])


def rocc(*, timeseries, thresholds, symmetric=False, flag="TEMPORAL"):
    return Rocc(timeseries, thresholds, symmetric, flag).execute()
