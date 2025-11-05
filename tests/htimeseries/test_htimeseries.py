from __future__ import annotations

import datetime as dt
import re
import textwrap
from configparser import ParsingError
from copy import copy
from io import StringIO
from typing import Any, Callable, cast
from unittest import TestCase
from zoneinfo import ZoneInfo

import numpy as np
import pandas as pd
from iso8601 import parse_date

from htimeseries import FormatAutoDetector, HTimeseries, MetadataReader, MetadataWriter

tenmin_test_timeseries = textwrap.dedent(
    """\
    2008-02-07 11:20,1141.00,
    2008-02-07 11:30,1142.01,MISS
    2008-02-07 11:40,1154.02,
    2008-02-07 11:50,,
    2008-02-07 12:00,1180.04,
    """
)

tenmin_test_timeseries_file_version_2 = textwrap.dedent(
    """\
    Version=2\r
    Unit=°C\r
    Count=5\r
    Title=A test 10-min time series\r
    Comment=This timeseries is extremely important\r
    Comment=because the comment that describes it\r
    Comment=spans five lines.\r
    Comment=\r
    Comment=These five lines form two paragraphs.\r
    Timezone=+0200\r
    Time_step=10,0\r
    Variable=temperature\r
    Precision=1\r
    \r
    2008-02-07 11:20,1141.0,\r
    2008-02-07 11:30,1142.0,MISS\r
    2008-02-07 11:40,1154.0,\r
    2008-02-07 11:50,,\r
    2008-02-07 12:00,1180.0,\r
    """
)

tenmin_test_timeseries_file_version_3 = textwrap.dedent(
    """\
    Unit=°C\r
    Count=5\r
    Title=A test 10-min time series\r
    Comment=This timeseries is extremely important\r
    Comment=because the comment that describes it\r
    Comment=spans five lines.\r
    Comment=\r
    Comment=These five lines form two paragraphs.\r
    Timezone=+0200\r
    Time_step=10,0\r
    Variable=temperature\r
    Precision=1\r
    Location=24.678900 38.123450 4326\r
    Altitude=219.22\r
    \r
    2008-02-07 11:20,1141.0,\r
    2008-02-07 11:30,1142.0,MISS\r
    2008-02-07 11:40,1154.0,\r
    2008-02-07 11:50,,\r
    2008-02-07 12:00,1180.0,\r
    """
)

tenmin_test_timeseries_file_version_4 = textwrap.dedent(
    """\
    Unit=°C\r
    Count=5\r
    Title=A test 10-min time series\r
    Comment=This timeseries is extremely important\r
    Comment=because the comment that describes it\r
    Comment=spans five lines.\r
    Comment=\r
    Comment=These five lines form two paragraphs.\r
    Timezone=+0200\r
    Time_step=10,0\r
    Variable=temperature\r
    Precision=1\r
    Location=24.678900 38.123450 4326\r
    Altitude=219.22\r
    \r
    2008-02-07 11:20,1141.0,\r
    2008-02-07 11:30,1142.0,MISS\r
    2008-02-07 11:40,1154.0,\r
    2008-02-07 11:50,,\r
    2008-02-07 12:00,1180.0,\r
    """
)

tenmin_test_timeseries_file_no_altitude = textwrap.dedent(
    """\
    Unit=°C\r
    Count=5\r
    Title=A test 10-min time series\r
    Comment=This timeseries is extremely important\r
    Comment=because the comment that describes it\r
    Comment=spans five lines.\r
    Comment=\r
    Comment=These five lines form two paragraphs.\r
    Timezone=+0200\r
    Time_step=10,0\r
    Variable=temperature\r
    Precision=1\r
    Location=24.678900 38.123450 4326\r
    \r
    2008-02-07 11:20,1141.0,\r
    2008-02-07 11:30,1142.0,MISS\r
    2008-02-07 11:40,1154.0,\r
    2008-02-07 11:50,,\r
    2008-02-07 12:00,1180.0,\r
    """
)

tenmin_test_timeseries_file_no_location = textwrap.dedent(
    """\
    Unit=°C\r
    Count=5\r
    Title=A test 10-min time series\r
    Comment=This timeseries is extremely important\r
    Comment=because the comment that describes it\r
    Comment=spans five lines.\r
    Comment=\r
    Comment=These five lines form two paragraphs.\r
    Timezone=+0200\r
    Time_step=10,0\r
    Variable=temperature\r
    Precision=1\r
    \r
    2008-02-07 11:20,1141.0,\r
    2008-02-07 11:30,1142.0,MISS\r
    2008-02-07 11:40,1154.0,\r
    2008-02-07 11:50,,\r
    2008-02-07 12:00,1180.0,\r
    """
)

