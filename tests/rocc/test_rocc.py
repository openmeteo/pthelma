import textwrap
from io import StringIO
from unittest import TestCase

try:
    from zoneinfo import ZoneInfo
except ImportError:
    from backports.zoneinfo import ZoneInfo

from htimeseries import HTimeseries
from rocc import Threshold, rocc


class RoccTestCase(TestCase):
    test_data = textwrap.dedent(
        """\
        2020-10-06 14:30,24.0,
        2020-10-06 14:40,25.0,
        2020-10-06 14:50,36.0,SOMEFLAG
        2020-10-06 15:01,51.0,
        2020-10-06 15:21,55.0,
        2020-10-06 15:31,65.0,
        2020-10-06 15:41,75.0,
        2020-10-06 15:51,70.0,
        """
    )

    def setUp(self):
        self.ahtimeseries = HTimeseries(
            StringIO(self.test_data), default_tzinfo=ZoneInfo("Etc/GMT-2")
        )
        self.ahtimeseries.precision = 1

    def _run_rocc(self, flag):
        self.return_value = rocc(
            timeseries=self.ahtimeseries,
            thresholds=(
                Threshold("10min", 10),
                Threshold("20min", 15),
                Threshold("h", 40),
            ),
            flag=flag,
        )

    def test_calculation(self):
        self._run_rocc(flag="TEMPORAL")
        result = StringIO()
        self.ahtimeseries.write(result)
        result = result.getvalue().replace("\r\n", "\n")
        self.assertEqual(
            result,
            textwrap.dedent(
                """\
                2020-10-06 14:30,24.0,
                2020-10-06 14:40,25.0,
                2020-10-06 14:50,36.0,SOMEFLAG TEMPORAL
                2020-10-06 15:01,51.0,
                2020-10-06 15:21,55.0,
                2020-10-06 15:31,65.0,
                2020-10-06 15:41,75.0,TEMPORAL
                2020-10-06 15:51,70.0,
                """
            ),
        )

    def test_return_value(self):
        self._run_rocc(flag="TEMPORAL")
        self.assertEqual(len(self.return_value), 2)
        self.assertEqual(
            self.return_value[0], "2020-10-06T14:50  +11.0 in 10min (> 10.0)"
        )
        self.assertEqual(
            self.return_value[1], "2020-10-06T15:41  +20.0 in 20min (> 15.0)"
        )

    def test_value_dtype(self):
        self._run_rocc(flag="TEMPORAL")
        expected_dtype = HTimeseries().data["value"].dtype
        self.assertEqual(self.ahtimeseries.data["value"].dtype, expected_dtype)

    def test_flags_dtype(self):
        self._run_rocc(flag="TEMPORAL")
        expected_dtype = HTimeseries().data["flags"].dtype
        self.assertEqual(self.ahtimeseries.data["flags"].dtype, expected_dtype)

    def test_empty_flag(self):
        self._run_rocc(flag=None)
        result = StringIO()
        self.ahtimeseries.write(result)
        result = result.getvalue().replace("\r\n", "\n")
        self.assertEqual(result, self.test_data)


class RoccSymmetricCase(TestCase):
    test_data = textwrap.dedent(
        """\
        2020-10-06 14:30,76.0,
        2020-10-06 14:40,75.0,SOMEFLAG
        2020-10-06 14:50,64.0,SOMEFLAG
        2020-10-06 15:01,49.0,
        2020-10-06 15:21,45.0,
        2020-10-06 15:31,35.0,
        2020-10-06 15:41,25.0,
        2020-10-06 15:51,30.0,
        """
    )

    def setUp(self):
        self.ahtimeseries = HTimeseries(
            StringIO(self.test_data), default_tzinfo=ZoneInfo("Etc/GMT-2")
        )
        self.ahtimeseries.precision = 1

    def test_without_symmetric(self):
        rocc(
            timeseries=self.ahtimeseries,
            thresholds=(
                Threshold("10min", 10),
                Threshold("20min", 15),
                Threshold("h", 40),
            ),
        )
        result = StringIO()
        self.ahtimeseries.write(result)
        result = result.getvalue().replace("\r\n", "\n")
        self.assertEqual(
            result,
            textwrap.dedent(
                """\
                2020-10-06 14:30,76.0,
                2020-10-06 14:40,75.0,SOMEFLAG
                2020-10-06 14:50,64.0,SOMEFLAG
                2020-10-06 15:01,49.0,
                2020-10-06 15:21,45.0,
                2020-10-06 15:31,35.0,
                2020-10-06 15:41,25.0,
                2020-10-06 15:51,30.0,
                """
            ),
        )

    def test_with_symmetric(self):
        rocc(
            timeseries=self.ahtimeseries,
            thresholds=(
                Threshold("10min", 10),
                Threshold("20min", 15),
                Threshold("h", 40),
            ),
            symmetric=True,
        )
        result = StringIO()
        self.ahtimeseries.write(result)
        result = result.getvalue().replace("\r\n", "\n")
        self.assertEqual(
            result,
            textwrap.dedent(
                """\
                2020-10-06 14:30,76.0,
                2020-10-06 14:40,75.0,SOMEFLAG
                2020-10-06 14:50,64.0,SOMEFLAG TEMPORAL
                2020-10-06 15:01,49.0,
                2020-10-06 15:21,45.0,
                2020-10-06 15:31,35.0,
                2020-10-06 15:41,25.0,TEMPORAL
                2020-10-06 15:51,30.0,
                """
            ),
        )

    def test_symmetric_return_value(self):
        return_value = rocc(
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
    def test_with_empty(self):
        ahtimeseries = HTimeseries()
        rocc(timeseries=ahtimeseries, thresholds=[Threshold("10min", 10)])
        self.assertTrue(ahtimeseries.data.empty)
