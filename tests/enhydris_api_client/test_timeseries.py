from unittest import TestCase

import requests

from enhydris_api_client import EnhydrisApiClient

from . import mock_session


class ListTimeseriesTestCase(TestCase):
    @mock_session(
        **{"get.return_value.json.return_value": {"results": [{"hello": "world"}]}}
    )
    def setUp(self, mock_requests_session):
        self.mock_requests_session = mock_requests_session
        self.client = EnhydrisApiClient("https://mydomain.com")
        self.data = self.client.list_timeseries(41, 42)

    def test_makes_request(self):
        self.mock_requests_session.return_value.get.assert_called_once_with(
            "https://mydomain.com/api/stations/41/timeseriesgroups/42/timeseries/"
        )

    def test_returns_data(self):
        self.assertEqual(self.data, [{"hello": "world"}])


class GetTimeseriesTestCase(TestCase):
    @mock_session(**{"get.return_value.json.return_value": {"hello": "world"}})
    def setUp(self, mock_requests_session):
        self.mock_requests_session = mock_requests_session
        self.client = EnhydrisApiClient("https://mydomain.com")
        self.data = self.client.get_timeseries(41, 42, 43)

    def test_makes_request(self):
        self.mock_requests_session.return_value.get.assert_called_once_with(
            "https://mydomain.com/api/stations/41/timeseriesgroups/42/timeseries/43/"
        )

    def test_returns_data(self):
        self.assertEqual(self.data, {"hello": "world"})


class GetStationOrTimeseriesErrorTestCase(TestCase):
    @mock_session(**{"get.return_value.status_code": 404})
    def setUp(self, mock_requests_session):
        self.client = EnhydrisApiClient("https://mydomain.com")

    def test_raises_exception_on_get_station_error(self):
        with self.assertRaises(requests.HTTPError):
            self.data = self.client.get_station(42)

    def test_raises_exception_on_get_timeseries_error(self):
        with self.assertRaises(requests.HTTPError):
            self.data = self.client.get_timeseries(41, 42, 43)


class PostTimeseriesTestCase(TestCase):
    @mock_session(**{"post.return_value.json.return_value": {"id": 43}})
    def setUp(self, mock_requests_session):
        self.mock_requests_session = mock_requests_session
        self.client = EnhydrisApiClient("https://mydomain.com")
        self.data = self.client.post_timeseries(41, 42, data={"location": "Syria"})

    def test_makes_request(self):
        self.mock_requests_session.return_value.post.assert_called_once_with(
            "https://mydomain.com/api/stations/41/timeseriesgroups/42/timeseries/",
            data={"location": "Syria"},
        )

    def test_returns_id(self):
        self.assertEqual(self.data, 43)


class FailedPostTimeseriesTestCase(TestCase):
    @mock_session(**{"post.return_value.status_code": 404})
    def setUp(self, mock_requests_session):
        self.client = EnhydrisApiClient("https://mydomain.com")

    def test_raises_exception_on_error(self):
        with self.assertRaises(requests.HTTPError):
            self.client.post_timeseries(41, 42, data={"location": "Syria"})


class DeleteTimeseriesTestCase(TestCase):
    @mock_session()
    def test_makes_request(self, mock_requests_session):
        self.client = EnhydrisApiClient("https://mydomain.com")
        self.client.delete_timeseries(41, 42, 43)
        mock_requests_session.return_value.delete.assert_called_once_with(
            "https://mydomain.com/api/stations/41/timeseriesgroups/42/timeseries/43/"
        )

    @mock_session(**{"delete.return_value.status_code": 404})
    def test_raises_exception_on_error(self, mock_requests_delete):
        self.client = EnhydrisApiClient("https://mydomain.com")
        with self.assertRaises(requests.HTTPError):
            self.client.delete_timeseries(41, 42, 43)