tenmin_test_timeseries_file_no_precision = textwrap.dedent(
    """\
    Unit=°C\r
    Count=5\r
    Title=A test 10-min time series\r
    Comment=This timeseries is extremely important\r
    Comment=because the comment that describes it\r
    Comment=spans five lines.\r
    Comment=\r
    Comment=These five lines form two paragraphs.\r
    Timezone=+0200\r
    Time_step=10,0\r
    Variable=temperature\r
    Location=24.678900 38.123450 4326\r
    Altitude=219.22\r
    \r
    2008-02-07 11:20,1141.000000,\r
    2008-02-07 11:30,1142.010000,MISS\r
    2008-02-07 11:40,1154.020000,\r
    2008-02-07 11:50,,\r
    2008-02-07 12:00,1180.040000,\r
    """
)

tenmin_test_timeseries_file_zero_precision = textwrap.dedent(
    """\
    Unit=°C\r
    Count=5\r
    Title=A test 10-min time series\r
    Comment=This timeseries is extremely important\r
    Comment=because the comment that describes it\r
    Comment=spans five lines.\r
    Comment=\r
    Comment=These five lines form two paragraphs.\r
    Timezone=+0200\r
    Time_step=10,0\r
    Variable=temperature\r
    Precision=0\r
    Location=24.678900 38.123450 4326\r
    Altitude=219.22\r
    \r
    2008-02-07 11:20,1141,\r
    2008-02-07 11:30,1142,MISS\r
    2008-02-07 11:40,1154,\r
    2008-02-07 11:50,,\r
    2008-02-07 12:00,1180,\r
    """
)


tenmin_test_timeseries_file_negative_precision = textwrap.dedent(
    """\
    Unit=°C\r
    Count=5\r
    Title=A test 10-min time series\r
    Comment=This timeseries is extremely important\r
    Comment=because the comment that describes it\r
    Comment=spans five lines.\r
    Comment=\r
    Comment=These five lines form two paragraphs.\r
    Timezone=+0200\r
    Time_step=10,0\r
    Variable=temperature\r
    Precision=-1\r
    Location=24.678900 38.123450 4326\r
    Altitude=219.22\r
    \r
    2008-02-07 11:20,1140,\r
    2008-02-07 11:30,1140,MISS\r
    2008-02-07 11:40,1150,\r
    2008-02-07 11:50,,\r
    2008-02-07 12:00,1180,\r
    """
)

standard_empty_dataframe = pd.DataFrame(
    data={"value": np.array([], dtype=np.float64), "flags": np.array([], dtype=str)},
    index=pd.DatetimeIndex([], tz=dt.timezone(dt.timedelta(hours=2))),
    columns=["value", "flags"],  # type: ignore[misc]
)
standard_empty_dataframe.index.name = "date"


class HTimeseriesArgumentsTestCase(TestCase):
    def test_raises_on_invalid_argument(self) -> None:
        msg = r"HTimeseries.__init__\(\) got an unexpected keyword argument 'invalid'"
        with self.assertRaisesRegex(TypeError, msg):
            HTimeseries(invalid=42)

    def test_raises_if_timezone_unspecified(self) -> None:
        with self.assertRaises(TypeError):
            HTimeseries(StringIO(tenmin_test_timeseries))

    def test_raises_if_dataframe_naive(self) -> None:
        df = copy(standard_empty_dataframe)
        df.index = pd.DatetimeIndex([])  # Replace with a naive index
        with self.assertRaises(TypeError):
            HTimeseries(df)


class HTimeseriesEmptyTestCase(TestCase):
    def test_read_empty(self) -> None:
        s = StringIO()
        ts = HTimeseries(s, default_tzinfo=dt.timezone(dt.timedelta(hours=2)))
        pd.testing.assert_frame_equal(ts.data, standard_empty_dataframe)

    def test_write_empty(self) -> None:
        ts = HTimeseries(default_tzinfo=dt.timezone(dt.timedelta(hours=2)))
        s = StringIO()
        ts.write(s)
        self.assertEqual(s.getvalue(), "")

    def test_create_empty(self) -> None:
        pd.testing.assert_frame_equal(
            HTimeseries(default_tzinfo=dt.timezone(dt.timedelta(hours=2))).data,
            standard_empty_dataframe,
        )

    def test_unspecified_default_tzinfo(self) -> None:
        ts = HTimeseries()
        self.assertEqual(cast(pd.DatetimeIndex, ts.data.index).tz, dt.timezone.utc)


