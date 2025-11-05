from __future__ import annotations

import datetime as dt
import textwrap
from io import StringIO
from typing import Any, Iterable
from unittest import TestCase
from zoneinfo import ZoneInfo

from htimeseries import HTimeseries
from rocc import Threshold, rocc


class RoccTestCase(TestCase):
    test_data: str = textwrap.dedent(
        """\
        2020-10-06 14:30,24.0,
        2020-10-06 14:40,25.0,
        2020-10-06 14:50,36.0,SOMEFLAG
        2020-10-06 15:01,50.0,
        2020-10-06 15:21,55.0,
        2020-10-06 15:31,65.0,
        2020-10-06 15:41,75.0,
        2020-10-06 15:51,70.0,
        """
    )

    def setUp(self) -> None:
        self.ahtimeseries: HTimeseries = HTimeseries(
            StringIO(self.test_data), default_tzinfo=ZoneInfo("Etc/GMT-2")
        )
        self.ahtimeseries.precision = 1
        self.return_value: list[str] = []

    def _run_rocc(self, flag: str | None) -> None:
        self.return_value = rocc(
            timeseries=self.ahtimeseries,
            thresholds=(
                Threshold("10min", 10),
                Threshold("20min", 15),
                Threshold("h", 40),
            ),
            flag=flag,
        )

    def test_calculation(self) -> None:
        self._run_rocc(flag="TEMPORAL")
        f: StringIO = StringIO()
        self.ahtimeseries.write(f)
        result = f.getvalue().replace("\r\n", "\n")
        self.assertEqual(
            result,
            textwrap.dedent(
                """\
                2020-10-06 14:30,24.0,
                2020-10-06 14:40,25.0,
                2020-10-06 14:50,36.0,SOMEFLAG TEMPORAL
                2020-10-06 15:01,50.0,
                2020-10-06 15:21,55.0,
                2020-10-06 15:31,65.0,
                2020-10-06 15:41,75.0,TEMPORAL
                2020-10-06 15:51,70.0,
                """
            ),
        )

    def test_return_value(self) -> None:
        self._run_rocc(flag="TEMPORAL")
        self.assertEqual(len(self.return_value), 2)
        self.assertEqual(
            self.return_value[0], "2020-10-06T14:50  +11.0 in 10min (> 10.0)"
        )
        self.assertEqual(
            self.return_value[1], "2020-10-06T15:41  +20.0 in 20min (> 15.0)"
        )

    def test_value_dtype(self) -> None:
        self._run_rocc(flag="TEMPORAL")
        expected_dtype: Any = HTimeseries().data["value"].dtype
        self.assertEqual(self.ahtimeseries.data["value"].dtype, expected_dtype)

    def test_flags_dtype(self) -> None:
        self._run_rocc(flag="TEMPORAL")
        expected_dtype: Any = HTimeseries().data["flags"].dtype
        self.assertEqual(self.ahtimeseries.data["flags"].dtype, expected_dtype)

    def test_empty_flag(self) -> None:
        self._run_rocc(flag=None)
        f: StringIO = StringIO()
        self.ahtimeseries.write(f)
        result = f.getvalue().replace("\r\n", "\n")
        self.assertEqual(result, self.test_data)


class RoccNegativeTestCase(TestCase):
    test_data: str = textwrap.dedent(
        """\
        2020-10-06 14:30,24.0,
        2020-10-06 14:40,25.0,
        2020-10-06 14:50,36.0,SOMEFLAG
        2020-10-06 15:01,50.0,
        2020-10-06 15:21,55.0,
        2020-10-06 15:31,65.0,
        2020-10-06 15:41,75.0,
        2020-10-06 15:51,70.0,
        """
    )

    def setUp(self) -> None:
        self.ahtimeseries: HTimeseries = HTimeseries(
            StringIO(self.test_data), default_tzinfo=ZoneInfo("Etc/GMT-2")
        )
        self.ahtimeseries.precision = 1
        self.return_value: list[str] = []

    def _run_rocc(self, flag: str | None) -> None:
        self.return_value = rocc(
            timeseries=self.ahtimeseries,
            thresholds=(
                Threshold("10min", 10),
                Threshold("10min", -4),
            ),
            flag=flag,
        )

    def test_calculation(self) -> None:
        self._run_rocc(flag="TEMPORAL")
        f = StringIO()
        self.ahtimeseries.write(f)
        result = f.getvalue().replace("\r\n", "\n")
        self.assertEqual(
            result,
            textwrap.dedent(
                """\
                2020-10-06 14:30,24.0,
                2020-10-06 14:40,25.0,
                2020-10-06 14:50,36.0,SOMEFLAG TEMPORAL
                2020-10-06 15:01,50.0,
                2020-10-06 15:21,55.0,
                2020-10-06 15:31,65.0,
                2020-10-06 15:41,75.0,
                2020-10-06 15:51,70.0,TEMPORAL
                """
            ),
        )

    def test_return_value(self) -> None:
        self._run_rocc(flag="TEMPORAL")
        self.assertEqual(len(self.return_value), 2)
        self.assertEqual(
            self.return_value[0], "2020-10-06T14:50  +11.0 in 10min (> 10.0)"
        )
        self.assertEqual(
            self.return_value[1], "2020-10-06T15:51  -5.0 in 10min (< -4.0)"
        )


