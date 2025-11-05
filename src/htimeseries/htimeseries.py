from __future__ import annotations

import csv
import datetime as dt
from configparser import ParsingError
from io import StringIO
from typing import IO, Any, Callable, Dict, List, Optional, Sequence, Tuple, Union, cast

import numpy as np
import pandas as pd
from pandas.tseries.frequencies import to_offset

from textbisect import text_bisect_left

from .timezone_utils import TzinfoFromString

TextFileLike = IO[str]
FileLike = Union[IO[str], IO[bytes], "_BacktrackableFile"]


class _BacktrackableFile:
    def __init__(self, fp: FileLike) -> None:
        self.fp: FileLike = fp
        self.line_number: int = 0
        self.next_line: Optional[Union[str, bytes]] = None

    def readline(self) -> Union[str, bytes]:
        if self.next_line is None:
            self.line_number += 1
            result = self.fp.readline()
        else:
            result = self.next_line
            self.next_line = None
        return result

    def backtrack(self, line: Union[str, bytes]) -> None:
        self.next_line = line

    def read(self, size: Optional[int] = None) -> Union[str, bytes]:
        return self.fp.read() if size is None else self.fp.read(size)

    def __iter__(self) -> "_BacktrackableFile":
        return self

    def __next__(self) -> Union[str, bytes]:
        return self.fp.__next__()

    def __getattr__(self, name: str) -> Any:
        return getattr(self.fp, name)


class _FilePart:
    """A wrapper that views only a subset of the wrapped csv filelike object.

    When it is created, three mandatory parameters are passed: a filelike object,
    start_date and end_date, the latter as stirngs. This wrapper then acts as a filelike
    object, which views the part of the wrapped object between start_date and end_date.
    """

    def __init__(self, stream: TextFileLike, start_date: str, end_date: str) -> None:
        self.stream: TextFileLike = stream
        self.start_date = start_date
        self.end_date = end_date

        lo = stream.tell()
        key: Callable[[str], str] = lambda x: x.split(",")[0]  # NOQA
        self.startpos: int = text_bisect_left(stream, start_date, lo=lo, key=key)
        self.endpos: int = text_bisect_left(stream, end_date, lo=self.startpos, key=key)
        self.stream.seek(self.startpos)

    def readline(self, size: int = -1) -> str:
        max_available_size = self.endpos + 1 - self.stream.tell()
        size = min(size, max_available_size)
        return self.stream.readline(size)

    def __iter__(self) -> "_FilePart":
        return self

    def __next__(self) -> str:
        result = self.stream.__next__()
        if result[:16] > self.end_date:
            raise StopIteration
        return result

    def __getattr__(self, name: str) -> Any:
        return getattr(self.stream, name)


