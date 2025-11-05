from __future__ import annotations

import datetime as dt
from typing import Sequence, TypedDict, cast

import pandas as pd

from enhydris_api_client import EnhydrisApiClient
from htimeseries import HTimeseries


class TimeseriesGroup(TypedDict):
    base_url: str
    station_id: int
    timeseries_group_id: int
    timeseries_id: int
    auth_token: str | None
    file: str


class TimeseriesCache(object):
    def __init__(self, timeseries_group: Sequence[TimeseriesGroup]) -> None:
        self.timeseries_group = timeseries_group
        self.base_url: str | None = None
        self.station_id: int | None = None
        self.timeseries_group_id: int | None = None
        self.timeseries_id: int | None = None
        self.auth_token: str | None = None
        self.filename: str | None = None

    def update(self) -> None:
        for item in self.timeseries_group:
            base_url = str(item["base_url"])
            if base_url[-1] != "/":
                base_url += "/"
            self.base_url = base_url
            self.station_id = int(item["station_id"])
            self.timeseries_group_id = int(item["timeseries_group_id"])
            self.timeseries_id = int(item["timeseries_id"])
            self.auth_token = cast(str | None, item.get("auth_token"))
            self.filename = str(item["file"])
            self._update_for_one_timeseries()

    def _update_for_one_timeseries(self) -> None:
        if self.filename is None:
            raise ValueError("Cache filename has not been initialised")
        cached_ts = self._read_timeseries_from_cache_file(self.filename)
        end_date = self._get_timeseries_end_date(cached_ts)
        start_date = end_date + dt.timedelta(minutes=1)
        new_ts = self._append_newer_timeseries(start_date, cached_ts)
        with open(self.filename, "w", encoding="utf-8") as f:
            new_ts.write(f, format=HTimeseries.FILE)

    def _read_timeseries_from_cache_file(self, filename: str) -> HTimeseries:
        try:
            with open(filename, newline="\n") as f:
                return HTimeseries(f)
        except (FileNotFoundError, ValueError):
            # If file is corrupted or nonexistent, continue with empty time series
            return HTimeseries()

    def _get_timeseries_end_date(self, timeseries: HTimeseries) -> dt.datetime:
        try:
            end_date = timeseries.data.index[-1]
        except IndexError:
            # Timeseries is totally empty; no start and end date
            end_date = dt.datetime(1, 1, 1, 0, 0, tzinfo=dt.timezone.utc)
        assert isinstance(end_date, dt.datetime)
        return end_date

    def _append_newer_timeseries(
        self, start_date: dt.datetime, old_ts: HTimeseries
    ) -> HTimeseries:
        if self.base_url is None:
            raise ValueError("API base URL has not been set")
        if self.station_id is None or self.timeseries_group_id is None:
            raise ValueError("Timeseries identifiers have not been set")
        if self.timeseries_id is None:
            raise ValueError("Timeseries id has not been set")
        with EnhydrisApiClient(self.base_url, token=self.auth_token) as api_client:
            ts = api_client.read_tsdata(
                self.station_id,
                self.timeseries_group_id,
                self.timeseries_id,
                start_date=start_date,
            )
            new_data = ts.data

            # For appending to work properly, both time series need to have the same
            # tz.
            oindex = cast(pd.DatetimeIndex, old_ts.data.index)
            nindex = cast(pd.DatetimeIndex, new_data.index)
            if len(old_ts.data):
                new_data.index = nindex.tz_convert(oindex.tz)
            else:
                old_ts.data.index = oindex.tz_convert(nindex.tz)

            ts.data = pd.concat(
                [old_ts.data, new_data], verify_integrity=True, sort=False
            )
        return ts
