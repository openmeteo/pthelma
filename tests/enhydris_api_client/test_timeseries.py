from __future__ import annotations

from unittest import TestCase, mock

import requests

from enhydris_api_client import EnhydrisApiClient

from . import mock_session


class ListTimeseriesTestCase(TestCase):
    def setUp(self) -> None:
        self.session_patcher = mock_session(
            **{"get.return_value.json.return_value": {"results": [{"hello": "world"}]}}
        )
        self.mock_requests_session = self.session_patcher.start()
        self.client = EnhydrisApiClient("https://mydomain.com")
        self.data = self.client.list_timeseries(41, 42)

    def tearDown(self) -> None:
        self.session_patcher.stop()

    def test_makes_request(self) -> None:
        self.mock_requests_session.return_value.get.assert_called_once_with(
            "https://mydomain.com/api/stations/41/timeseriesgroups/42/timeseries/"
        )

    def test_returns_data(self) -> None:
        self.assertEqual(self.data, [{"hello": "world"}])


class GetTimeseriesTestCase(TestCase):
    def setUp(self) -> None:
        self.session_patcher = mock_session(
            **{"get.return_value.json.return_value": {"hello": "world"}}
        )
        self.mock_requests_session = self.session_patcher.start()
        self.client = EnhydrisApiClient("https://mydomain.com")
        self.data = self.client.get_timeseries(41, 42, 43)

    def tearDown(self) -> None:
        self.session_patcher.stop()

    def test_makes_request(self) -> None:
        self.mock_requests_session.return_value.get.assert_called_once_with(
            "https://mydomain.com/api/stations/41/timeseriesgroups/42/timeseries/43/"
        )

    def test_returns_data(self) -> None:
        self.assertEqual(self.data, {"hello": "world"})


class GetStationOrTimeseriesErrorTestCase(TestCase):
    def setUp(self) -> None:
        with mock_session(**{"get.return_value.status_code": 404}):
            self.client = EnhydrisApiClient("https://mydomain.com")

    def test_raises_exception_on_get_station_error(self) -> None:
        with self.assertRaises(requests.HTTPError):
            self.data = self.client.get_station(42)

    def test_raises_exception_on_get_timeseries_error(self) -> None:
        with self.assertRaises(requests.HTTPError):
            self.data = self.client.get_timeseries(41, 42, 43)


class PostTimeseriesTestCase(TestCase):
    def setUp(self) -> None:
        self.session_patcher = mock_session(
            **{"post.return_value.json.return_value": {"id": 43}}
        )
        self.mock_requests_session = self.session_patcher.start()
        self.client = EnhydrisApiClient("https://mydomain.com")
        self.data = self.client.post_timeseries(41, 42, data={"location": "Syria"})

    def tearDown(self) -> None:
        self.session_patcher.stop()

    def test_makes_request(self) -> None:
        self.mock_requests_session.return_value.post.assert_called_once_with(
            "https://mydomain.com/api/stations/41/timeseriesgroups/42/timeseries/",
            data={"location": "Syria"},
        )

    def test_returns_id(self) -> None:
        self.assertEqual(self.data, 43)


@mock_session()
class PutTimeseriesTestCase(TestCase):
    def test_makes_request(self, m: mock.MagicMock) -> None:
        client = EnhydrisApiClient("https://mydomain.com")
        client.put_timeseries(41, 42, 43, data={"location": "Syria"})
        m.return_value.put.assert_called_once_with(
            "https://mydomain.com/api/stations/41/timeseriesgroups/42/timeseries/43/",
            data={"location": "Syria"},
        )


class FailedPostTimeseriesTestCase(TestCase):
    @mock_session(**{"post.return_value.status_code": 404})
    def test_raises_exception_on_error(self, m: mock.MagicMock) -> None:
        self.client = EnhydrisApiClient("https://mydomain.com")
        with self.assertRaises(requests.HTTPError):
            self.client.post_timeseries(41, 42, data={"location": "Syria"})


class DeleteTimeseriesTestCase(TestCase):
    @mock_session()
    def test_makes_request(self, mock_requests_session: mock.MagicMock) -> None:
        self.client = EnhydrisApiClient("https://mydomain.com")
        self.client.delete_timeseries(41, 42, 43)
        mock_requests_session.return_value.delete.assert_called_once_with(
            "https://mydomain.com/api/stations/41/timeseriesgroups/42/timeseries/43/"
        )

    @mock_session(**{"delete.return_value.status_code": 404})
    def test_raises_exception_on_error(
        self, mock_requests_delete: mock.MagicMock
    ) -> None:
        self.client = EnhydrisApiClient("https://mydomain.com")
        with self.assertRaises(requests.HTTPError):
            self.client.delete_timeseries(41, 42, 43)