class MetadataWriter:
    def __init__(self, f: IO[str], htimeseries: "HTimeseries", version: int) -> None:
        self.version = version
        self.htimeseries = htimeseries
        self.f = f

    def write_meta(self) -> None:
        if self.version == 2:
            self.f.write("Version=2\r\n")
        self.write_simple("unit")
        self.write_count()
        self.write_simple("title")
        self.write_comment()
        self.write_timezone()
        self.write_time_step()
        self.write_simple("interval_type")
        self.write_simple("variable")
        self.write_simple("precision")
        self.write_location()
        self.write_altitude()

    def write_simple(self, parm: str) -> None:
        value = getattr(self.htimeseries, parm, None)
        if value is not None:
            self.f.write("{}={}\r\n".format(parm.capitalize(), value))

    def write_count(self) -> None:
        self.f.write("Count={}\r\n".format(len(self.htimeseries.data)))

    def write_comment(self) -> None:
        if hasattr(self.htimeseries, "comment"):
            for line in self.htimeseries.comment.splitlines():
                self.f.write("Comment={}\r\n".format(line))

    def write_timezone(self) -> None:
        index = cast(pd.DatetimeIndex, self.htimeseries.data.index)
        assert index.tz is not None
        offset = index.tz.utcoffset(None)
        assert offset is not None
        sign = "-+"[offset >= dt.timedelta(0)]
        offset = abs(offset)
        hours = offset.seconds // 3600
        minutes = offset.seconds % 3600 // 60
        self.f.write(f"Timezone={sign}{hours:02}{minutes:02}\r\n")

    def write_location(self) -> None:
        if self.version <= 2 or not getattr(self.htimeseries, "location", None):
            return
        assert self.htimeseries.location is not None
        self.f.write(
            "Location={:.6f} {:.6f} {}\r\n".format(
                *[
                    self.htimeseries.location[x]
                    for x in ["abscissa", "ordinate", "srid"]
                ]
            )
        )

    def write_altitude(self) -> None:
        if self.version <= 2 or not getattr(self.htimeseries, "location", None):
            return
        assert self.htimeseries.location is not None

        if self.htimeseries.location.get("altitude") is None:
            return
        altitude = self.htimeseries.location["altitude"]
        asrid = (
            self.htimeseries.location["asrid"]
            if "asrid" in self.htimeseries.location
            else None
        )
        fmt = (
            "Altitude={altitude:.2f} {asrid}\r\n"
            if asrid
            else "Altitude={altitude:.2f}\r\n"
        )
        self.f.write(fmt.format(altitude=altitude, asrid=asrid))

    def write_time_step(self) -> None:
        if getattr(self.htimeseries, "time_step", ""):
            self._write_nonempty_time_step()

    def _write_nonempty_time_step(self) -> None:
        if self.version >= 5:
            self.f.write(f"Time_step={self.htimeseries.time_step}\r\n")
        else:
            self._write_old_time_step()

    def _write_old_time_step(self) -> None:
        try:
            old_time_step = self._get_old_time_step_in_minutes()
        except ValueError:
            old_time_step = self._get_old_time_step_in_months()
        self.f.write("Time_step={}\r\n".format(old_time_step))

    def _get_old_time_step_in_minutes(self) -> str:
        td = cast(pd.Timedelta, pd.to_timedelta(to_offset(self.htimeseries.time_step)))  # type: ignore
        return str(int(td.total_seconds() / 60)) + ",0"

    def _get_old_time_step_in_months(self) -> str:
        time_step = self.htimeseries.time_step
        try:
            value, unit = self._split_time_step_string(time_step)
            value = value or 1
            if unit in ("M", "ME"):
                return "0," + str(int(value))
            elif unit in ("A", "Y", "YE"):
                return "0," + str(12 * int(value))
        except (IndexError, ValueError):
            pass
        raise ValueError('Cannot format time step "{}"'.format(time_step))

    def _split_time_step_string(self, time_step_string: str) -> Tuple[str, str]:
        value = ""
        for i, char in enumerate(time_step_string):
            if not char.isdigit():
                return value, time_step_string[i:]
            value += char
        assert False, "Unreachable"


