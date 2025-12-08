from __future__ import annotations

import datetime as dt
from copy import copy
from io import StringIO
from typing import Any, Optional, cast
from unittest import TestCase, mock

import pandas as pd
import requests

from enhydris_api_client import EnhydrisApiClient
from htimeseries import HTimeseries

from . import (
    AssertFrameEqualMixin,
    mock_session,
    test_timeseries_csv,
    test_timeseries_csv_bottom,
    test_timeseries_htimeseries,
)

TEST_TIMESERIES_HTS = f"Timezone=+0200\r\n\r\n{test_timeseries_csv}"


@mock_session(**{"get.return_value.text": TEST_TIMESERIES_HTS})
class ReadTsDataTestCase(TestCase, AssertFrameEqualMixin):
    url = "http://example.com/api/stations/41/timeseriesgroups/42/timeseries/43/data/"

    def _read_tsdata(self, **extra_args: Any) -> HTimeseries:
        self.client = EnhydrisApiClient("http://example.com")
        return self.client.read_tsdata(41, 42, 43, **extra_args)

    def test_makes_request(self, m: mock.MagicMock) -> None:
        self._read_tsdata()
        m.return_value.get.assert_called_once_with(
            self.url,
            params={
                "fmt": "hts",
                "start_date": None,
                "end_date": None,
                "timezone": None,
            },
        )

    def test_returns_data(self, m: mock.MagicMock) -> None:
        ahts = self._read_tsdata()
        self.assert_frame_equal(ahts.data, test_timeseries_htimeseries.data)

    def test_uses_timezone(self, m: mock.MagicMock) -> None:
        self._read_tsdata(timezone="UTC")
        m.return_value.get.assert_called_once_with(
            self.url,
            params={
                "fmt": "hts",
                "start_date": None,
                "end_date": None,
                "timezone": "UTC",
            },
        )


class ReadTsDataWithStartAndEndDateTestCase(TestCase, AssertFrameEqualMixin):
    def setUp(self) -> None:
        self.session_patcher = mock_session(
            **{"get.return_value.text": TEST_TIMESERIES_HTS}
        )
        self.mock_session = self.session_patcher.start()
        self.client = EnhydrisApiClient("https://mydomain.com")

    def tearDown(self) -> None:
        self.session_patcher.stop()

    def _make_request(
        self, start_tzinfo: Optional[dt.tzinfo], end_tzinfo: Optional[dt.tzinfo]
    ) -> None:
        self.data = self.client.read_tsdata(
            41,
            42,
            43,
            start_date=dt.datetime(2019, 6, 12, 0, 0, tzinfo=start_tzinfo),
            end_date=dt.datetime(2019, 6, 13, 15, 25, tzinfo=end_tzinfo),
        )

    def test_makes_request(self) -> None:
        self._make_request(dt.timezone.utc, dt.timezone.utc)
        self.mock_session.return_value.get.assert_called_once_with(
            "https://mydomain.com/api/stations/41/timeseriesgroups/42/timeseries/43/"
            "data/",
            params={
                "fmt": "hts",
                "start_date": "2019-06-12T00:00:00+00:00",
                "end_date": "2019-06-13T15:25:00+00:00",
                "timezone": None,
            },
        )

    def test_returns_data(self) -> None:
        self._make_request(dt.timezone.utc, dt.timezone.utc)
        self.assert_frame_equal(self.data.data, test_timeseries_htimeseries.data)

    def test_checks_that_start_date_is_aware(self) -> None:
        with self.assertRaises(ValueError):
            self._make_request(None, dt.timezone.utc)

    def test_checks_that_end_date_is_aware(self) -> None:
        with self.assertRaises(ValueError):
            self._make_request(dt.timezone.utc, None)


class ReadEmptyTsDataTestCase(TestCase, AssertFrameEqualMixin):
    @mock_session(**{"get.return_value.text": ""})
    def test_returns_data(self, mock_requests_session: mock.MagicMock) -> None:
        self.client = EnhydrisApiClient("https://mydomain.com")
        self.data = self.client.read_tsdata(41, 42, 43)
        self.assert_frame_equal(self.data.data, HTimeseries().data)


