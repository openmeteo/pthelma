from collections import namedtuple

from .calculation import Rocc

Threshold = namedtuple("Threshold", ["delta_t", "allowed_diff"])


def rocc(
    *,
    timeseries,
    thresholds,
    symmetric=False,
    flag="TEMPORAL",
    progress_callback=lambda x: None,
):
    return Rocc(
        timeseries,
        thresholds,
        symmetric,
        flag,
        progress_callback=progress_callback,
    ).execute()
