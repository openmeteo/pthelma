# cython: language_level=3, warn.undeclared=True, warn.maybe_uninitialized=True, infer_types=False

cdef object dt
import datetime as dt

cimport numpy as np

np.import_array()

import cython

from cpython cimport array
from cpython.bytes cimport PyBytes_AsStringAndSize
from libc.math cimport NAN, isnan
from libc.string cimport memcpy

import numpy as np


cdef object pd
import pandas as pd


cdef int MAX_SUCCESSIVE_DELTA_T_FACTOR = 100


cdef class Rocc:
    cdef object htimeseries
    cdef object thresholds
    cdef array.array threshold_deltas
    cdef array.array threshold_allowed_diffs
    cdef long[:] ts_index
    cdef np.uint8_t[:] failed_mask
    cdef double[:] ts_values
    cdef int max_flags_length
    cdef bytes rocc_flag
    cdef char *p_rocc_flag
    cdef int rocc_flag_len_bytes
    cdef np.uint32_t[:, :] ts_flags
    cdef array.array buf
    cdef bint symmetric
    cdef str flag
    cdef list failures
    cdef np.int64_t largest_delta
    cdef np.int64_t smallest_delta
    cdef int len_thresholds
    cdef int ts_utc_offset_minutes
    cdef object progress_callback

    @cython.warn.undeclared(False)
    def __init__(self, timeseries, thresholds, symmetric, flag, progress_callback):
        cdef Py_ssize_t n

        if flag is None:
            flag = ""
        self.htimeseries = timeseries
        self.thresholds = sorted(
            thresholds,
            key=lambda t: (self._get_delta_t_transformed(t.delta_t), t.allowed_diff),
        )
        self.symmetric = symmetric
        self.flag = flag or ""
        self.failures = []
        self._transform_thresholds()
        self._transform_to_plain_numpy()
        self.largest_delta = self.threshold_deltas[-1]
        self.smallest_delta = self.threshold_deltas[0]
        bufsize = MAX_SUCCESSIVE_DELTA_T_FACTOR + self.largest_delta // self.smallest_delta + 1
        self.buf = array.array("l", [0] * bufsize)
        self.len_thresholds = len(thresholds)
        self.rocc_flag = flag.encode("utf-32-le")
        self.rocc_flag_len_bytes = len(self.rocc_flag)
        PyBytes_AsStringAndSize(self.rocc_flag, &self.p_rocc_flag, &n)
        self.rocc_flag_len_bytes = n
        self.progress_callback = progress_callback

    def _get_delta_t_transformed(self, delta_t):
        if not delta_t[0].isdigit():
            delta_t = "1" + delta_t
        return int(pd.Timedelta(delta_t).to_timedelta64())

    def execute(self):
        self._do_actual_job()
        self._transform_to_pandas()
        return self.failures

    @cython.warn.undeclared(False)
    def _transform_thresholds(self):
        self.threshold_deltas = array.array("l")
        self.threshold_allowed_diffs = array.array("d")

        for t in self.thresholds:
            self.threshold_deltas.append(self._get_delta_t_transformed(t.delta_t))
            self.threshold_allowed_diffs.append(t.allowed_diff)

    @cython.warn.undeclared(False)
    def _transform_to_plain_numpy(self):
        flag_lengths = self.htimeseries.data["flags"].str.len()
        max_existing_flags_length = 0 if flag_lengths.empty else max(flag_lengths)
        self.max_flags_length = max_existing_flags_length + 1 + len(self.flag)
        flags_dtype = f"U{self.max_flags_length}"
        self.ts_index = self.htimeseries.data.index.values.astype(np.int64)
        self.failed_mask = np.zeros(self.ts_index.size, dtype=np.uint8)
        self.ts_values = self.htimeseries.data["value"].values
        flags = self.htimeseries.data["flags"].values
        self.ts_flags = flags.astype(flags_dtype).view(np.uint32).reshape(-1, self.max_flags_length)
        try:
            utc_offset = self.htimeseries.data.index.tz.utcoffset(dt.datetime.now())
        except AttributeError:
            utc_offset = dt.timedelta(0)
        self.ts_utc_offset_minutes = int(utc_offset.total_seconds() / 60)

    cdef _do_actual_job(self):
        cdef int i, last_valid_index = -1
        cdef bint record_passes_check

        for i in range(self.ts_index.size):
            if i % 10000 == 0:
                self.progress_callback(i / self.ts_index.size)
            record_passes_check = self._record_passes_check(i, last_valid_index)
            if not record_passes_check:
                self.failed_mask[i] = 1
                if self.flag:
                    self._add_flag(i)
            elif not isnan(self.ts_values[i]):
                last_valid_index = i

    @cython.warn.undeclared(False)
    def _transform_to_pandas(self):
        flags = np.asarray(self.ts_flags).reshape(-1).view(f"<U{self.max_flags_length}")
        self.htimeseries.data = pd.DataFrame(
            index=self.htimeseries.data.index,
            columns=["value", "flags"],
            data=np.vstack((self.ts_values, flags)).transpose(),
        )
        self.htimeseries.data["value"] = self.htimeseries.data["value"].astype(np.float64)

    cdef void _add_flag(self, int i):
        cdef int j = 0
        while j < self.max_flags_length and self.ts_flags[i, j] != 0:
            j += 1
        if j > 0:
            self.ts_flags[i, j] = 32  # Add space
            j += 1
        memcpy(&self.ts_flags[i, j], self.p_rocc_flag, self.rocc_flag_len_bytes)

    cdef bint _record_passes_check(self, int record_index, int last_valid_index):
        cdef int ti
        cdef double diff, threshold, max_allowed_diff
        cdef np.int64_t delta, timestamp, delta_t
        cdef str datestr, diffsign, thresholdsign, cmpsign, max_allowed_diff_sign
        cdef bint fails

        # Check explicit thresholds
        for ti in range(self.len_thresholds):
            delta = self.threshold_deltas[ti]
            threshold = self.threshold_allowed_diffs[ti]
            if self.symmetric:
                threshold = abs(threshold)
            diff = self._record_fails_explicit_threshold(record_index, delta, threshold)
            if not isnan(diff):
                timestamp = self.ts_index[record_index]
                datestr = str(
                    np.datetime64(timestamp, "ns") + np.timedelta64(self.ts_utc_offset_minutes, "m")
                )[:16]
                diffsign = '+' if diff > 0 else ''
                thresholdsign = '-' if self.symmetric and diff < 0 else ''
                cmpsign = '>' if diff > 0 else '<'
                self.failures.append(
                    f"{datestr}  {diffsign}{diff} in {self.thresholds[ti].delta_t} "
                    f"({cmpsign} {thresholdsign}{threshold})"
                )
                return False

        # Check implied thresholds with the previous valid record
        if last_valid_index < 0:
            return True
        delta_t = self.ts_index[record_index] - self.ts_index[last_valid_index]
        if delta_t > self.threshold_deltas[-1] * MAX_SUCCESSIVE_DELTA_T_FACTOR:
            return True
        diff = self.ts_values[record_index] - self.ts_values[last_valid_index]
        max_allowed_diff = self._get_max_allowed_diff(delta_t, diff < 0)
        fails = (
            (not self.symmetric and
                ((max_allowed_diff > 0 and diff > max_allowed_diff)
                or (max_allowed_diff < 0 and diff < max_allowed_diff)))
            or (self.symmetric and abs(diff) > abs(max_allowed_diff))
        )
        if fails:
            timestamp = self.ts_index[record_index]
            datestr = str(
                np.datetime64(timestamp, "ns") + np.timedelta64(self.ts_utc_offset_minutes, "m")
            )[:16]
            diffsign = '+' if diff > 0 else ''
            max_allowed_diff_sign = '-' if self.symmetric and diff < 0 else ''
            cmpsign = '>' if diff > 0 else '<'
            self.failures.append(
                f"{datestr}  {diffsign}{diff} "
                f"({cmpsign} {max_allowed_diff_sign}{max_allowed_diff})"
            )
            return False
        
        return True

    cdef double _record_fails_explicit_threshold(
        self,
        int record_index,
        np.int64_t threshold_delta,
        double threshold_allowed_diff,
    ):
        cdef double current_value = self.ts_values[record_index]
        cdef long current_timestamp = self.ts_index[record_index]
        cdef int i, fails
        cdef double diff;

        for i in range(record_index - 1, -1, -1):
            if current_timestamp - self.ts_index[i] > threshold_delta:
                return NAN
            if self.failed_mask[i]:
                continue
            diff = current_value - self.ts_values[i]
            fails = (
                not self.symmetric and
                (
                    (threshold_allowed_diff > 0 and diff > threshold_allowed_diff)
                    or (threshold_allowed_diff < 0 and diff < threshold_allowed_diff)
                )
                or (self.symmetric and abs(diff) > abs(threshold_allowed_diff))
            )
            if fails:
                return diff
        return NAN

    cdef double _get_max_allowed_diff(self, long delta_t, bint negative):
        cdef int pick, i
        cdef long remainder = delta_t
        cdef double allowed_diff, result = 0.0

        while True:
            pick = -1
            for i in range(self.len_thresholds - 1, -1, -1):
                if not self.symmetric:
                    if negative and self.threshold_allowed_diffs[i] > 0:
                        continue
                    elif not negative and self.threshold_allowed_diffs[i] < 0:
                        continue
                if self.threshold_deltas[i] <= remainder:
                    pick = i
                    break
            if pick < 0:
                break
            remainder -= self.threshold_deltas[pick]
            allowed_diff = self.threshold_allowed_diffs[pick]
            if self.symmetric:
                allowed_diff = abs(allowed_diff)
            result += allowed_diff
        if remainder > 0:
            # Find first threshold with correct sign and add it to result
            if self.symmetric:
                result += abs(self.threshold_allowed_diffs[0])
            elif negative:
                for i in range(self.len_thresholds):
                    if self.threshold_allowed_diffs[i] < 0:
                        result += self.threshold_allowed_diffs[i]
                        break
            else:
                for i in range(self.len_thresholds):
                    if self.threshold_allowed_diffs[i] > 0:
                        result += self.threshold_allowed_diffs[i]
                        break
        return result