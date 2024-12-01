# cython: language_level=3
import datetime as dt

cimport numpy as np
from cpython cimport array

import numpy as np
import pandas as pd


class Rocc:
    def __init__(self, timeseries, thresholds, symmetric, flag):
        self.htimeseries = timeseries
        self.thresholds = thresholds
        self.symmetric = symmetric
        self.flag = flag or ""

    def execute(self):
        self._transform_thresholds()
        self._transform_to_plain_numpy()
        failures = self._do_actual_job()
        self._transform_to_pandas()
        return failures

    def _transform_thresholds(self):
        threshold_deltas = array.array("l")
        threshold_allowed_diffs = array.array("d")

        for threshold in self.thresholds:
            delta_t = int(self._get_delta_t_transformed(threshold.delta_t))
            threshold_deltas.append(delta_t)
            threshold_allowed_diffs.append(threshold.allowed_diff)
        self.threshold_deltas = threshold_deltas
        self.threshold_allowed_diffs = threshold_allowed_diffs

    def _get_delta_t_transformed(self, delta_t):
        if not delta_t[0].isdigit():
            delta_t = "1" + delta_t
        return pd.Timedelta(delta_t).to_timedelta64()

    def _transform_to_plain_numpy(self):
        flag_lengths = self.htimeseries.data["flags"].str.len()
        max_flag_length = 0 if flag_lengths.empty else max(flag_lengths)
        flags_dtype = "U" + str(max_flag_length + 1 + len(self.flag))
        self.ts_index = self.htimeseries.data.index.values.astype(long)
        self.ts_values = self.htimeseries.data["value"].values
        self.ts_flags = self.htimeseries.data["flags"].values.astype(flags_dtype)
        try:
            utc_offset = self.htimeseries.data.index.tz.utcoffset(dt.datetime.now())
        except AttributeError:
            utc_offset = dt.timedelta(0)
        self.ts_utc_offset_minutes = int(utc_offset.total_seconds() / 60)

    def _do_actual_job(self):
        return _perform_rocc(
            self.ts_index,
            self.ts_values,
            self.ts_flags,
            self.ts_utc_offset_minutes,
            list(self.thresholds),
            self.threshold_deltas,
            self.threshold_allowed_diffs,
            self.symmetric,
            self.flag,
        )

    def _transform_to_pandas(self):
        self.htimeseries.data = pd.DataFrame(
            index=self.htimeseries.data.index,
            columns=["value", "flags"],
            data=np.vstack((self.ts_values, self.ts_flags)).transpose(),
        )
        self.htimeseries.data["value"] = self.htimeseries.data["value"].astype(np.float64)


# IMPORTANT: There's some plain Python in the Cython below. Specifically, there are some
# Python lists and some places with undeclared variables. These are only used when a
# failure is found. Given that failures should be very few, this should not affect the
# overall speed. But I'm not really a Cython expert and I don't know exactly how it
# works.


def _perform_rocc(
    np.ndarray ts_index,
    np.ndarray ts_values,
    np.ndarray ts_flags,
    int ts_utc_offset_minutes,
    list thresholds,
    array.array threshold_deltas,
    array.array threshold_allowed_diffs,
    int symmetric,
    str flag,
):
    cdef int i, record_fails_check
    cdef list failures = []

    for i in range(ts_index.size):
        record_fails_check = _record_fails_check(
            i,
            ts_index,
            ts_values,
            ts_utc_offset_minutes,
            thresholds,
            threshold_deltas,
            threshold_allowed_diffs,
            symmetric,
            failures,
        )
        if record_fails_check and flag:
            _add_flag(i, ts_flags, flag)
    return failures


def _add_flag(int i, np.ndarray ts_flags, str flag):
    if ts_flags[i]:
        ts_flags[i] = ts_flags[i] + " "
    ts_flags[i] = ts_flags[i] + flag


def _record_fails_check(
    int record_index,
    np.ndarray ts_index,
    np.ndarray ts_values,
    int ts_utc_offset_minutes,
    list thresholds,
    array.array threshold_deltas,
    array.array threshold_allowed_diffs,
    int symmetric,
    list failures,
):
    cdef int ti
    cdef double diff

    for ti in range(len(threshold_deltas)):
        diff = _record_fails_threshold(
            record_index,
            threshold_deltas[ti],
            threshold_allowed_diffs[ti],
            ts_index,
            ts_values,
            symmetric,
        )
        if diff:
            timestamp = ts_index[record_index].item()
            datestr = str(
                np.datetime64(timestamp, "ns") + np.timedelta64(ts_utc_offset_minutes, "m")
            )[:16]
            diffsign = '+' if diff > 0 else ''
            thresholdsign = '-' if diff < 0 else ''
            cmpsign = '>' if diff > 0 else '<'
            failures.append(
                f"{datestr}  {diffsign}{diff} in {thresholds[ti].delta_t} "
                f"({cmpsign} {thresholdsign}{threshold_allowed_diffs[ti]})"
            )
            return True
    return False


def _record_fails_threshold(
    int record_index,
    long threshold_delta,
    double threshold_allowed_diff,
    np.ndarray ts_index,
    np.ndarray ts_values,
    int symmetric,
):
    cdef double current_value = ts_values[record_index]
    cdef long current_timestamp = ts_index[record_index]
    cdef int i, fails
    cdef double diff;

    for i in range(record_index - 1, -1, -1):
        if current_timestamp - ts_index[i] > threshold_delta:
            return False
        diff = current_value - ts_values[i];
        fails = (
            diff > threshold_allowed_diff
            or (symmetric and diff < -threshold_allowed_diff)
        )
        if fails:
            return diff
    return False