class HTimeseriesWriteSimpleTestCase(TestCase):
    def test_write(self) -> None:
        anp = np.array(
            [
                [parse_date("2005-08-23 18:53"), 93, ""],
                [parse_date("2005-08-24 19:52"), 108.7, ""],
                [parse_date("2005-08-25 23:59"), 28.3, "HEARTS SPADES"],
                [parse_date("2005-08-26 00:02"), float("NaN"), ""],
                [parse_date("2005-08-27 00:02"), float("NaN"), "DIAMONDS"],
            ],
            dtype=object,
        )
        data = pd.DataFrame(anp[:, [1, 2]], index=anp[:, 0], columns=("value", "flags"))  # type: ignore[misc]
        ts = HTimeseries(data=data)
        s = StringIO()
        ts.write(s)
        self.assertEqual(
            s.getvalue(),
            textwrap.dedent(
                """\
                2005-08-23 18:53,93,\r
                2005-08-24 19:52,108.7,\r
                2005-08-25 23:59,28.3,HEARTS SPADES\r
                2005-08-26 00:02,,\r
                2005-08-27 00:02,,DIAMONDS\r
                """
            ),
        )


class HTimeseriesWriteFileTestCase(TestCase):
    def setUp(self) -> None:
        data = pd.read_csv(  # type: ignore[misc]
            StringIO(tenmin_test_timeseries),
            parse_dates=[0],
            usecols=["date", "value", "flags"],  # type: ignore[misc]
            index_col=0,
            header=None,
            names=("date", "value", "flags"),
            dtype={"value": np.float64, "flags": str},
        ).asfreq("10min")
        data.index = cast(pd.DatetimeIndex, data.index).tz_localize(
            dt.timezone(dt.timedelta(hours=2))
        )
        self.reference_ts = HTimeseries(data=data)
        self.reference_ts.unit = "°C"
        self.reference_ts.title = "A test 10-min time series"
        self.reference_ts.precision = 1
        self.reference_ts.time_step = "10min"
        self.reference_ts.variable = "temperature"
        self.reference_ts.comment = (
            "This timeseries is extremely important\n"
            "because the comment that describes it\n"
            "spans five lines.\n\n"
            "These five lines form two paragraphs."
        )
        self.reference_ts.location = {
            "abscissa": 24.6789,
            "ordinate": 38.12345,
            "srid": 4326,
            "altitude": 219.22,
            "asrid": None,
        }

    def test_version_2(self) -> None:
        outstring = StringIO()
        self.reference_ts.write(outstring, format=HTimeseries.FILE, version=2)
        self.assertEqual(outstring.getvalue(), tenmin_test_timeseries_file_version_2)

    def test_version_3(self) -> None:
        outstring = StringIO()
        self.reference_ts.write(outstring, format=HTimeseries.FILE, version=3)
        self.assertEqual(outstring.getvalue(), tenmin_test_timeseries_file_version_3)

    def test_version_4(self) -> None:
        outstring = StringIO()
        self.reference_ts.write(outstring, format=HTimeseries.FILE, version=4)
        self.assertEqual(outstring.getvalue(), tenmin_test_timeseries_file_version_4)

    def test_version_5(self) -> None:
        outstring = StringIO()
        self.reference_ts.write(outstring, format=HTimeseries.FILE, version=5)
        self.assertEqual(
            outstring.getvalue(),
            tenmin_test_timeseries_file_version_4.replace(
                "Time_step=10,0", "Time_step=10min"
            ),
        )

    def test_version_latest(self) -> None:
        outstring = StringIO()
        self.reference_ts.write(outstring, format=HTimeseries.FILE)
        self.assertEqual(
            outstring.getvalue(),
            tenmin_test_timeseries_file_version_4.replace(
                "Time_step=10,0", "Time_step=10min"
            ),
        )

    def test_altitude_none(self) -> None:
        assert self.reference_ts.location is not None
        self.reference_ts.location["altitude"] = None
        outstring = StringIO()
        self.reference_ts.write(outstring, format=HTimeseries.FILE, version=4)
        self.assertEqual(outstring.getvalue(), tenmin_test_timeseries_file_no_altitude)

    def test_no_altitude(self) -> None:
        assert self.reference_ts.location is not None
        del self.reference_ts.location["altitude"]
        outstring = StringIO()
        self.reference_ts.write(outstring, format=HTimeseries.FILE, version=4)
        self.assertEqual(outstring.getvalue(), tenmin_test_timeseries_file_no_altitude)

    def test_altitude_zero(self) -> None:
        assert self.reference_ts.location is not None
        self.reference_ts.location["altitude"] = 0
        outstring = StringIO()
        self.reference_ts.write(outstring, format=HTimeseries.FILE, version=4)
        self.assertIn("Altitude=0", outstring.getvalue())

    def test_location_none(self) -> None:
        self.reference_ts.location = None
        outstring = StringIO()
        self.reference_ts.write(outstring, format=HTimeseries.FILE, version=4)
        self.assertEqual(outstring.getvalue(), tenmin_test_timeseries_file_no_location)

    def test_no_location(self) -> None:
        delattr(self.reference_ts, "location")
        outstring = StringIO()
        self.reference_ts.write(outstring, format=HTimeseries.FILE, version=4)
        self.assertEqual(outstring.getvalue(), tenmin_test_timeseries_file_no_location)

    def test_precision_none(self) -> None:
        self.reference_ts.precision = None
        outstring = StringIO()
        self.reference_ts.write(outstring, format=HTimeseries.FILE, version=4)
        self.assertEqual(outstring.getvalue(), tenmin_test_timeseries_file_no_precision)

    def test_no_precision(self) -> None:
        delattr(self.reference_ts, "precision")
        outstring = StringIO()
        self.reference_ts.write(outstring, format=HTimeseries.FILE, version=4)
        self.assertEqual(outstring.getvalue(), tenmin_test_timeseries_file_no_precision)

    def test_precision_zero(self) -> None:
        self.reference_ts.precision = 0
        outstring = StringIO()
        self.reference_ts.write(outstring, format=HTimeseries.FILE, version=4)
        self.assertEqual(
            outstring.getvalue(), tenmin_test_timeseries_file_zero_precision
        )

    def test_negative_precision(self) -> None:
        self.reference_ts.precision = -1
        outstring = StringIO()
        self.reference_ts.write(outstring, format=HTimeseries.FILE, version=4)
        self.assertEqual(
            outstring.getvalue(), tenmin_test_timeseries_file_negative_precision
        )

    def test_timezone_utc(self) -> None:
        self.reference_ts.data = self.reference_ts.data.tz_convert(dt.timezone.utc)
        outstring = StringIO()
        self.reference_ts.write(outstring, format=HTimeseries.FILE, version=4)
        self.assertIn("Timezone=+0000\r\n", outstring.getvalue())

    def test_timezone_positive(self) -> None:
        tz = dt.timezone(dt.timedelta(hours=2, minutes=30))
        self.reference_ts.data = self.reference_ts.data.tz_convert(tz)
        outstring = StringIO()
        self.reference_ts.write(outstring, format=HTimeseries.FILE, version=4)
        self.assertIn("Timezone=+0230\r\n", outstring.getvalue())

    def test_timezone_negative(self) -> None:
        tz = dt.timezone(-dt.timedelta(hours=3, minutes=15))
        self.reference_ts.data = self.reference_ts.data.tz_convert(tz)
        outstring = StringIO()
        self.reference_ts.write(outstring, format=HTimeseries.FILE, version=4)
        self.assertIn("Timezone=-0315\r\n", outstring.getvalue())


