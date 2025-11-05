from __future__ import annotations

from htimeseries import HTimeseries

from .haggregate import RegularizationMode

class RegularizeError(Exception): ...

def regularize(
    ts: HTimeseries,
    new_date_flag: str = ...,
    mode: RegularizationMode = ...,
) -> HTimeseries: ...
