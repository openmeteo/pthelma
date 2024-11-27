import datetime as dt
import os
import shutil
import tempfile
import textwrap
from io import StringIO
from unittest import TestCase, mock

from enhydris_api_client import EnhydrisApiClient
from enhydris_cache import TimeseriesCache
from htimeseries import HTimeseries

test_timeseries = {
    "42_all": textwrap.dedent(
        """\
        2014-01-01 08:00,11,
        2014-01-02 08:00,12,
        2014-01-03 08:00,13,
        2014-01-04 08:00,14,
        2014-01-05 08:00,15,
        """
    ),
    "43_all": textwrap.dedent(
        """\
        2014-07-01 08:00,9.11,
        2014-07-02 08:00,9.12,
        2014-07-03 08:00,9.13,
        2014-07-04 08:00,9.14,
        2014-07-05 08:00,9.15,
        """
    ),
}
test_timeseries["42_top"] = "".join(test_timeseries["42_all"].splitlines(True)[:-1])
test_timeseries["43_top"] = "".join(test_timeseries["43_all"].splitlines(True)[:-1])
test_timeseries["42_bottom"] = test_timeseries["42_all"].splitlines(True)[-1]
test_timeseries["43_bottom"] = test_timeseries["43_all"].splitlines(True)[-1]

UTC_PLUS_2 = dt.timezone(dt.timedelta(hours=2))


def mock_read_tsdata(
    station_id, timeseries_group_id, timeseries_id, start_date=None, end_date=None
):
    result = _get_hts_object(timeseries_id, start_date)
    _set_hts_attributes(result, timeseries_id)
    return result


def _get_hts_object(timeseries_id, start_date):
    timeseries_top = HTimeseries(
        StringIO(test_timeseries[f"{timeseries_id}_top"]), default_tzinfo=UTC_PLUS_2
    )
    if start_date is None or start_date < dt.datetime(1, 1, 2, 0, 0, tzinfo=UTC_PLUS_2):
        return timeseries_top
    assert start_date == timeseries_top.data.index[-1] + dt.timedelta(minutes=1)
    result = HTimeseries(
        StringIO(test_timeseries[f"{timeseries_id}_bottom"]), default_tzinfo=UTC_PLUS_2
    )
    return result


def _set_hts_attributes(hts, timeseries_id):
    hts.time_step = "D"
    hts.precision = 0 if timeseries_id == 42 else 2
    hts.comment = "Très importante"


class TimeseriesCacheTestCase(TestCase):
    def setUp(self):
        self.api_client = EnhydrisApiClient("https://mydomain.com")

        # Temporary directory for cache files
        self.tempdir = tempfile.mkdtemp()
        self.savedcwd = os.getcwd()
        os.chdir(self.tempdir)

    def tearDown(self):
        os.chdir(self.savedcwd)
        shutil.rmtree(self.tempdir)

    @mock.patch(
        "enhydris_cache.enhydris_cache.EnhydrisApiClient",
        **{
            "return_value.__enter__.return_value.read_tsdata.side_effect": (
                mock_read_tsdata
            )
        },
    )
    def test_update(self, mock_api_client):

        two_timeseries = [
            {
                "base_url": "https://mydomain.com",
                "station_id": 2,
                "timeseries_group_id": 22,
                "timeseries_id": 42,
                "auth_token": "01234567890abcdefghijklmnopqrstuvwxyz",
                "file": "file1",
            },
            {
                "base_url": "https://mydomain.com",
                "station_id": 3,
                "timeseries_group_id": 33,
                "timeseries_id": 43,
                "auth_token": "01234567890abcdefghijklmnopqrstuvwxyz",
                "file": "file2",
            },
        ]

        # Cache the two timeseries
        cache = TimeseriesCache(two_timeseries)
        cache.update()

        # Check that the cached stuff is what it should be
        with open("file1", newline="\n") as f:
            ts1_before = HTimeseries(f)
        self.assertEqual(ts1_before.time_step, "D")
        c = StringIO()
        ts1_before.write(c)
        self.assertEqual(c.getvalue().replace("\r", ""), test_timeseries["42_top"])
        with open("file2", newline="\n") as f:
            ts2_before = HTimeseries(f)
        self.assertEqual(ts2_before.time_step, "D")
        c = StringIO()
        ts2_before.write(c)
        self.assertEqual(c.getvalue().replace("\r", ""), test_timeseries["43_top"])

        # Update the cache
        cache.update()

        # Check that the cached stuff is what it should be
        with open("file1", newline="\n") as f:
            ts1_after = HTimeseries(f)
        self.assertEqual(ts1_after.time_step, "D")
        c = StringIO()
        ts1_after.write(c)
        self.assertEqual(c.getvalue().replace("\r", ""), test_timeseries["42_all"])
        with open("file2", newline="\n") as f:
            ts2_after = HTimeseries(f)
        self.assertEqual(ts2_after.time_step, "D")
        c = StringIO()
        ts2_after.write(c)
        self.assertEqual(c.getvalue().replace("\r", ""), test_timeseries["43_all"])

        # Check that the time series comments are the same before and after
        self.assertEqual(ts1_before.comment, ts1_after.comment)
        self.assertEqual(ts2_before.comment, ts2_after.comment)