class ReadFilelikeTestCaseBase:
    ts: HTimeseries
    assertEqual: Callable[[Any, Any], None]

    def test_length(self) -> None:
        self.assertEqual(len(self.ts.data), 5)

    def test_dates(self) -> None:
        np.testing.assert_array_equal(
            self.ts.data.index,
            pd.date_range("2008-02-07 11:20+0200", periods=5, freq="10min"),
        )

    def test_values(self) -> None:
        expected = np.array(
            [1141.00, 1142.01, 1154.02, float("NaN"), 1180.04], dtype=float
        )
        np.testing.assert_allclose(self.ts.data.values[:, 0].astype(float), expected)

    def test_flags(self) -> None:
        expected = np.array(["", "MISS", "", "", ""])
        np.testing.assert_array_equal(self.ts.data.values[:, 1], expected)

    def test_tz(self) -> None:
        tz = cast(pd.DatetimeIndex, self.ts.data.index).tz
        assert tz is not None
        self.assertEqual(tz.utcoffset(dt.datetime(2000, 1, 1)), dt.timedelta(hours=2))


class HTimeseriesReadTwoColumnsTestCase(ReadFilelikeTestCaseBase, TestCase):
    def setUp(self) -> None:
        string = self._remove_flags_column(tenmin_test_timeseries)
        s = StringIO(string)
        s.seek(0)
        self.ts = HTimeseries(s, default_tzinfo=ZoneInfo("Etc/GMT-2"))

    def _remove_flags_column(self, s: str) -> str:
        return re.sub(r",[^,]*$", "", s, flags=re.MULTILINE) + "\n"

    def test_flags(self) -> None:
        expected = np.array(["", "", "", "", ""])
        np.testing.assert_array_equal(self.ts.data.values[:, 1], expected)

    def test_tz(self) -> None:
        tz = cast(pd.DatetimeIndex, self.ts.data.index).tz
        assert tz is not None
        self.assertEqual(tz.utcoffset(dt.datetime(2000, 1, 1)), dt.timedelta(hours=2))