class RoccSymmetricTestCase(TestCase):
    test_data: str = textwrap.dedent(
        """\
        2020-10-06 14:30,76.0,
        2020-10-06 14:40,75.0,SOMEFLAG
        2020-10-06 14:50,64.0,SOMEFLAG
        2020-10-06 15:01,50,
        2020-10-06 15:21,45.0,
        2020-10-06 15:31,35.0,
        2020-10-06 15:41,25.0,
        2020-10-06 15:51,30.0,
        """
    )

    def setUp(self) -> None:
        self.ahtimeseries: HTimeseries = HTimeseries(
            StringIO(self.test_data), default_tzinfo=ZoneInfo("Etc/GMT-2")
        )
        self.ahtimeseries.precision = 1

    def test_without_symmetric(self) -> None:
        rocc(
            timeseries=self.ahtimeseries,
            thresholds=(
                Threshold("10min", 10),
                Threshold("20min", 15),
                Threshold("h", 40),
            ),
        )
        f = StringIO()
        self.ahtimeseries.write(f)
        result = f.getvalue().replace("\r\n", "\n")
        self.assertEqual(
            result,
            textwrap.dedent(
                """\
                2020-10-06 14:30,76.0,
                2020-10-06 14:40,75.0,SOMEFLAG
                2020-10-06 14:50,64.0,SOMEFLAG
                2020-10-06 15:01,50.0,
                2020-10-06 15:21,45.0,
                2020-10-06 15:31,35.0,
                2020-10-06 15:41,25.0,
                2020-10-06 15:51,30.0,
                """
            ),
        )

    def test_with_symmetric(self) -> None:
        output: list[str] = rocc(
            timeseries=self.ahtimeseries,
            thresholds=(  # Keep in strange order to test for possible errors
                Threshold("20min", -15),
                Threshold("h", 40),
                Threshold("10min", 10),
            ),
            symmetric=True,
        )
        f = StringIO()
        self.ahtimeseries.write(f)
        result = f.getvalue().replace("\r\n", "\n")
        self.assertEqual(
            result,
            textwrap.dedent(
                """\
                2020-10-06 14:30,76.0,
                2020-10-06 14:40,75.0,SOMEFLAG
                2020-10-06 14:50,64.0,SOMEFLAG TEMPORAL
                2020-10-06 15:01,50.0,
                2020-10-06 15:21,45.0,
                2020-10-06 15:31,35.0,
                2020-10-06 15:41,25.0,TEMPORAL
                2020-10-06 15:51,30.0,
                """
            ),
        )
        self.assertEqual(
            output,
            [
                "2020-10-06T14:50  -11.0 in 10min (< -10.0)",
                "2020-10-06T15:41  -20.0 in 20min (< -15.0)",
            ],
        )

    def test_symmetric_return_value(self) -> None:
        return_value: list[str] = rocc(
            timeseries=self.ahtimeseries,
            thresholds=(
                Threshold("10min", 10),
                Threshold("20min", 15),
                Threshold("h", 40),
            ),
            symmetric=True,
        )
        self.assertEqual(len(return_value), 2)
        self.assertEqual(return_value[0], "2020-10-06T14:50  -11.0 in 10min (< -10.0)")
        self.assertEqual(return_value[1], "2020-10-06T15:41  -20.0 in 20min (< -15.0)")


class RoccEmptyCase(TestCase):
    def test_with_empty(self) -> None:
        ahtimeseries: HTimeseries = HTimeseries()
        rocc(timeseries=ahtimeseries, thresholds=[Threshold("10min", 10)])
        self.assertTrue(ahtimeseries.data.empty)