class ReadTsDataErrorTestCase(TestCase):
    @mock_session(**{"get.return_value.status_code": 404})
    def test_raises_exception_on_error(
        self, mock_requests_session: mock.MagicMock
    ) -> None:
        self.client = EnhydrisApiClient("https://mydomain.com")
        with self.assertRaises(requests.HTTPError):
            self.client.read_tsdata(41, 42, 43)


class PostTsDataTestCase(TestCase):
    @mock_session()
    def test_makes_request(self, mock_requests_session: mock.MagicMock) -> None:
        client = EnhydrisApiClient("https://mydomain.com")
        client.post_tsdata(41, 42, 43, test_timeseries_htimeseries)
        f = StringIO()
        data = copy(test_timeseries_htimeseries.data)
        index = cast(pd.DatetimeIndex, data.index)
        data.index = index.tz_convert("UTC")
        data.to_csv(f, header=False)
        mock_requests_session.return_value.post.assert_called_once_with(
            "https://mydomain.com/api/stations/41/timeseriesgroups/42/timeseries/43/"
            "data/",
            data={
                "timeseries_records": f.getvalue(),
                "timezone": "UTC",
                "mode": "append",
            },
        )

    @mock_session()
    def test_insert_mode(self, mock_requests_session: mock.MagicMock) -> None:
        client = EnhydrisApiClient("https://mydomain.com")
        client.post_tsdata(41, 42, 43, test_timeseries_htimeseries, mode="insert")
        f = StringIO()
        data = copy(test_timeseries_htimeseries.data)
        index = cast(pd.DatetimeIndex, data.index)
        data.index = index.tz_convert("UTC")
        data.to_csv(f, header=False)
        mock_requests_session.return_value.post.assert_called_once_with(
            "https://mydomain.com/api/stations/41/timeseriesgroups/42/timeseries/43/"
            "data/",
            data={
                "timeseries_records": f.getvalue(),
                "timezone": "UTC",
                "mode": "insert",
            },
        )

    @mock_session(**{"post.return_value.status_code": 404})
    def test_raises_exception_on_error(
        self, mock_requests_session: mock.MagicMock
    ) -> None:
        client = EnhydrisApiClient("https://mydomain.com")
        with self.assertRaises(requests.HTTPError):
            client.post_tsdata(41, 42, 43, test_timeseries_htimeseries)


@mock_session(**{"get.return_value.text": test_timeseries_csv_bottom})
class GetTsEndDateTestCase(TestCase):
    url = "http://mydom.com/api/stations/41/timeseriesgroups/42/timeseries/43/bottom/"

    def _get_ts_end_date(self, **extra_args: Any) -> Optional[dt.datetime]:
        self.client = EnhydrisApiClient("http://mydom.com")
        return self.client.get_ts_end_date(41, 42, 43, **extra_args)

    def test_makes_request(self, m: mock.MagicMock) -> None:
        self._get_ts_end_date()
        m.return_value.get.assert_called_once_with(self.url, params={"timezone": None})

    def test_returns_date(self, m: mock.MagicMock) -> None:
        result = self._get_ts_end_date()
        self.assertEqual(result, dt.datetime(2014, 1, 5, 8, 0))

    def test_uses_timezone(self, m: mock.MagicMock) -> None:
        self._get_ts_end_date(timezone="Etc/GMT-2")
        m.return_value.get.assert_called_once_with(
            self.url, params={"timezone": "Etc/GMT-2"}
        )


class GetTsEndDateErrorTestCase(TestCase):
    @mock_session(**{"get.return_value.status_code": 404})
    def test_checks_response_code(self, mock_requests_session: mock.MagicMock) -> None:
        client = EnhydrisApiClient("https://mydomain.com")
        with self.assertRaises(requests.HTTPError):
            client.get_ts_end_date(41, 42, 43)


class GetTsEndDateEmptyTestCase(TestCase):
    @mock_session(**{"get.return_value.text": ""})
    def test_returns_date(self, mock_requests_session: mock.MagicMock) -> None:
        client = EnhydrisApiClient("https://mydomain.com")
        date = client.get_ts_end_date(41, 42, 43)
        self.assertIsNone(date)
