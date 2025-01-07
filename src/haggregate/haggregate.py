import re
from enum import Enum

import numpy as np
import pandas as pd

from htimeseries import HTimeseries

methods = {
    "sum": pd.Series.sum,
    "mean": pd.Series.mean,
    "max": pd.Series.max,
    "min": pd.Series.min,
}


class AggregateError(Exception):
    pass


def aggregate(
    hts,
    target_step,
    method,
    min_count=1,
    missing_flag="MISS",
    target_timestamp_offset=None,
):
    aggregation = Aggregation(
        source_timeseries=hts,
        target_step=target_step,
        method=method,
        min_count=min_count,
        missing_flag=missing_flag,
        target_timestamp_offset=target_timestamp_offset,
    )
    aggregation.execute()
    return aggregation.result


class Aggregation:
    def __init__(self, **kwargs):
        for key, value in kwargs.items():
            setattr(self, key, value)
        self.source = SourceTimeseries(self.source_timeseries)
        self.result = AggregatedTimeseries()
        self.result.time_step = self.target_step

    def execute(self):
        self.result.set_metadata(self.source_timeseries)
        try:
            self.source.normalize(self.target_step)
        except CannotInferFrequency:
            return
        self.do_aggregation()
        self.result.remove_leading_and_trailing_nans()
        self.result.add_timestamp_offset(self.target_timestamp_offset)

    def do_aggregation(self):
        self.create_resampler()
        self.get_result_values()
        self.get_result_flags()

    def create_resampler(self):
        self.resampler = self.source.data["value"].resample(
            self.result.time_step, closed="right", label="right"
        )

    def get_result_values(self):
        result_values = self.resampler.agg(methods[self.method])
        values_count = self.resampler.count()
        result_values[values_count < self.min_count] = np.nan
        self.result.data["value"] = result_values

    def get_result_flags(self):
        max_count = int(pd.Timedelta(self.result.time_step) / self.source.freq)
        values_count = self.resampler.count()
        self.result.data["flags"] = (max_count - values_count).apply(
            lambda x: self.missing_flag.format(x) if x else ""
        )


class CannotInferFrequency(Exception):
    pass


attrs = ("unit", "timezone", "interval_type", "variable", "precision", "location")


class SourceTimeseries(HTimeseries):
    def __init__(self, s):
        for attr in attrs:
            setattr(self, attr, getattr(s, attr, None))
        self.data = s.data

    def normalize(self, target_step):
        """Reindex so that it has no missing records but has NaNs instead, starting from
        one before and ending in one after.
        """
        current_range = self.data.index
        try:
            self.freq = pd.tseries.frequencies.to_offset(pd.infer_freq(current_range))
            if self.freq is None:
                raise AggregateError(
                    "Can't infer time series step; maybe it's not regularized"
                )
        except ValueError:
            raise CannotInferFrequency()
        first_timestamp = (current_range[0] - pd.Timedelta("1s")).floor(target_step)
        end_timestamp = current_range[-1].ceil(target_step)
        new_range = pd.date_range(first_timestamp, end_timestamp, freq=self.freq)
        self.data = self.data.reindex(new_range)


class AggregatedTimeseries(HTimeseries):
    def set_metadata(self, source_timeseries):
        for attr in attrs:
            setattr(self, attr, getattr(source_timeseries, attr, None))
        if self.time_step not in ("1h", "1D"):
            raise AggregateError("The target step can currently only be 1h or 1D")
        if hasattr(source_timeseries, "title"):
            self.title = "Aggregated " + source_timeseries.title
        if hasattr(source_timeseries, "comment"):
            self.comment = (
                "Created by aggregating the time series that had this comment:\n\n"
                + source_timeseries.comment
            )

    def remove_leading_and_trailing_nans(self):
        while len(self.data.index) > 0 and pd.isnull(self.data["value"]).iloc[0]:
            self.data = self.data.drop(self.data.index[0])
        while len(self.data.index) > 0 and pd.isnull(self.data["value"]).iloc[-1]:
            self.data = self.data.drop(self.data.index[-1])

    def add_timestamp_offset(self, target_timestamp_offset):
        if target_timestamp_offset:
            periods = target_timestamp_offset.startswith("-") and 1 or -1
            freq = target_timestamp_offset.lstrip("-")
            self.data = self.data.shift(periods, freq=freq)


def _get_offset_in_minutes(timestamp_offset):
    m = re.match(r"(-?)(\d*)min$", timestamp_offset)
    if not m:
        raise AggregateError(
            "The target timestamp offset can currently only be a number of minutes "
            "such as 1min"
        )
    sign = m.group(1) == "-" and -1 or 1
    return sign * int(m.group(2))


class RegularizationMode(Enum):
    INSTANTANEOUS = 1
    INTERVAL = 2