class RoccImpliedThresholdsTestCase(TestCase):
    def _create_htimeseries(self, test_data: str) -> None:
        self.ahtimeseries: HTimeseries = HTimeseries(
            StringIO(test_data), default_tzinfo=dt.timezone.utc
        )
        self.ahtimeseries.precision = 2
        self.return_value: list[str] = []

    def _run_rocc(
        self, thresholds: Iterable[Threshold], symmetric: bool = False
    ) -> str:
        self.return_value = rocc(
            timeseries=self.ahtimeseries, thresholds=thresholds, symmetric=symmetric
        )
        f = StringIO()
        self.ahtimeseries.write(f)
        result = f.getvalue().replace("\r\n", "\n")
        return result

    def test_positive_ok(self) -> None:
        test_data = textwrap.dedent(
            """\
            2020-10-06 14:30,25.00,
            2020-10-06 15:00,49.99,
            """
        )
        self._create_htimeseries(test_data)
        result: str = self._run_rocc(
            thresholds=(
                Threshold("10min", 10),
                Threshold("20min", 15),
            ),
        )
        self.assertEqual(
            result,
            textwrap.dedent(
                """\
                2020-10-06 14:30,25.00,
                2020-10-06 15:00,49.99,
                """
            ),
        )

    def test_positive_not_ok(self) -> None:
        test_data = textwrap.dedent(
            """\
            2020-10-06 14:30,25.00,
            2020-10-06 15:00,50.01,
            """
        )
        self._create_htimeseries(test_data)
        result: str = self._run_rocc(
            thresholds=(
                Threshold("10min", 10),
                Threshold("20min", 15),
            ),
        )
        self.assertEqual(
            result,
            textwrap.dedent(
                """\
                2020-10-06 14:30,25.00,
                2020-10-06 15:00,50.01,TEMPORAL
                """
            ),
        )

    def test_negative_ok(self) -> None:
        test_data = textwrap.dedent(
            """\
            2020-10-06 14:30,75.00,
            2020-10-06 15:00,50.01,
            """
        )
        self._create_htimeseries(test_data)
        result: str = self._run_rocc(
            thresholds=(
                Threshold("10min", -10),
                Threshold("20min", -15),
            ),
        )
        self.assertEqual(
            result,
            textwrap.dedent(
                """\
                2020-10-06 14:30,75.00,
                2020-10-06 15:00,50.01,
                """
            ),
        )

    def test_negative_not_ok(self) -> None:
        test_data = textwrap.dedent(
            """\
            2020-10-06 14:30,75.00,
            2020-10-06 15:00,49.99,
            """
        )
        self._create_htimeseries(test_data)
        result: str = self._run_rocc(
            thresholds=(
                Threshold("10min", -10),
                Threshold("20min", -15),
            ),
        )
        self.assertEqual(
            result,
            textwrap.dedent(
                """\
                2020-10-06 14:30,75.00,
                2020-10-06 15:00,49.99,TEMPORAL
                """
            ),
        )

    def test_symmetric_ok(self) -> None:
        test_data = textwrap.dedent(
            """\
            2020-10-06 14:30,50.00,
            2020-10-06 15:00,74.99,
            """
        )
        self._create_htimeseries(test_data)
        result: str = self._run_rocc(
            thresholds=(
                Threshold("10min", 10),
                Threshold("20min", -15),
            ),
            symmetric=True,
        )
        self.assertEqual(
            result,
            textwrap.dedent(
                """\
                2020-10-06 14:30,50.00,
                2020-10-06 15:00,74.99,
                """
            ),
        )

    def test_symmetric_not_ok(self) -> None:
        test_data = textwrap.dedent(
            """\
            2020-10-06 14:30,75.00,
            2020-10-06 15:00,49.99,
            """
        )
        self._create_htimeseries(test_data)
        result: str = self._run_rocc(
            thresholds=(
                Threshold("10min", 10),
                Threshold("20min", -15),
            ),
            symmetric=True,
        )
        self.assertEqual(
            result,
            textwrap.dedent(
                """\
                2020-10-06 14:30,75.00,
                2020-10-06 15:00,49.99,TEMPORAL
                """
            ),
        )

    def test_compare_to_previous_not_null_record(self) -> None:
        test_data = textwrap.dedent(
            """\
            2023-10-13 08:40,12.3,
            2023-10-13 09:20,,RANGE
            2023-10-13 09:30,-6.8,
            """
        )
        self._create_htimeseries(test_data)
        result: str = self._run_rocc(
            thresholds=(Threshold("10min", 1),),
            symmetric=True,
        )
        self.assertEqual(
            result,
            textwrap.dedent(
                """\
                2023-10-13 08:40,12.30,
                2023-10-13 09:20,,RANGE
                2023-10-13 09:30,-6.80,TEMPORAL
                """
            ),
        )

    def test_check_delta_remainder_with_symmetric_and_negative_threshold(self) -> None:
        test_data = textwrap.dedent(
            """\
            2023-10-13 08:40,12.30,
            2023-10-13 08:51,14.30,
            """
        )
        self._create_htimeseries(test_data)
        result: str = self._run_rocc(
            thresholds=(Threshold("10min", -1),),
            symmetric=True,
        )

        self.assertEqual(result, test_data)