class MetadataReader:
    def __init__(self, f: FileLike) -> None:
        f = _BacktrackableFile(f)

        # Check if file contains headers
        first_line = f.readline()
        f.backtrack(first_line)
        if isinstance(first_line, bytes):
            first_line = first_line.decode("utf-8-sig")
        assert isinstance(first_line, str)
        has_headers = not first_line[0].isdigit()

        # Read file, with its headers if needed
        self.meta: Dict[str, Any] = {}
        if has_headers:
            self.read_meta(f)

    def read_meta(self, f: FileLike) -> None:
        """Read the headers of a file in file format and place them in the
        self.meta dictionary.
        """
        if not isinstance(f, _BacktrackableFile):
            f = _BacktrackableFile(f)

        try:
            (name, value) = self.read_meta_line(f)
            while name:
                method_name = "get_{}".format(name)
                if hasattr(self, method_name):
                    method = getattr(self, method_name)
                    method(name, value)
                name, value = self.read_meta_line(f)
                if not name and not value:
                    break
        except ParsingError as e:
            e.args = e.args + (f.line_number,)
            raise

    def get_unit(self, name: str, value: str) -> None:
        self.meta[name] = value

    get_title = get_unit
    get_variable = get_unit

    def get_time_step(self, name: str, value: str) -> None:
        if value and "," in value:
            minutes, months = self.read_minutes_months(value)
            self.meta[name] = self._time_step_from_minutes_months(minutes, months)
        else:
            self.meta[name] = value

    def get_timezone(self, name: str, value: str) -> None:
        self.meta["_timezone"] = value

    def _time_step_from_minutes_months(self, minutes: int, months: int) -> str:
        if minutes != 0 and months != 0:
            raise ParsingError("Invalid time step")
        elif minutes != 0:
            return str(minutes) + "min"
        else:
            return str(months) + "M"

    def get_interval_type(self, name: str, value: str) -> None:
        value = value.lower()
        if value not in ("sum", "average", "maximum", "minimum", "vector_average"):
            raise ParsingError(("Invalid interval type"))
        self.meta[name] = value

    def get_precision(self, name: str, value: str) -> None:
        try:
            self.meta[name] = int(value)
        except ValueError as e:
            raise ParsingError(str(e))

    def get_comment(self, name: str, value: str) -> None:
        if "comment" in self.meta:
            self.meta["comment"] += "\n"
        else:
            self.meta["comment"] = ""
        self.meta["comment"] += value

    def get_location(self, name: str, value: str) -> None:
        self._ensure_location_attribute_exists()
        try:
            items = value.split()
            self.meta["location"]["abscissa"] = float(items[0])
            self.meta["location"]["ordinate"] = float(items[1])
            self.meta["location"]["srid"] = int(items[2])
        except (IndexError, ValueError):
            raise ParsingError("Invalid location")

    def _ensure_location_attribute_exists(self) -> None:
        if "location" not in self.meta:
            self.meta["location"] = {}

    def get_altitude(self, name: str, value: str) -> None:
        self._ensure_location_attribute_exists()
        try:
            items = value.split()
            self.meta["location"]["altitude"] = float(items[0])
            self.meta["location"]["asrid"] = int(items[1]) if len(items) > 1 else None
        except (IndexError, ValueError):
            raise ParsingError("Invalid altitude")

    def read_minutes_months(self, s: str) -> Tuple[int, int]:
        """Return a (minutes, months) tuple after parsing a "M,N" string."""
        try:
            (minutes, months) = [int(x.strip()) for x in s.split(",")]
            return minutes, months
        except Exception:
            raise ParsingError(('Value should be "minutes, months"'))

    def read_meta_line(self, f: FileLike) -> Tuple[str, str]:
        """Read one line from a file format header and return a (name, value)
        tuple, where name is lowercased. Returns ('', '') if the next line is
        blank. Raises ParsingError if next line in f is not a valid header
        line."""
        line = f.readline()
        if isinstance(line, bytes):
            line = line.decode("utf-8-sig")
        assert isinstance(line, str)
        name, value = "", ""
        if line.isspace():
            return (name, value)
        if line.find("=") > 0:
            name, value = line.split("=", 1)
            name = name.rstrip().lower()
            value = value.strip()
        name = "" if any([c.isspace() for c in name]) else name
        if not name:
            raise ParsingError("Invalid file header line")
        return (name, value)


class HTimeseries:
    TEXT = "TEXT"
    FILE = "FILE"
    args: Dict[str, Optional[Any]] = {
        "format": None,
        "start_date": None,
        "end_date": None,
        "default_tzinfo": None,
    }
    comment: str
    location: Dict[str, Any] | None
    time_step: str
    _timezone: str | None
    precision: int | None
    unit: str
    title: str
    variable: str

    def __init__(
        self,
        data: Optional[Union[pd.DataFrame, FileLike]] = None,
        **kwargs: Any,
    ) -> None:
        extra_parms = set(kwargs) - set(self.args)
        if extra_parms:
            raise TypeError(
                "HTimeseries.__init__() got an unexpected keyword argument "
                f"'{extra_parms.pop()}'"
            )
        for arg, default_value in self.args.items():
            kwargs.setdefault(arg, default_value)
        if data is None:
            if not kwargs["default_tzinfo"]:
                kwargs["default_tzinfo"] = dt.timezone.utc
            self._read_filelike(StringIO(), **kwargs)
        elif isinstance(data, pd.DataFrame):
            self._check_dataframe(data)
            self.data = data
        else:
            self._read_filelike(data, **kwargs)

    def _check_dataframe(self, data: pd.DataFrame) -> None:
        if cast(pd.DatetimeIndex, data.index).tz is None:
            raise TypeError("data.index.tz must exist")

    def _read_filelike(self, f: FileLike, **kwargs: Any) -> None:
        reader = TimeseriesStreamReader(
            f,
            format=kwargs["format"],
            start_date=kwargs["start_date"],
            end_date=kwargs["end_date"],
            default_tzinfo=kwargs["default_tzinfo"],
        )
        self.__dict__.update(reader.get_metadata())
        try:
            tzinfo = TzinfoFromString(self._timezone)
        except AttributeError:
            tzinfo = kwargs["default_tzinfo"]
        self.data = reader.get_data(tzinfo)
        if self.data.size and (tzinfo is None):
            raise TypeError(
                "Cannot read filelike object without timezone or default_tzinfo "
                "specified"
            )

    def write(self, f: IO[str], format: str = TEXT, version: int = 5) -> None:
        writer = TimeseriesStreamWriter(self, f, format=format, version=version)
        writer.write()