class HTimeseriesReadMixOf2And3ColumnsTestCase(ReadFilelikeTestCaseBase, TestCase):
    def setUp(self) -> None:
        string = self._remove_empty_flags_column(tenmin_test_timeseries)
        s = StringIO(string)
        s.seek(0)
        self.ts = HTimeseries(s, default_tzinfo=ZoneInfo("Etc/GMT-2"))

    def _remove_empty_flags_column(self, s: str) -> str:
        return re.sub(r",$", "", s, flags=re.MULTILINE) + "\n"


class HTimeseriesReadOneColumnTestCase(TestCase):
    def test_one_column(self) -> None:
        s = StringIO("2023-12-19 15:17\n")
        s.seek(0)
        self.ts = HTimeseries(s, default_tzinfo=ZoneInfo("Etc/GMT-2"))
        expected = pd.DataFrame(
            {"value": [np.nan], "flags": [""]},
            index=[dt.datetime(2023, 12, 19, 15, 17, tzinfo=ZoneInfo("Etc/GMT-2"))],  # type: ignore[misc]
        )
        expected.index.name = "date"
        pd.testing.assert_frame_equal(self.ts.data, expected)


class HTimeseriesReadFilelikeMetadataOnlyTestCase(TestCase):
    def setUp(self) -> None:
        s = StringIO(tenmin_test_timeseries_file_version_4)
        s.seek(0)
        self.ts = HTimeseries(
            s, start_date="1971-01-01 00:00", end_date="1970-01-01 00:00"
        )

    def test_data_is_empty(self) -> None:
        self.assertEqual(len(self.ts.data), 0)

    def test_metadata_was_read(self) -> None:
        self.assertEqual(self.ts.unit, "°C")


class HTimeseriesReadFilelikeWithMissingLocationButPresentAltitudeTestCase(TestCase):
    def setUp(self) -> None:
        s = StringIO("Altitude=55\n\n")
        self.ts = HTimeseries(s, default_tzinfo=dt.timezone(dt.timedelta(hours=2)))

    def test_data_is_empty(self) -> None:
        pd.testing.assert_frame_equal(self.ts.data, standard_empty_dataframe)

    def test_has_altitude(self) -> None:
        assert self.ts.location is not None
        self.assertEqual(self.ts.location["altitude"], 55)

    def test_has_no_abscissa(self) -> None:
        assert self.ts.location is not None
        self.assertFalse("abscissa" in self.ts.location)


