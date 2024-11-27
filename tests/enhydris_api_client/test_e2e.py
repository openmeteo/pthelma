import datetime as dt
import json
import os
import textwrap
from io import StringIO
from unittest import TestCase, skipUnless

try:
    from zoneinfo import ZoneInfo
except ImportError:
    from backports.zoneinfo import ZoneInfo

import pandas as pd
import requests

from enhydris_api_client import EnhydrisApiClient
from htimeseries import HTimeseries

from . import AssertFrameEqualMixin, test_timeseries_htimeseries

UTC_PLUS_2 = dt.timezone(dt.timedelta(hours=2))


@skipUnless(
    os.getenv("PTHELMA_TEST_ENHYDRIS_SERVER"), "Set PTHELMA_TEST_ENHYDRIS_SERVER"
)
class EndToEndTestCase(AssertFrameEqualMixin, TestCase):
    """End-to-end test against a real Enhydris instance.
    To execute this test, specify the PTHELMA_TEST_ENHYDRIS_SERVER environment variable
    like this:
        PTHELMA_TEST_ENHYDRIS_SERVER='
            {"base_url": "http://localhost:8001",
             "token": "topsecrettokenkey",
             "owner_id": 9,
             "variable_id": 22,
             "unit_of_measurement_id": 18,
             "station_id": 1403,
             "timeseries_group_id": 513
             }
        '
    This should point to an Enhydris server. Avoid using a production database for
    that; the testing functionality will write objects to the database. Although
    things are normally cleaned up (created objects will be deleted), id serial
    numbers will be affected and things might not be cleaned up if there is an error.

    It's possible that not all items of the above PTHELMA_TEST_ENHYDRIS_SERVER example
    are being used in the test case, but they might be used by other test cases, such
    as in enhydris_cache.
    """

    def setUp(self):
        v = json.loads(os.getenv("PTHELMA_TEST_ENHYDRIS_SERVER"))
        self.token = v["token"]
        self.client = EnhydrisApiClient(v["base_url"], token=self.token)
        self.client.__enter__()
        self.owner_id = v["owner_id"]
        self.variable_id = v["variable_id"]
        self.unit_of_measurement_id = v["unit_of_measurement_id"]

    def tearDown(self):
        self.client.__exit__()

    def test_e2e(self):
        # Verify we're authenticated
        token = self.client.session.headers.get("Authorization")
        self.assertEqual(token, f"token {self.token}")

        # Create a test station
        tmp_station_id = self.client.post_station(
            {
                "name": "My station",
                "copyright_holder": "Joe User",
                "copyright_years": "2019",
                "geom": "POINT(20.94565 39.12102)",
                "original_srid": 4326,
                "owner": self.owner_id,
                "display_timezone": "Etc/GMT-1",
            }
        )

        # Get the test station
        station = self.client.get_station(tmp_station_id)
        self.assertEqual(station["id"], tmp_station_id)
        self.assertEqual(station["name"], "My station")

        # Patch station and verify
        self.client.patch_station(tmp_station_id, {"name": "New name"})
        station = self.client.get_station(tmp_station_id)
        self.assertEqual(station["name"], "New name")

        # Put station and verify
        self.client.put_station(
            tmp_station_id,
            {
                "name": "Newer name",
                "copyright_holder": "Joe User",
                "copyright_years": "2019",
                "geom": "POINT(20.94565 39.12102)",
                "original_srid": 4326,
                "owner": self.owner_id,
            },
        )
        station = self.client.get_station(tmp_station_id)
        self.assertEqual(station["name"], "Newer name")

        # Create a time series group and verify it was created
        self.timeseries_group_id = self.client.post_timeseries_group(
            tmp_station_id,
            data={
                "name": "My time series group",
                "gentity": tmp_station_id,
                "variable": self.variable_id,
                "unit_of_measurement": self.unit_of_measurement_id,
                "precision": 2,
            },
        )
        timeseries_group = self.client.get_timeseries_group(
            tmp_station_id, self.timeseries_group_id
        )
        self.assertEqual(timeseries_group["name"], "My time series group")

        # Create a time series and verify it was created
        self.timeseries_id = self.client.post_timeseries(
            tmp_station_id,
            self.timeseries_group_id,
            data={
                "type": "Regularized",
                "time_step": "10min",
                "timeseries_group": self.timeseries_group_id,
            },
        )
        timeseries = self.client.get_timeseries(
            tmp_station_id, self.timeseries_group_id, self.timeseries_id
        )
        self.assertEqual(timeseries["type"], "Regularized")

        # Post time series data
        self.client.post_tsdata(
            tmp_station_id,
            self.timeseries_group_id,
            self.timeseries_id,
            test_timeseries_htimeseries,
        )

        # Get the last date and check it
        date = self.client.get_ts_end_date(
            tmp_station_id,
            self.timeseries_group_id,
            self.timeseries_id,
        )
        self.assertEqual(date, dt.datetime(2014, 1, 5, 7, 0))

        # Get the last date in a different timezone from the default
        date = self.client.get_ts_end_date(
            tmp_station_id,
            self.timeseries_group_id,
            self.timeseries_id,
            timezone="Etc/GMT-5",
        )
        self.assertEqual(date, dt.datetime(2014, 1, 5, 11, 0))

        # Get all time series data and check it
        hts = self.client.read_tsdata(
            tmp_station_id, self.timeseries_group_id, self.timeseries_id
        )
        try:
            # Compatibility with older Python or pandas versions (such as Python 3.7
            # with pandas 0.23): comparison may fail if tzinfo, although practically the
            # same thing, is a different object
            if hts.data.index.tz.offset == dt.timedelta(0):
                hts.data.index = hts.data.index.tz_convert(dt.timezone.utc)
        except AttributeError:
            pass
        self.assert_frame_loosely_equal(hts.data, test_timeseries_htimeseries.data)

        # The other attributes should have been set too.
        self.assertTrue(hasattr(hts, "variable"))

        # Get part of the time series data and check it
        hts = self.client.read_tsdata(
            tmp_station_id,
            self.timeseries_group_id,
            self.timeseries_id,
            start_date=dt.datetime(2014, 1, 3, 8, 0, tzinfo=UTC_PLUS_2),
            end_date=dt.datetime(2014, 1, 4, 8, 0, tzinfo=UTC_PLUS_2),
            timezone="Etc/GMT-1",
        )
        expected_result = HTimeseries(
            StringIO(
                textwrap.dedent(
                    """\
                    2014-01-03 07:00,13.0,
                    2014-01-04 07:00,14.0,
                    """
                )
            ),
            default_tzinfo=ZoneInfo("Etc/GMT-1"),
        )
        try:
            # Compatibility with older Python or pandas versions (such as Python 3.7
            # with pandas 0.23): comparison may fail if tzinfo, although practically the
            # same thing, is a different object
            if hts.data.index.tz.offset == dt.timedelta(minutes=60):
                hts.data.index = hts.data.index.tz_convert(ZoneInfo("Etc/GMT-1"))
        except AttributeError:
            pass
        pd.testing.assert_frame_equal(hts.data, expected_result.data)

        # Delete the time series and verify
        self.client.delete_timeseries(
            tmp_station_id, self.timeseries_group_id, self.timeseries_id
        )
        with self.assertRaises(requests.HTTPError):
            self.client.get_timeseries(
                tmp_station_id, self.timeseries_group_id, self.timeseries_id
            )

        # Delete station
        self.client.delete_station(tmp_station_id)
        with self.assertRaises(requests.HTTPError):
            self.client.get_station(tmp_station_id)
