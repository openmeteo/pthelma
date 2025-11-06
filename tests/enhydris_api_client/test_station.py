from __future__ import annotations

from unittest import TestCase
from unittest.mock import MagicMock, call

import requests

from enhydris_api_client import EnhydrisApiClient, MalformedResponseError

from . import mock_session


class ListStationsSinglePageTestCase(TestCase):
    def setUp(self) -> None:  # type: ignore[misc]
        self.session_patcher = mock_session(
            **{
                "get.return_value.json.return_value": {
                    "count": 2,
                    "next": None,
                    "previous": None,
                    "results": [{"name": "Hobbiton"}, {"name": "Rivendell"}],
                }
            }
        )
        self.mock_session = self.session_patcher.start()
        client = EnhydrisApiClient("https://mydomain.com")
        self.result = client.list_stations()

    def tearDown(self) -> None:
        self.session_patcher.stop()

    def test_makes_request(self) -> None:
        next(self.result)  # Ensure the request is actually made
        m = self.mock_session
        m.return_value.get.assert_called_once_with("https://mydomain.com/api/stations/")

    def test_result(self) -> None:
        self.assertEqual(
            list(self.result),
            [{"name": "Hobbiton"}, {"name": "Rivendell"}],
        )


@mock_session(
    **{
        "get.return_value.json.return_value": {
            "count": 2,
            "next": None,
            "previous": None,
            "results": [{"name": "Hobbiton"}, {"name": "Rivendell"}],
        }
    }
)
class ListStationsWithQueryTestCase(TestCase):
    def test_makes_request_with_query(self, m: MagicMock) -> None:
        client = EnhydrisApiClient("https://mydomain.com")
        result = client.list_stations(query_string="hello world")
        next(result)  # Ensure the request is actually made
        m.return_value.get.assert_called_once_with(
            "https://mydomain.com/api/stations/?q=hello+world"
        )


class ListStationsMultiPageTestCase(TestCase):
    def setUp(self) -> None:  # type: ignore[misc]
        self.session_patcher = mock_session(
            **{
                "get.return_value.json.side_effect": [
                    {
                        "count": 3,
                        "next": "https://mydomain.com/api/stations/?page=2",
                        "previous": None,
                        "results": [{"name": "Hobbiton"}, {"name": "Rivendell"}],
                    },
                    {
                        "count": 3,
                        "next": None,
                        "previous": "https://mydomain.com/api/stations/",
                        "results": [{"name": "Mordor"}],
                    },
                ]
            }
        )
        self.mock_session = self.session_patcher.start()
        client = EnhydrisApiClient("https://mydomain.com")
        self.result = client.list_stations()

    def tearDown(self) -> None:
        self.session_patcher.stop()

    def test_requests(self) -> None:
        list(self.result)  # Ensure all requests are made
        self.assertEqual(
            self.mock_session.return_value.get.call_args_list,
            [
                call("https://mydomain.com/api/stations/"),
                call("https://mydomain.com/api/stations/?page=2"),
            ],
        )

    def test_result(self) -> None:
        self.assertEqual(
            list(self.result),
            [{"name": "Hobbiton"}, {"name": "Rivendell"}, {"name": "Mordor"}],
        )


class ListStationsErrorTestCase(TestCase):
    @mock_session(**{"get.return_value.status_code": 500})
    def test_raises_exception_on_error(self, m: MagicMock) -> None:
        client = EnhydrisApiClient("https://mydomain.com")
        with self.assertRaises(requests.HTTPError):
            next(client.list_stations())

    @mock_session(**{"get.return_value.json.return_value": "not a dict"})
    def test_raises_exception_on_non_json_response(self, m: MagicMock) -> None:
        client = EnhydrisApiClient("https://mydomain.com")
        with self.assertRaises(MalformedResponseError):
            next(client.list_stations())

    @mock_session(**{"get.return_value.json.return_value": {"no": "expected"}})
    def test_raises_exception_on_unexpected_json(self, m: MagicMock) -> None:
        client = EnhydrisApiClient("https://mydomain.com")
        with self.assertRaises(MalformedResponseError):
            next(client.list_stations())


class GetStationTestCase(TestCase):
    def setUp(self) -> None:
        self.session_patcher = mock_session(
            **{"get.return_value.json.return_value": {"hello": "world"}}
        )
        self.mock_requests_session = self.session_patcher.start()
        self.client = EnhydrisApiClient("https://mydomain.com")
        self.data = self.client.get_station(42)

    def tearDown(self) -> None:
        self.session_patcher.stop()

    def test_makes_request(self) -> None:
        self.mock_requests_session.return_value.get.assert_called_once_with(
            "https://mydomain.com/api/stations/42/"
        )

    def test_returns_data(self) -> None:
        self.assertEqual(self.data, {"hello": "world"})


class PostStationTestCase(TestCase):
    def setUp(self) -> None:
        self.session_patcher = mock_session(
            **{"post.return_value.json.return_value": {"id": 42}}
        )
        self.mock_requests_session = self.session_patcher.start()
        self.client = EnhydrisApiClient("https://mydomain.com")
        self.data = self.client.post_station(data={"location": "Syria"})

    def tearDown(self) -> None:
        self.session_patcher.stop()

    def test_makes_request(self) -> None:
        self.mock_requests_session.return_value.post.assert_called_once_with(
            "https://mydomain.com/api/stations/", data={"location": "Syria"}
        )

    def test_returns_id(self) -> None:
        self.assertEqual(self.data, 42)


class PutStationTestCase(TestCase):
    @mock_session()
    def test_makes_request(self, m: MagicMock) -> None:
        self.client = EnhydrisApiClient("https://mydomain.com")
        self.client.put_station(42, data={"location": "Syria"})
        m.return_value.put.assert_called_once_with(
            "https://mydomain.com/api/stations/42/", data={"location": "Syria"}
        )


class PatchStationTestCase(TestCase):
    @mock_session()
    def test_makes_request(self, m: MagicMock) -> None:
        self.client = EnhydrisApiClient("https://mydomain.com")
        self.client.patch_station(42, data={"location": "Syria"})
        m.return_value.patch.assert_called_once_with(
            "https://mydomain.com/api/stations/42/", data={"location": "Syria"}
        )


class DeleteStationTestCase(TestCase):
    @mock_session()
    def test_makes_request(self, mock_requests_session: MagicMock) -> None:
        self.client = EnhydrisApiClient("https://mydomain.com")
        self.client.delete_station(42)
        mock_requests_session.return_value.delete.assert_called_once_with(
            "https://mydomain.com/api/stations/42/"
        )

    @mock_session(**{"delete.return_value.status_code": 404})
    def test_raises_exception_on_error(self, mock_requests_delete: MagicMock) -> None:
        self.client = EnhydrisApiClient("https://mydomain.com")
        with self.assertRaises(requests.HTTPError):
            self.client.delete_station(42)