class TimeseriesStreamReader:
    def __init__(
        self,
        f: FileLike,
        *,
        format: Optional[str],
        start_date: Optional[Union[str, dt.datetime]],
        end_date: Optional[Union[str, dt.datetime]],
        default_tzinfo: Optional[dt.tzinfo],
    ) -> None:
        self.f: FileLike = f
        self.specified_format = format
        self.start_date = start_date
        self.end_date = end_date
        self.default_tzinfo = default_tzinfo

    def get_metadata(self) -> Dict[str, Any]:
        if self.format == HTimeseries.FILE:
            return MetadataReader(self.f).meta
        else:
            return {}

    @property
    def format(self) -> str:
        if self.specified_format is None:
            return self.autodetected_format
        else:
            return self.specified_format

    @property
    def autodetected_format(self) -> str:
        if not hasattr(self, "_stored_autodetected_format"):
            self._stored_autodetected_format = FormatAutoDetector(self.f).detect()
        return self._stored_autodetected_format

    def get_data(self, tzinfo: Optional[dt.tzinfo]) -> pd.DataFrame:
        return TimeseriesRecordsReader(
            self.f, self.start_date, self.end_date, tzinfo=tzinfo
        ).read()


def _check_timeseries_index_has_no_duplicates(
    data: pd.DataFrame, error_message_prefix: str
) -> None:
    duplicate_dates = data.index[data.index.duplicated()].tolist()  # type: ignore
    if duplicate_dates:
        dates_str = ", ".join([str(x) for x in duplicate_dates])
        raise ValueError(
            f"{error_message_prefix}: the following timestamps appear more than "
            f"once: {dates_str}"
        )


class TimeseriesRecordsReader:
    def __init__(
        self,
        f: FileLike,
        start_date: Optional[Union[str, dt.datetime]],
        end_date: Optional[Union[str, dt.datetime]],
        tzinfo: Optional[dt.tzinfo],
    ) -> None:
        self.f = f
        self.start_date = start_date
        self.end_date = end_date
        self.tzinfo = tzinfo

    def read(self) -> pd.DataFrame:
        start_date, end_date = self._get_bounding_dates_as_strings()
        f2 = _FilePart(cast(TextFileLike, self.f), start_date, end_date)
        data = self._read_data_from_stream(f2)
        self._check_there_are_no_duplicates(data)
        return data

    def _get_bounding_dates_as_strings(self) -> Tuple[str, str]:
        start_date = "0001-01-01 00:00" if self.start_date is None else self.start_date
        end_date = "9999-12-31 00:00" if self.end_date is None else self.end_date
        if isinstance(start_date, dt.datetime):
            start_date = start_date.strftime("%Y-%m-%d %H:%M")
        if isinstance(end_date, dt.datetime):
            end_date = end_date.strftime("%Y-%m-%d %H:%M")
        return start_date, end_date

    def _read_data_from_stream(self, f: _FilePart) -> pd.DataFrame:
        dates, values, flags = self._read_csv(f)
        dates = self._localize_dates(dates)
        result = pd.DataFrame(
            {
                "value": np.array(values, dtype=np.float64),
                "flags": np.array(flags, dtype=str),
            },
            index=dates,
        )
        result.index.name = "date"
        return result

    def _localize_dates(self, dates: Sequence[str]) -> pd.DatetimeIndex:
        try:
            result: pd.DatetimeIndex = pd.to_datetime(dates)  # type: ignore
        except ValueError:
            raise ValueError(
                "Could not parse timestamps correctly. Maybe the CSV contains mixed "
                "aware and naive timestamps."
            )
        assert isinstance(result, pd.DatetimeIndex)
        if len(result) == 0 or (len(result) > 0 and result.tz is None):
            result = pd.to_datetime(dates).tz_localize(  # type: ignore
                self.tzinfo, ambiguous=len(dates) * [True]
            )
        assert isinstance(result, pd.DatetimeIndex)
        return result

    def _read_csv(self, f: _FilePart) -> Tuple[List[str], List[str], List[str]]:
        dates: List[str] = []
        values: List[str] = []
        flags: List[str] = []
        for row in csv.reader(f):  # We don't use pd.read_csv() because it's much slower
            if not len(row):
                continue
            dates.append(row[0])
            if len(row) > 1 and row[1]:
                values.append(row[1])
            else:
                values.append("NaN")
            flags.append(row[2] if len(row) > 2 else "")
        return dates, values, flags

    def _check_there_are_no_duplicates(self, data: pd.DataFrame) -> None:
        _check_timeseries_index_has_no_duplicates(
            data, error_message_prefix="Can't read time series"
        )