class HTimeseriesReadWithStartDateAndEndDateTestCase(TestCase):
    def setUp(self) -> None:
        s = StringIO(tenmin_test_timeseries)
        s.seek(0)
        self.ts = HTimeseries(
            s,
            start_date=dt.datetime(2008, 2, 7, 11, 30, tzinfo=dt.timezone.utc),
            end_date=dt.datetime(2008, 2, 7, 11, 55, tzinfo=dt.timezone.utc),
            default_tzinfo=dt.timezone.utc,
        )

    def test_length(self) -> None:
        self.assertEqual(len(self.ts.data), 3)

    def test_dates(self) -> None:
        np.testing.assert_array_equal(
            self.ts.data.index,
            pd.date_range(
                "2008-02-07 11:30", periods=3, freq="10min", tz=dt.timezone.utc
            ),
        )

    def test_values(self) -> None:
        np.testing.assert_allclose(
            self.ts.data.values[:, 0].astype(float),
            np.array([1142.01, 1154.02, float("NaN")]),
        )

    def test_flags(self) -> None:
        np.testing.assert_array_equal(
            self.ts.data.values[:, 1], np.array(["MISS", "", ""])
        )


class HTimeseriesReadWithStartDateTestCase(TestCase):
    def setUp(self) -> None:
        s = StringIO(tenmin_test_timeseries)
        s.seek(0)
        self.ts = HTimeseries(
            s,
            start_date=dt.datetime(2008, 2, 7, 11, 45, tzinfo=dt.timezone.utc),
            default_tzinfo=dt.timezone.utc,
        )

    def test_length(self) -> None:
        self.assertEqual(len(self.ts.data), 2)

    def test_dates(self) -> None:
        np.testing.assert_array_equal(
            self.ts.data.index,
            pd.date_range(
                "2008-02-07 11:50", periods=2, freq="10min", tz=dt.timezone.utc
            ),
        )

    def test_values(self) -> None:
        np.testing.assert_allclose(
            self.ts.data.values[:, 0].astype(float), np.array([float("NaN"), 1180.04])
        )

    def test_flags(self) -> None:
        np.testing.assert_array_equal(self.ts.data.values[:, 1], np.array(["", ""]))


class HTimeseriesReadWithEndDateTestCase(TestCase):
    def setUp(self) -> None:
        s = StringIO(tenmin_test_timeseries)
        s.seek(0)
        self.ts = HTimeseries(
            s,
            end_date=dt.datetime(2008, 2, 7, 11, 50, tzinfo=dt.timezone.utc),
            default_tzinfo=dt.timezone.utc,
        )

    def test_length(self) -> None:
        self.assertEqual(len(self.ts.data), 4)

    def test_dates(self) -> None:
        np.testing.assert_array_equal(
            self.ts.data.index,
            pd.date_range(
                "2008-02-07 11:20", periods=4, freq="10min", tz=dt.timezone.utc
            ),
        )

    def test_values(self) -> None:
        np.testing.assert_allclose(
            self.ts.data.values[:, 0].astype(float),
            np.array([1141.00, 1142.01, 1154.02, float("NaN")]),
        )

    def test_flags(self) -> None:
        np.testing.assert_array_equal(
            self.ts.data.values[:, 1], np.array(["", "MISS", "", ""])
        )


class HTimeseriesReadFileFormatTestCase(TestCase):
    def setUp(self) -> None:
        s = StringIO(tenmin_test_timeseries_file_version_4)
        s.seek(0)
        self.ts = HTimeseries(s)

    def test_unit(self) -> None:
        self.assertEqual(self.ts.unit, "°C")

    def test_title(self) -> None:
        self.assertEqual(self.ts.title, "A test 10-min time series")

    def test_comment(self) -> None:
        self.assertEqual(
            self.ts.comment,
            textwrap.dedent(
                """\
                This timeseries is extremely important
                because the comment that describes it
                spans five lines.

                These five lines form two paragraphs."""
            ),
        )

    def test_timezone(self) -> None:
        tz = cast(pd.DatetimeIndex, self.ts.data.index).tz
        assert tz is not None
        self.assertEqual(tz.utcoffset(None), dt.timedelta(hours=2))

    def test_time_step(self) -> None:
        self.assertEqual(self.ts.time_step, "10min")

    def test_variable(self) -> None:
        self.assertEqual(self.ts.variable, "temperature")

    def test_precision(self) -> None:
        self.assertEqual(self.ts.precision, 1)

    def test_abscissa(self) -> None:
        assert self.ts.location is not None
        self.assertAlmostEqual(self.ts.location["abscissa"], 24.678900, places=6)

    def test_ordinate(self) -> None:
        assert self.ts.location is not None
        self.assertAlmostEqual(self.ts.location["ordinate"], 38.123450, places=6)

    def test_srid(self) -> None:
        assert self.ts.location is not None
        self.assertEqual(self.ts.location["srid"], 4326)

    def test_altitude(self) -> None:
        assert self.ts.location is not None
        self.assertAlmostEqual(self.ts.location["altitude"], 219.22, places=2)

    def test_asrid(self) -> None:
        assert self.ts.location is not None
        self.assertTrue(self.ts.location["asrid"] is None)

    def test_length(self) -> None:
        self.assertEqual(len(self.ts.data), 5)

    def test_dates(self) -> None:
        np.testing.assert_array_equal(
            self.ts.data.index,
            pd.date_range(
                "2008-02-07 11:20", periods=5, freq="10min", tz=ZoneInfo("Etc/GMT-2")
            ),
        )

    def test_values(self) -> None:
        np.testing.assert_allclose(
            self.ts.data.values[:, 0].astype(float),
            np.array([1141.0, 1142.0, 1154.0, float("NaN"), 1180.0]),
        )

    def test_flags(self) -> None:
        np.testing.assert_array_equal(
            self.ts.data.values[:, 1], np.array(["", "MISS", "", "", ""])
        )


