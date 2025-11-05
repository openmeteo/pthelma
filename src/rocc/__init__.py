from __future__ import annotations

from typing import TYPE_CHECKING, Callable, Iterable, NamedTuple

from .calculation import Rocc

if TYPE_CHECKING:  # pragma: no cover - used for type checkers only
    from htimeseries import HTimeseries


class Threshold(NamedTuple):
    delta_t: str
    allowed_diff: float


def rocc(
    *,
    timeseries: HTimeseries,
    thresholds: Iterable[Threshold],
    symmetric: bool = False,
    flag: str | None = "TEMPORAL",
    progress_callback: Callable[[float], None] = lambda x: None,
) -> list[str]:
    return Rocc(
        timeseries,
        thresholds,
        symmetric,
        flag,
        progress_callback=progress_callback,
    ).execute()
