from unittest import TestCase
from unittest.mock import call

import requests

from enhydris_api_client import EnhydrisApiClient, MalformedResponseError

from . import mock_session


class ListTimeseriesGroupsSinglePageTestCase(TestCase):
    @mock_session()
    def setUp(self, m):
        m.return_value.get.return_value.json.return_value = {
            "count": 2,
            "next": None,
            "previous": None,
            "results": [{"name": "Temperature"}, {"name": "Humidity"}],
        }
        self.mock_session = m
        client = EnhydrisApiClient("https://mydomain.com")
        self.result = client.list_timeseries_groups(station_id=42)

    def test_makes_request(self):
        next(self.result)  # Ensure the request is actually made
        m = self.mock_session
        m.return_value.get.assert_called_once_with(
            "https://mydomain.com/api/stations/42/timeseriesgroups/"
        )

    def test_result(self):
        self.assertEqual(
            list(self.result),
            [{"name": "Temperature"}, {"name": "Humidity"}],
        )


class ListTimeseriesGroupsMultiPageTestCase(TestCase):
    @mock_session()
    def setUp(self, m):
        m.return_value.get.return_value.json.side_effect = [
            {
                "count": 3,
                "next": "https://mydomain.com/api/stations/42/timeseriesgroups/?page=2",
                "previous": None,
                "results": [{"name": "Temperature"}, {"name": "Humidity"}],
            },
            {
                "count": 3,
                "next": None,
                "previous": "https://mydomain.com/api/stations/42/timeseriesgroups/",
                "results": [{"name": "Pressure"}],
            },
        ]
        self.mock_session = m
        client = EnhydrisApiClient("https://mydomain.com")
        self.result = client.list_timeseries_groups(station_id=42)

    def test_requests(self):
        list(self.result)  # Ensure all requests are made
        self.assertEqual(
            self.mock_session.return_value.get.call_args_list,
            [
                call("https://mydomain.com/api/stations/42/timeseriesgroups/"),
                call("https://mydomain.com/api/stations/42/timeseriesgroups/?page=2"),
            ],
        )

    def test_result(self):
        self.assertEqual(
            list(self.result),
            [{"name": "Temperature"}, {"name": "Humidity"}, {"name": "Pressure"}],
        )


class ListTimeseriesGroupsErrorTestCase(TestCase):
    @mock_session(**{"get.return_value.status_code": 500})
    def test_raises_exception_on_error(self, m):
        client = EnhydrisApiClient("https://mydomain.com")
        with self.assertRaises(requests.HTTPError):
            next(client.list_timeseries_groups(station_id=42))

    @mock_session(**{"get.return_value.json.return_value": "not a dict"})
    def test_raises_exception_on_non_json_response(self, m):
        client = EnhydrisApiClient("https://mydomain.com")
        with self.assertRaises(MalformedResponseError):
            next(client.list_timeseries_groups(station_id=42))

    @mock_session(**{"get.return_value.json.return_value": {"no": "expected"}})
    def test_raises_exception_on_unexpected_json(self, m):
        client = EnhydrisApiClient("https://mydomain.com")
        with self.assertRaises(MalformedResponseError):
            next(client.list_timeseries_groups(station_id=42))


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