class FormatAutoDetectorTestCase(TestCase):
    def test_auto_detect_text_format(self) -> None:
        detected_format = FormatAutoDetector(StringIO(tenmin_test_timeseries)).detect()
        self.assertEqual(detected_format, HTimeseries.TEXT)

    def test_auto_detect_file_format(self) -> None:
        detected_format = FormatAutoDetector(
            StringIO(tenmin_test_timeseries_file_version_4)
        ).detect()
        self.assertEqual(detected_format, HTimeseries.FILE)


class WriteOldTimeStepTestCase(TestCase):
    def get_value(self, time_step: str) -> str:
        self.f = StringIO()
        self.htimeseries = HTimeseries()
        self.htimeseries.time_step = time_step
        MetadataWriter(self.f, self.htimeseries, version=2).write_time_step()
        return self.f.getvalue()

    def test_empty(self) -> None:
        self.assertEqual(self.get_value(""), "")

    def test_min(self) -> None:
        self.assertEqual(self.get_value("27min"), "Time_step=27,0\r\n")

    def test_min_without_number(self) -> None:
        self.assertEqual(self.get_value("min"), "Time_step=1,0\r\n")

    def test_hour(self) -> None:
        self.assertEqual(self.get_value("3h"), "Time_step=180,0\r\n")

    def test_hour_without_number(self) -> None:
        self.assertEqual(self.get_value("h"), "Time_step=60,0\r\n")

    def test_day(self) -> None:
        self.assertEqual(self.get_value("3D"), "Time_step=4320,0\r\n")

    def test_day_without_number(self) -> None:
        self.assertEqual(self.get_value("D"), "Time_step=1440,0\r\n")

    def test_month(self) -> None:
        self.assertEqual(self.get_value("3ME"), "Time_step=0,3\r\n")

    def test_month_without_number(self) -> None:
        self.assertEqual(self.get_value("ME"), "Time_step=0,1\r\n")

    def test_year(self) -> None:
        self.assertEqual(self.get_value("3YE"), "Time_step=0,36\r\n")

    def test_year_without_number(self) -> None:
        self.assertEqual(self.get_value("YE"), "Time_step=0,12\r\n")

    def test_garbage(self) -> None:
        with self.assertRaisesRegex(ValueError, 'Cannot format time step "hello"'):
            self.get_value("hello")

    def test_wrong_number(self) -> None:
        with self.assertRaisesRegex(ValueError, 'Cannot format time step "FM"'):
            self.get_value("FM")


class GetTimeStepTestCase(TestCase):
    def get_value(self, time_step: str) -> str:
        f = StringIO("Time_step={}\r\n\r\n".format(time_step))
        return MetadataReader(f).meta["time_step"]

    def test_min(self) -> None:
        self.assertEqual(self.get_value("1min"), "1min")

    def test_minutes(self) -> None:
        self.assertEqual(self.get_value("250,0"), "250min")

    def test_months(self) -> None:
        self.assertEqual(self.get_value("0,25"), "25M")

    def test_both_nonzero(self) -> None:
        with self.assertRaisesRegex(ParsingError, "Invalid time step"):
            self.get_value("5,5")


