# cython: language_level=3, linetrace=True
# distutils: define_macros=CYTHON_TRACE=1

import datetime as dt
cimport numpy as np
import numpy as np
import pandas as pd
from libc.math cimport isnan
from pandas.tseries.frequencies import to_offset

from htimeseries import HTimeseries

from .haggregate import RegularizationMode as RM


class RegularizeError(Exception):
    pass


def regularize(ts, new_date_flag="DATEINSERT", mode=RM.INTERVAL):
    # Sanity checks
    if not hasattr(ts, "time_step"):
        raise RegularizeError("The source time series does not specify a time step")
    try:
        pd.to_timedelta(to_offset(ts.time_step))
    except ValueError:
        raise RegularizeError(
            "The time step is malformed or is specified in months. Only time steps "
            "specified in minutes, hours or days are supported."
        )

    # Set metadata of result
    result = HTimeseries()
    attrs = (
        "unit",
        "timezone",
        "time_step",
        "interval_type",
        "variable",
        "precision",
        "location",
    )
    for attr in attrs:
        setattr(result, attr, getattr(ts, attr, None))
    if hasattr(ts, "title"):
        result.title = "Regularized " + ts.title
    if hasattr(ts, "comment"):
        result.comment = (
            "Created by regularizing step of timeseries that had this comment:\n\n"
            + ts.comment
        )

    # Return immediately if empty
    if len(ts.data) == 0:
        return result

    # Determine first and last timestamps
    step = pd.Timedelta(ts.time_step)
    first_timestamp_of_result = ts.data.index[0].round(step)
    last_timestamp_of_result = ts.data.index[-1].round(step)

    # Transform all pandas information to plain numpy, which is way faster and is also
    # supported by numba and Cython
    max_flags_length = max(ts.data["flags"].str.len()) + 1 + len(new_date_flag)
    flags_dtype = "U" + str(max_flags_length)
    ts_index = ts.data.index.values.astype(long)
    ts_values = ts.data["value"].values
    ts_flags = ts.data["flags"].values.astype(flags_dtype)
    result_step = np.timedelta64(step).astype(int) * 1000
    result_index = pd.date_range(
        first_timestamp_of_result, last_timestamp_of_result, freq=ts.time_step
    ).values
    result_values = np.full(len(result_index), np.nan, dtype=object)
    result_flags = np.full(len(result_index), "", dtype=flags_dtype)

    # Do the job
    _perform_regularization(
        result_index,
        result_values,
        result_flags,
        ts_index,
        ts_values,
        ts_flags,
        result_step,
        new_date_flag,
        mode.value,
    )

    result.data = pd.DataFrame(
        index=result_index,
        columns=["value", "flags"],
        data=np.vstack((result_values, result_flags)).transpose(),
    ).tz_localize(dt.timezone.utc).tz_convert(first_timestamp_of_result.tz)
    return result


def _perform_regularization(
    np.ndarray result_index,
    np.ndarray result_values,
    np.ndarray result_flags,
    np.ndarray ts_index,
    np.ndarray ts_values,
    np.ndarray ts_flags,
    long result_step,
    str new_date_flag,
    int mode,
):
    cdef int i, previous_pos
    cdef long t

    previous_pos = 0
    for i in range(result_index.size):
        t = result_index[i]
        result_values[i], result_flags[i], previous_pos = _get_record(
            ts_index,
            ts_values,
            ts_flags,
            t,
            result_step,
            new_date_flag,
            previous_pos,
            mode,
        )


def _get_record(
    np.ndarray ts_index,
    np.ndarray ts_values,
    np.ndarray ts_flags,
    long t,
    long result_step,
    str new_date_flag,
    int previous_pos,
    int mode,
):
    cdef int i, found, count
    cdef int nearest_i = -1
    cdef int INTERVAL = RM.INTERVAL.value
    cdef int INSTANTANEOUS = RM.INSTANTANEOUS.value

    # Return the source record if it already exists
    found = False
    for i in range(previous_pos, ts_index.size):
        if ts_index[i] == t and (mode == INTERVAL or not isnan(ts_values[i])):
            found = True
            break
        if ts_index[i] > t:
            break
    if found:
        return ts_values[i], ts_flags[i], i

    # Otherwise get the nearby record, if it exists
    start = t - result_step / 2
    end = t + result_step / 2
    count = 0
    for i in range(previous_pos, ts_index.size):
        ti = ts_index[i]
        if ti >= start and ti < end and (mode == INTERVAL or not isnan(ts_values[i])):
            count += 1
            nearest_i = _get_nearest(nearest_i, i, ts_index, ts_values, t, mode)
        if ts_index[i] >= end:
            i -= 1
            break
    if count < 1 or (count > 1 and mode == INTERVAL):
        return np.nan, "", i
    value = ts_values[nearest_i]
    flags = ts_flags[nearest_i]
    if flags:
        flags += " "
    flags += new_date_flag
    return value, flags, i + 1


def _get_nearest(
    int previous_nearest_i,
    int current_i,
    np.ndarray ts_index,
    np.ndarray ts_values,
    long t,
    int mode,
):
    if mode == RM.INTERVAL.value:
        # In that case it doesn't really matter which is the nearest, so long as it's
        # only one (which is checked elsewhere), so we return immediately.
        return current_i
    if previous_nearest_i < 0:
        return current_i
    current_distance = abs(t - ts_index[current_i])
    previous_distance = abs(t - ts_index[previous_nearest_i])
    if current_distance < previous_distance:
        return current_i
    else:
        return previous_nearest_i
