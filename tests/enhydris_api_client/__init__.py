import datetime as dt
import textwrap
from copy import copy
from io import StringIO
from unittest import mock

import pandas as pd
import requests

from htimeseries import HTimeseries

test_timeseries_csv = textwrap.dedent(
    """\
    2014-01-01 08:00,11.0,
    2014-01-02 08:00,12.0,
    2014-01-03 08:00,13.0,
    2014-01-04 08:00,14.0,
    2014-01-05 08:00,15.0,
    """
)
test_timeseries_htimeseries = HTimeseries(
    StringIO(test_timeseries_csv), default_tzinfo=dt.timezone(dt.timedelta(hours=2))
)
test_timeseries_csv_top = "".join(test_timeseries_csv.splitlines(keepends=True)[:-1])
test_timeseries_csv_bottom = test_timeseries_csv.splitlines(keepends=True)[-1]


def mock_session(**kwargs):
    """Mock requests.Session.

    Returns
        @mock.patch("requests.Session", modified_kwargs)

    However, it first tampers with kwargs in order to achieve the following:
    - It adds a leading "return_value." to the kwargs; so you don't need to specify,
      for example, "return_value.get.return_value", you just specify "get.return_value".
    - If kwargs doesn't contain "get.return_value.status_code", it adds
      a return code of 200. Likewise for post, put and patch. For delete it's 204.
    - If "get.return_value.status_code" is not between 200 and 399,
      then raise_for_status() will raise HTTPError. Likewise for the other methods.
    """
    for method in ("get", "post", "put", "patch", "delete"):
        default_value = 204 if method == "delete" else 200
        c = kwargs.setdefault(method + ".return_value.status_code", default_value)
        if c < 200 or c >= 400:
            method_side_effect = method + ".return_value.raise_for_status.side_effect"
            kwargs[method_side_effect] = requests.HTTPError
    for old_key in list(kwargs.keys()):
        kwargs["return_value." + old_key] = kwargs.pop(old_key)
    return mock.patch("requests.Session", **kwargs)


class AssertFrameEqualMixin:
    def assert_frame_equal(self, actual, expected):
        self.assertEqual(
            actual.index.tz.utcoffset(None), expected.index.tz.utcoffset(None)
        )
        pd.testing.assert_frame_equal(actual, expected, check_index_type=False)

    def assert_frame_loosely_equal(self, actual, expected):
        actual = copy(actual)
        expected = copy(expected)
        actual.index = actual.index.tz_convert("UTC")
        expected.index = expected.index.tz_convert("UTC")
        pd.testing.assert_frame_equal(actual, expected)
