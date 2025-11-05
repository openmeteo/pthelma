from __future__ import annotations

import datetime as dt
from enum import Enum
from typing import Any, Optional

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
    hts: HTimeseries,
    target_step: str,
    method: str,
    min_count: int = 1,
    missing_flag: str = "MISS",
    target_timestamp_offset: Optional[str] = None,
) -> HTimeseries:
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
    def __init__(
        self,
        *,
        source_timeseries: HTimeseries,
        target_step: str,
        method: str,
        min_count: int,
        missing_flag: str,
        target_timestamp_offset: Optional[str],
    ) -> None:
        self.source_timeseries = source_timeseries
        self.target_step = target_step
        self.method = method
        self.min_count = min_count
        self.missing_flag = missing_flag
        self.target_timestamp_offset = target_timestamp_offset
        self.source = SourceTimeseries(self.source_timeseries)
        self.result = AggregatedTimeseries()
        self.result.time_step = self.target_step
        self.resampler: Any = None

    def execute(self) -> None:
        self.result.set_metadata(self.source_timeseries)
        try:
            self.source.normalize(self.target_step)
        except CannotInferFrequency:
            return
        self.do_aggregation()
        self.result.remove_leading_and_trailing_nans()
        self.result.add_timestamp_offset(self.target_timestamp_offset)

    def do_aggregation(self) -> None:
        self.create_resampler()
        self.get_result_values()
        self.get_result_flags()

    def create_resampler(self) -> None:
        self.resampler = self.source.data["value"].resample(
            self.result.time_step, closed="right", label="right"
        )

    def get_result_values(self) -> None:
        if self.resampler is None:
            raise RuntimeError("Resampler has not been initialised")
        result_values = self.resampler.agg(methods[self.method])
        values_count = self.resampler.count()
        result_values[values_count < self.min_count] = np.nan
        self.result.data["value"] = result_values

    def get_result_flags(self) -> None:
        if self.resampler is None:
            raise RuntimeError("Resampler has not been initialised")
        assert self.source.freq is not None
        source_time_step = dt.timedelta(microseconds=self.source.freq.nanos / 1000)
        result_time_step = pd.Timedelta(self.result.time_step)
        assert isinstance(result_time_step, dt.timedelta)
        max_count = int(result_time_step / source_time_step)
        values_count = self.resampler.count()
        self.result.data["flags"] = (max_count - values_count).apply(
            lambda x: self.missing_flag.format(x) if x else ""
        )


class CannotInferFrequency(Exception):
    pass


attrs: tuple[str, ...] = (
    "unit",
    "timezone",
    "interval_type",
    "variable",
    "precision",
    "location",
)


class SourceTimeseries(HTimeseries):
    def __init__(self, s: HTimeseries) -> None:
        for attr in attrs:
            setattr(self, attr, getattr(s, attr, None))
        self.data = s.data

    def normalize(self, target_step: str) -> None:
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
        end_timestamp = current_range[-1].ceil(target_step)  # type: ignore[assignment]
        new_range = pd.date_range(first_timestamp, end_timestamp, freq=self.freq)
        self.data = self.data.reindex(new_range)


class AggregatedTimeseries(HTimeseries):
    def set_metadata(self, source_timeseries: HTimeseries) -> None:
        for attr in attrs:
            setattr(self, attr, getattr(source_timeseries, attr, None))
        try:
            time_step = pd.Timedelta(self.time_step)
            assert isinstance(time_step, dt.timedelta)
            if time_step <= pd.Timedelta(0):
                raise ValueError("Non-positive time step")
        except ValueError as e:
            raise AggregateError(
                "The target step must be a positive, fixed duration such as 1h or 1D"
            ) from e
        if hasattr(source_timeseries, "title"):
            self.title = "Aggregated " + source_timeseries.title
        if hasattr(source_timeseries, "comment"):
            self.comment = (
                "Created by aggregating the time series that had this comment:\n\n"
                + source_timeseries.comment
            )

    def remove_leading_and_trailing_nans(self) -> None:
        while len(self.data.index) > 0 and pd.isnull(self.data["value"]).iloc[0]:
            self.data = self.data.drop(self.data.index[0])  # type: ignore[index]
        while len(self.data.index) > 0 and pd.isnull(self.data["value"]).iloc[-1]:
            self.data = self.data.drop(self.data.index[-1])  # type: ignore[index]

    def add_timestamp_offset(self, target_timestamp_offset: Optional[str]) -> None:
        if target_timestamp_offset:
            periods = target_timestamp_offset.startswith("-") and 1 or -1
            freq = target_timestamp_offset.lstrip("-")
            self.data = self.data.shift(periods, freq=freq)


class RegularizationMode(Enum):
    INSTANTANEOUS = 1
    INTERVAL = 2
