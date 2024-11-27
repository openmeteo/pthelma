from unittest import TestCase

import requests

from enhydris_api_client import EnhydrisApiClient

from . import mock_session


class GetStationTestCase(TestCase):
    @mock_session(**{"get.return_value.json.return_value": {"hello": "world"}})
    def setUp(self, mock_requests_session):
        self.mock_requests_session = mock_requests_session
        self.client = EnhydrisApiClient("https://mydomain.com")
        self.data = self.client.get_station(42)

    def test_makes_request(self):
        self.mock_requests_session.return_value.get.assert_called_once_with(
            "https://mydomain.com/api/stations/42/"
        )

    def test_returns_data(self):
        self.assertEqual(self.data, {"hello": "world"})


class PostStationTestCase(TestCase):
    @mock_session(**{"post.return_value.json.return_value": {"id": 42}})
    def setUp(self, mock_requests_session):
        self.mock_requests_session = mock_requests_session
        self.client = EnhydrisApiClient("https://mydomain.com")
        self.data = self.client.post_station(data={"location": "Syria"})

    def test_makes_request(self):
        self.mock_requests_session.return_value.post.assert_called_once_with(
            "https://mydomain.com/api/stations/", data={"location": "Syria"}
        )

    def test_returns_id(self):
        self.assertEqual(self.data, 42)


class PutStationTestCase(TestCase):
    @mock_session()
    def setUp(self, mock_requests_session):
        self.mock_requests_session = mock_requests_session
        self.client = EnhydrisApiClient("https://mydomain.com")
        self.client.put_station(42, data={"location": "Syria"})

    def test_makes_request(self):
        self.mock_requests_session.return_value.put.assert_called_once_with(
            "https://mydomain.com/api/stations/42/", data={"location": "Syria"}
        )


class PatchStationTestCase(TestCase):
    @mock_session()
    def setUp(self, mock_requests_session):
        self.mock_requests_session = mock_requests_session
        self.client = EnhydrisApiClient("https://mydomain.com")
        self.client.patch_station(42, data={"location": "Syria"})

    def test_makes_request(self):
        self.mock_requests_session.return_value.patch.assert_called_once_with(
            "https://mydomain.com/api/stations/42/", data={"location": "Syria"}
        )


class DeleteStationTestCase(TestCase):
    @mock_session()
    def test_makes_request(self, mock_requests_session):
        self.client = EnhydrisApiClient("https://mydomain.com")
        self.client.delete_station(42)
        mock_requests_session.return_value.delete.assert_called_once_with(
            "https://mydomain.com/api/stations/42/"
        )

    @mock_session(**{"delete.return_value.status_code": 404})
    def test_raises_exception_on_error(self, mock_requests_delete):
        self.client = EnhydrisApiClient("https://mydomain.com")
        with self.assertRaises(requests.HTTPError):
            self.client.delete_station(42)