class FormatAutoDetector:
    def __init__(self, f: FileLike) -> None:
        self.f = f

    def detect(self) -> str:
        original_position = self.f.tell()
        result = self._guess_format_from_first_nonempty_line()
        self.f.seek(original_position)
        return result

    def _guess_format_from_first_nonempty_line(self) -> str:
        line = self._get_first_nonempty_line()
        if line and not line[0].isdigit():
            return HTimeseries.FILE
        else:
            return HTimeseries.TEXT

    def _get_first_nonempty_line(self) -> str:
        for line in self.f:
            if line.strip():
                if isinstance(line, bytes):
                    return line.decode("utf-8-sig")
                elif isinstance(line, str):
                    return line
                assert False, "Unreachable"
        return ""


class TimeseriesStreamWriter:
    def __init__(
        self,
        htimeseries: HTimeseries,
        f: IO[str],
        *,
        format: str,
        version: Optional[int],
    ) -> None:
        self.htimeseries = htimeseries
        self.f = f
        self.format = format
        self.version = version

    def write(self) -> None:
        self._write_metadata()
        self._write_records()

    def _write_metadata(self) -> None:
        if self.format == HTimeseries.FILE:
            version = self.version or 5
            MetadataWriter(self.f, self.htimeseries, version=version).write_meta()
            self.f.write("\r\n")

    def _write_records(self) -> None:
        TimeseriesRecordsWriter(self.htimeseries, self.f).write()


class TimeseriesRecordsWriter:
    def __init__(self, htimeseries: HTimeseries, f: IO[str]) -> None:
        self.htimeseries = htimeseries
        self.f = f
        self.float_format: str = "%f"

    def write(self) -> None:
        if self.htimeseries.data.empty:
            return
        self._check_there_are_no_duplicates()
        self._setup_precision()
        self._write_records()

    def _check_there_are_no_duplicates(self) -> None:
        _check_timeseries_index_has_no_duplicates(
            self.htimeseries.data, error_message_prefix="Can't write time series"
        )

    def _setup_precision(self) -> None:
        precision = getattr(self.htimeseries, "precision", None)
        if precision is None:
            self.float_format = "%f"
        elif precision >= 0:
            self.float_format = "%.{}f".format(self.htimeseries.precision)
        else:
            self.float_format = "%.0f"
            self._prepare_records_for_negative_precision(precision)

    def _prepare_records_for_negative_precision(self, precision: int) -> None:
        assert precision < 0
        datacol = self.htimeseries.data.columns[0]
        m = 10 ** (-precision)
        self.htimeseries.data[datacol] = np.rint(self.htimeseries.data[datacol] / m) * m

    def _write_records(self) -> None:
        self.htimeseries.data.to_csv(
            self.f,
            float_format=self.float_format,
            header=False,
            mode="w",
            lineterminator="\r\n",
            date_format="%Y-%m-%d %H:%M",
        )
