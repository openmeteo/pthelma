from __future__ import annotations

import datetime as dt
import textwrap
from copy import copy
from io import StringIO
from typing import Any, Callable, Dict, cast
from unittest import mock

import pandas as pd
import requests

from htimeseries import HTimeseries

test_timeseries_csv: str = textwrap.dedent(
    """\
    2014-01-01 08:00,11.0,
    2014-01-02 08:00,12.0,
    2014-01-03 08:00,13.0,
    2014-01-04 08:00,14.0,
    2014-01-05 08:00,15.0,
    """
)
test_timeseries_htimeseries: HTimeseries = HTimeseries(
    StringIO(test_timeseries_csv), default_tzinfo=dt.timezone(dt.timedelta(hours=2))
)
test_timeseries_csv_top: str = "".join(
    test_timeseries_csv.splitlines(keepends=True)[:-1]
)
test_timeseries_csv_bottom: str = test_timeseries_csv.splitlines(keepends=True)[-1]


def mock_session(**kwargs: Any) -> mock._patch:
    """Mock requests.Session.

    Returns
        mock.patch("requests.Session", modified_kwargs)

    However, it first tampers with kwargs in order to achieve the following:
    - It adds a leading "return_value." to the kwargs; so you don't need to specify,
      for example, "return_value.get.return_value", you just specify "get.return_value".
    - If kwargs doesn't contain "get.return_value.status_code", it adds
      a return code of 200. Likewise for post, put and patch. For delete it's 204.
    - If "get.return_value.status_code" is not between 200 and 399,
      then raise_for_status() will raise HTTPError. Likewise for the other methods.
    """
    patch_kwargs: Dict[str, Any] = dict(kwargs)
    for method in ("get", "post", "put", "patch", "delete"):
        default_value = 204 if method == "delete" else 200
        status_code_key = f"{method}.return_value.status_code"
        status_code = patch_kwargs.setdefault(status_code_key, default_value)
        if isinstance(status_code, bool) or not isinstance(status_code, int):
            raise TypeError(
                "status_code overrides must be integers "
                f"(got {status_code!r} for {method})"
            )
        if status_code < 200 or status_code >= 400:
            method_side_effect = f"{method}.return_value.raise_for_status.side_effect"
            patch_kwargs[method_side_effect] = requests.HTTPError
    for old_key in list(patch_kwargs.keys()):
        patch_kwargs[f"return_value.{old_key}"] = patch_kwargs.pop(old_key)
    return mock.patch("requests.Session", **patch_kwargs)


class AssertFrameEqualMixin:
    assertEqual: Callable[..., None]

    def assert_frame_equal(self, actual: pd.DataFrame, expected: pd.DataFrame) -> None:
        actual_index = cast(pd.DatetimeIndex, actual.index)
        expected_index = cast(pd.DatetimeIndex, expected.index)
        assert actual_index.tz is not None
        assert expected_index.tz is not None
        self.assertEqual(
            actual_index.tz.utcoffset(None), expected_index.tz.utcoffset(None)
        )
        pd.testing.assert_frame_equal(actual, expected, check_index_type=False)

    def assert_frame_loosely_equal(
        self, actual: pd.DataFrame, expected: pd.DataFrame
    ) -> None:
        actual = copy(actual)
        expected = copy(expected)
        actual_index = cast(pd.DatetimeIndex, actual.index)
        expected_index = cast(pd.DatetimeIndex, expected.index)
        actual.index = actual_index.tz_convert("UTC")
        expected.index = expected_index.tz_convert("UTC")
        pd.testing.assert_frame_equal(actual, expected)