class HTimeseriesReadWithDuplicateDatesTestCase(TestCase):
    csv_with_duplicates = textwrap.dedent(
        """\
        2020-02-23 11:00,5,
        2020-02-23 12:00,6,
        2020-02-23 12:00,7,
        2020-02-23 13:00,8,
        2020-02-23 13:00,8,
        2020-02-23 14:00,8,
        """
    )

    def test_read_csv_with_duplicates_raises_error(self) -> None:
        s = StringIO(self.csv_with_duplicates)
        s.seek(0)
        msg = (
            "Can't read time series: the following timestamps appear more than once: "
            "2020-02-23 12:00:00, 2020-02-23 13:00:00"
        )
        with self.assertRaisesRegex(ValueError, msg):
            HTimeseries(s)

    def test_write_csv_with_duplicates_raises_error(self) -> None:
        data = pd.read_csv(  # type: ignore[misc]
            StringIO(self.csv_with_duplicates),
            parse_dates=[0],
            usecols=["date", "value", "flags"],  # type: ignore[misc]
            index_col=0,
            header=None,
            names=("date", "value", "flags"),
            dtype={"value": np.float64, "flags": str},
        )
        data.index = cast(pd.DatetimeIndex, data.index).tz_localize(dt.timezone.utc)
        msg = (
            "Can't write time series: the following timestamps appear more than once: "
            r"2020-02-23 12:00:00\+00:00, 2020-02-23 13:00:00\+00:00"
        )
        with self.assertRaisesRegex(ValueError, msg):
            HTimeseries(data).write(StringIO())


class HTimeseriesTimeChangeTestCase(TestCase):
    """Test what happens when we read a csv containing a time change.

    We use a hard case here, a switch from DST to normal, which contains a duplicate
    hour. HTimeseries will refuse to handle repeating timestamps, so we use test data
    that does not contain a repeating hour. In that case, HTimeseries assumes the
    ambiguous times are before the switch.
    """

    time_change_test_timeseries = textwrap.dedent(
        """\
        2023-10-29 02:30,15,
        2023-10-29 03:00,16,
        2023-10-29 03:30,17,
        2023-10-29 04:00,20,
        2023-10-29 04:30,21,
        """
    )

    def setUp(self) -> None:
        s = StringIO(self.time_change_test_timeseries)
        s.seek(0)
        self.ts = HTimeseries(s, default_tzinfo=ZoneInfo("Europe/Athens"))

    def test_dates(self) -> None:
        expected = np.array(
            [
                dt.datetime(2023, 10, 28, 23, 30, 0, tzinfo=dt.timezone.utc),
                dt.datetime(2023, 10, 29, 0, 0, 0, tzinfo=dt.timezone.utc),
                dt.datetime(2023, 10, 29, 0, 30, 0, tzinfo=dt.timezone.utc),
                dt.datetime(2023, 10, 29, 2, 0, 0, tzinfo=dt.timezone.utc),
                dt.datetime(2023, 10, 29, 2, 30, 0, tzinfo=dt.timezone.utc),
            ]
        )
        index = cast(pd.DatetimeIndex, self.ts.data.index)
        np.testing.assert_array_equal(index.tz_convert(dt.timezone.utc), expected)


class HTimeseriesCsvWithAwareTimestampsTestCase(TestCase):
    """Test what happens when we read a csv with aware timestamps.

    Some enhydris-api-client/loggertodb versions attempt to upload CSVs
    with timestamps containing time zones, such as 2023-12-22
    19:53+00:00. We check that we handle this correctly.
    """

    def test_csv_with_aware_timestamps(self) -> None:
        s = StringIO("2023-12-22 19:53+00:00,42.0,\n")
        s.seek(0)
        self.ts = HTimeseries(s, default_tzinfo=ZoneInfo("Etc/GMT-2"))
        self.assertEqual(
            self.ts.data.index[0],
            dt.datetime(2023, 12, 22, 19, 53, tzinfo=dt.timezone.utc),
        )

    def test_csv_with_mixed_timestamps(self) -> None:
        s = StringIO("2023-12-22 19:53+00:00,42.0,\n2023-12-22 20:53,43.0,\n")
        s.seek(0)
        msg = "Maybe the CSV contains mixed aware and naive timestamps"
        with self.assertRaisesRegex(ValueError, msg):
            HTimeseries(s, default_tzinfo=ZoneInfo("Etc/GMT-2"))
