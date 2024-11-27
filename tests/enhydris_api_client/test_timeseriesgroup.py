from unittest import TestCase

import requests

from enhydris_api_client import EnhydrisApiClient

from . import mock_session


class GetTimeseriesGroupTestCase(TestCase):
    @mock_session(**{"get.return_value.json.return_value": {"hello": "world"}})
    def setUp(self, mock_requests_session):
        self.mock_requests_session = mock_requests_session
        self.client = EnhydrisApiClient("https://mydomain.com")
        self.data = self.client.get_timeseries_group(42, 43)

    def test_makes_request(self):
        self.mock_requests_session.return_value.get.assert_called_once_with(
            "https://mydomain.com/api/stations/42/timeseriesgroups/43/"
        )

    def test_returns_data(self):
        self.assertEqual(self.data, {"hello": "world"})


class PostTimeseriesGroupTestCase(TestCase):
    @mock_session(**{"post.return_value.json.return_value": {"id": 43}})
    def setUp(self, mock_requests_session):
        self.mock_requests_session = mock_requests_session
        self.client = EnhydrisApiClient("https://mydomain.com")
        self.data = self.client.post_timeseries_group(42, data={"precision": 2})

    def test_makes_request(self):
        self.mock_requests_session.return_value.post.assert_called_once_with(
            "https://mydomain.com/api/stations/42/timeseriesgroups/",
            data={"precision": 2},
        )

    def test_returns_id(self):
        self.assertEqual(self.data, 43)


class PutTimeseriesGroupTestCase(TestCase):
    @mock_session()
    def setUp(self, mock_requests_session):
        self.mock_requests_session = mock_requests_session
        self.client = EnhydrisApiClient("https://mydomain.com")
        self.client.put_timeseries_group(42, 43, data={"precision": 2})

    def test_makes_request(self):
        self.mock_requests_session.return_value.put.assert_called_once_with(
            "https://mydomain.com/api/stations/42/timeseriesgroups/43/",
            data={"precision": 2},
        )


class PatchTimeseriesGroupTestCase(TestCase):
    @mock_session()
    def setUp(self, mock_requests_session):
        self.mock_requests_session = mock_requests_session
        self.client = EnhydrisApiClient("https://mydomain.com")
        self.client.patch_timeseries_group(42, 43, data={"precision": 2})

    def test_makes_request(self):
        self.mock_requests_session.return_value.patch.assert_called_once_with(
            "https://mydomain.com/api/stations/42/timeseriesgroups/43/",
            data={"precision": 2},
        )


class DeleteTimeseriesGroupTestCase(TestCase):
    @mock_session()
    def test_makes_request(self, mock_requests_session):
        self.client = EnhydrisApiClient("https://mydomain.com")
        self.client.delete_timeseries_group(42, 43)
        mock_requests_session.return_value.delete.assert_called_once_with(
            "https://mydomain.com/api/stations/42/timeseriesgroups/43/"
        )

    @mock_session(**{"delete.return_value.status_code": 404})
    def test_raises_exception_on_error(self, mock_requests_delete):
        self.client = EnhydrisApiClient("https://mydomain.com")
        with self.assertRaises(requests.HTTPError):
            self.client.delete_timeseries_group(42, 43)
