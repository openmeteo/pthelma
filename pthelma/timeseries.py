#!/usr/bin/python
"""
Timeseries processing
=====================

Copyright (C) 2005-2011 National Technical University of Athens

Copyright (C) 2005 Antonis Christofides

This program is free software; you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation; either version 2 of the License, or
(at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.
"""

from calendar import monthrange
from ctypes import CDLL, c_int, c_longlong, c_double, c_char, c_char_p, \
    byref, Structure, c_void_p, POINTER, string_at
from datetime import datetime, timedelta, tzinfo
import math
from math import sin, cos, atan2, pi
import random
import re
import zlib

import six
from six import u, StringIO
from six.moves.configparser import ParsingError

import iso8601
import pytz
from simpletail import ropen

psycopg2 = None  # Do not import unless needed


class T_REC(Structure):
    _fields_ = [("timestamp", c_longlong),
                ("null", c_int),
                ("value", c_double),
                ("flags", c_char_p)]


class T_INTERVAL(Structure):
    _fields_ = [("start_date", c_longlong),
                ("end_date", c_longlong)]


class T_INTERVALLIST(Structure):
    _fields_ = [("intervals", POINTER(T_INTERVAL)),
                ("n", c_int)]


class T_TIMESERIESLIST(Structure):
    _fields = [("ts", c_void_p),
               ("n", c_int)]

import platform
dickinson = CDLL(
    (platform.system() == 'Windows' and 'dickinson.dll') or
    (platform.system().startswith('Darwin') and 'libdickinson.dylib') or
    'libdickinson.so')

dickinson.ts_get_item.restype = T_REC
dickinson.ts_create.restype = c_void_p
dickinson.tsl_create.restype = POINTER(T_TIMESERIESLIST)
dickinson.il_create.restype = POINTER(T_INTERVALLIST)
dickinson.ts_min.restype = c_double
dickinson.ts_max.restype = c_double
dickinson.ts_average.restype = c_double
dickinson.ts_sum.restype = c_double
dickinson.ts_write.restype = POINTER(c_char)
dickinson.ts_get_next.restype = POINTER(T_REC)
dickinson.ts_get_prev.restype = POINTER(T_REC)


def datetime_from_iso(isostring):
    return iso8601.parse_date(isostring, default_timezone=None)


def isoformat_nosecs(adatetime, sep='T'):
    return adatetime.isoformat(sep)[:16]


def add_months_to_datetime(adatetime, months):
    m, y, d = adatetime.month, adatetime.year, adatetime.day
    m += months
    while m > 12:
        m -= 12
        y += 1
    while m < 1:
        m += 12
        y -= 1
    d = min(d, monthrange(y, m)[1])
    return adatetime.replace(year=y, month=m, day=d)


_DT_BASE = datetime(1970, 1, 1, 0, 0)
_DT_BASE_AWARE = datetime(1970, 1, 1, 0, 0, tzinfo=pytz.utc)
_SECONDS_PER_DAY = 86400
if 'long' in [c.__name__ for c in six.integer_types]:
    _SECONDS_PER_DAY = long(_SECONDS_PER_DAY)


def is_aware(d):
    return (d.tzinfo is not None) and (d.tzinfo.utcoffset(d) is not None)


def _datetime_to_time_t(d):
    """Convert d (a datetime or iso string) to number of seconds since 1970"""
    if not isinstance(d, datetime):
        d = iso8601.parse_date(d, default_timezone=None)
    dt_base = _DT_BASE_AWARE if is_aware(d) else _DT_BASE
    delta = d - dt_base
    return delta.days * _SECONDS_PER_DAY + delta.seconds


def _time_t_to_datetime(t):
    """Convert t (number of seconds since 1970) to datetime."""
    return _DT_BASE + timedelta(days=t // 86400, seconds=t % 86400)


datere = re.compile(r"""(?P<year>\d+)
                        (-(?P<month>\d+)
                            (-(?P<day>\d+)
                            ([ tT](?P<hour>\d+):(?P<minute>\d+))?
                            )?
                        )?
                    """, re.VERBOSE)


def datestr_diff(datestr1, datestr2):
    m1 = datere.match(datestr1)
    m2 = datere.match(datestr2)
    year1 = int(m1.group('year'))
    year2 = int(m2.group('year'))
    month1 = int(m1.group('month') or 1)
    month2 = int(m2.group('month') or 1)
    day1 = int(m1.group('day') or 1)
    day2 = int(m2.group('day') or 1)
    hour1 = int(m1.group('hour') or 0)
    hour2 = int(m2.group('hour') or 0)
    minute1 = int(m1.group('minute') or 0)
    minute2 = int(m2.group('minute') or 0)

    date1 = datetime(year1, month1, day1, hour1, minute1)
    date2 = datetime(year2, month2, day2, hour2, minute2)
    return date_diff(date1, date2)


def date_diff(date1, date2):
    if date1 >= date2:
        return _date_diff(date1, date2)
    else:
        months, minutes = _date_diff(date2, date1)
        return (-months, -minutes)


def _date_diff(date1, date2):
    """
    Similar to date_diff, but lower level and used by it. Only works if
    date1 >= date2.
    """
    diff_months = (date1.year - date2.year) * 12 + date1.month - date2.month
    date2a = add_months_to_datetime(date2, diff_months)
    if date2a > date1:
        diff_months -= 1
        date2a = add_months_to_datetime(date2a, -1)
    diff_minutes = int((date1 - date2a).total_seconds()) / 60
    return (diff_months, diff_minutes)


class TzinfoFromString(tzinfo):
    """Create a tzinfo object from a string formatted as "+0000" or as
       "XXX (+0000)" or as "XXX (UTC+0000)".
    """

    def __init__(self, string):
        self.offset = None
        self.name = ''
        if not string:
            return

        # If string contains brackets, set tzname to whatever is before the
        # brackets and retrieve the part inside the brackets.
        i = string.find('(')
        if i > 0:
            self.name = string[:i].strip()
        s = string[i + 1:]
        i = s.find(')')
        i = len(s) if i < 0 else i
        s = s[:i]

        # Remove any preceeding 'UTC' (as in "UTC+0200")
        s = s[3:] if s.startswith('UTC') else s

        # s should be in +0000 format
        try:
            if len(s) != 5:
                raise ValueError()
            sign = {'+': 1, '-': -1}[s[0]]
            hours = int(s[1:3])
            minutes = int(s[3:5])
        except (ValueError, IndexError):
            raise ValueError('Time zone {} is invalid'.format(string))

        self.offset = sign * timedelta(hours=hours, minutes=minutes)

    def utcoffset(self, dt):
        return self.offset

    def dst(self, dt):
        return timedelta(0)

    def tzname(self, dt):
        return self.name


def read_timeseries_tail_from_db(db, id):
    c = db.cursor()
    c.execute("""SELECT bottom FROM ts_records
                 WHERE id=%d""" % (id,))
    r = c.fetchone()
    bottom_lines = r[0].strip().splitlines()
    c.close()
    if not bottom_lines:
        raise ValueError('No time series with id=%d found' % (id,))
    return bottom_lines[-1].split(',')[:2]


def read_timeseries_tail_from_file(filename):

    def get_next_line(fp):
        try:
            return fp.next()
        except StopIteration:
            raise ValueError('File {} does not contain a time series'.
                             format(filename))

    with ropen(filename) as fp:
        last_line = get_next_line(fp)
        datestring = last_line.split(',')[0]
        try:
            return iso8601.parse_date(datestring, default_timezone=None)
        except ValueError as e:
            exception = e

        # We were unable to read the last line. Perhaps the time series has no
        # data?
        while last_line.isspace():
            last_line = get_next_line(fp)  # Skip empty lines
        if '=' in last_line:
            return None  # Last line looks like "name=value" - empty series

        # No evidence that this is a time series with no data.
        raise ValueError(exception.message
                         + ' (file {}, last line)'.format(filename))


def timeseries_bounding_dates_from_db(db, id):
    c = db.cursor()
    c.execute("""SELECT timeseries_start_date(%d)""" % (id,))
    r = c.fetchone()
    start_date = r[0]
    c.execute("""SELECT timeseries_end_date(%d)""" % (id,))
    r = c.fetchone()
    end_date = r[0]
    return start_date, end_date


class IntervalType:
    SUM = 1
    AVERAGE = 2
    MINIMUM = 3
    MAXIMUM = 4
    VECTOR_AVERAGE = 5


class TimeStep:

    def __init__(self, length_minutes=0, length_months=0, interval_type=None,
                 timestamp_rounding=None, timestamp_offset=(0, 0)):
        self.length_minutes = length_minutes
        self.length_months = length_months
        self.timestamp_rounding = timestamp_rounding
        self.timestamp_offset = timestamp_offset
        self.interval_type = interval_type

    def _check_timestamp_rounding(self):
        """Called whenever an operation requires timestamp rounding; verifies
        that timestamp_rounding is not None, otherwise raises exception."""
        if self.timestamp_rounding:
            return
        raise ValueError("This operation requires timestamp_rounding")

    def up(self, timestamp):
        self._check_timestamp_rounding()
        if self.length_minutes:
            required_modulo = self.timestamp_rounding[0]
            if required_modulo < 0:
                required_modulo += self.length_minutes
            reference_date = timestamp.replace(day=1, hour=0, minute=0)
            d = timestamp - reference_date
            diff_in_minutes = d.days * 1440 + d.seconds / 60
            actual_modulo = diff_in_minutes % self.length_minutes
            result = timestamp - timedelta(
                minutes=actual_modulo - required_modulo)
            while result < timestamp:
                result += timedelta(minutes=self.length_minutes)
            return result
        else:
            y = timestamp.year - 1
            m = 1 + self.timestamp_rounding[1]
            result = timestamp.replace(
                year=y, month=m, day=1, hour=0, minute=0) + \
                timedelta(minutes=self.timestamp_rounding[0])
            while result < timestamp:
                m += self.length_months
                if m > 12:
                    m -= 12
                    y += 1
                result = timestamp.replace(
                    year=y, month=m, day=1, hour=0, minute=0) + \
                    timedelta(minutes=self.timestamp_rounding[0])
            return result

    def down(self, timestamp):
        self._check_timestamp_rounding()
        if self.length_minutes:
            required_modulo = self.timestamp_rounding[0]
            if required_modulo < 0:
                required_modulo += self.length_minutes
            reference_date = timestamp.replace(day=1, hour=0, minute=0)
            d = timestamp - reference_date
            diff_in_minutes = d.days * 1440 + d.seconds / 60
            actual_modulo = diff_in_minutes % self.length_minutes
            result = timestamp + timedelta(minutes=required_modulo -
                                           actual_modulo)
            while result > timestamp:
                result -= timedelta(minutes=self.length_minutes)
        elif self.length_months:
            y = timestamp.year + 1
            m = 1 + self.timestamp_rounding[1]
            result = timestamp.replace(
                year=y, month=m, day=1, hour=0, minute=0) + \
                timedelta(minutes=self.timestamp_rounding[0])
            while result > timestamp:
                m -= self.length_months
                if m < 1:
                    m += 12
                    y -= 1
                result = timestamp.replace(
                    year=y, month=m, day=1, hour=0, minute=0) + \
                    timedelta(minutes=self.timestamp_rounding[0])
        else:
            assert(False)
        return result

    def next(self, timestamp):
        timestamp = self.up(timestamp)
        m = timestamp.month
        y = timestamp.year
        m += self.length_months
        while m > 12:
            m -= 12
            y += 1
        timestamp = timestamp.replace(year=y, month=m)
        return timestamp + timedelta(minutes=self.length_minutes)

    def previous(self, timestamp):
        timestamp = self.down(timestamp)
        m = timestamp.month
        y = timestamp.year
        m -= self.length_months
        while m < 1:
            m += 12
            y -= 1
        timestamp = timestamp.replace(year=y, month=m)
        return timestamp - timedelta(minutes=self.length_minutes)

    def actual_timestamp(self, timestamp):
        m = timestamp.month + self.timestamp_offset[1]
        y = timestamp.year
        while m > 12:
            m -= 12
            y += 1
        while m < 1:
            m += 12
            y -= 1
        return timestamp.replace(year=y, month=m) + \
            timedelta(minutes=self.timestamp_offset[0])

    def containing_interval(self, timestamp):
        result = self.down(timestamp)
        while self.actual_timestamp(result) >= timestamp:
            result = self.previous(result)
        while self.actual_timestamp(result) < timestamp:
            result = self.next(result)
        return result

    def interval_endpoints(self, nominal_timestamp):
        end_date = self.actual_timestamp(nominal_timestamp)
        start_date = self.actual_timestamp(self.previous(nominal_timestamp))
        return start_date, end_date


class _Tsvalue(float):

    def __new__(cls, value, flags=[]):
        return super(_Tsvalue, cls).__new__(cls, value)

    def __init__(self, value, flags=[]):
        self.flags = set(flags)


def strip_trailing_zeros(s):
    if s.rfind('.') > 0:
        s = s.rstrip('0')
    if s[-1] == '.':
        s = s[:-1]
    return s


class BacktrackableFile(object):

    def __init__(self, fp):
        self.fp = fp
        self.line_number = 0
        self.next_line = None

    def readline(self):
        if self.next_line is None:
            self.line_number += 1
            result = self.fp.readline()
        else:
            result = self.next_line
            self.next_line = None
        return result

    def backtrack(self, line):
        self.next_line = line

    def read(self, size=None):
        return self.fp.read() if size is None else self.fp.read(size)


class Timeseries(dict):

    # Some constants for how timeseries records are distributed in
    # top, middle, and bottom.  Records are appended to bottom, except
    # if bottom would then have more than MAX_BOTTOM plus/minus
    # MAX_BOTTOM_NOISE records (i.e. random noise, evenly distributed
    # between -MAX_BOTTOM_NOISE and +MAX_BOTTOM_NOISE is added to
    # MAX_BOTTOM; this is to avoid reaching circumstances where 20
    # timeseries will be repacked altogether).  If a timeseries is
    # stored entirely from scratch, then all records go to bottom if
    # they are less than MAX_ALL_BOTTOM; otherwise ROWS_IN_TOP_BOTTOM
    # go to top, another as much go to bottom, the rest goes to
    # middle.
    MAX_BOTTOM = 1000
    MAX_BOTTOM_NOISE = 150
    MAX_ALL_BOTTOM = 80
    ROWS_IN_TOP_BOTTOM = 20

    SQLDRIVER_NONE = 0
    SQLDRIVER_PSYCOPG2 = 1

    def __init__(self, id=0, time_step=None, unit=u(''), title=u(''),
                 timezone=u(''), variable=u(''), precision=None, comment=u(''),
                 location={}, driver=SQLDRIVER_PSYCOPG2):
        self.ts_handle = None
        self.id = id
        if time_step:
            self.time_step = time_step
        else:
            self.time_step = TimeStep()
        self.unit = unit
        self.title = title
        self.timezone = timezone
        self.variable = variable
        self.precision = precision
        self.comment = comment
        assert(driver in (self.SQLDRIVER_NONE, self.SQLDRIVER_PSYCOPG2))
        self.driver = driver
        self.location = location
        self.ts_handle = c_void_p(dickinson.ts_create())
        if self.ts_handle.value == 0:
            raise MemoryError.Create('Could not allocate memory '
                                     'for time series object.')
        # When the object is being destroyed, it doesn't always have access
        # to module globals (see Python documentation on the __del__ special
        # method), and therefore we keep a copy of the required globals here.
        self.__dickinson = dickinson

    def __repr__(self):
        metastr = StringIO()
        self.write_meta(metastr, version=3)
        datastr = StringIO()
        self.write(datastr)
        lines = datastr.getvalue()[:-2].split('\r\n')
        if len(lines) > 7:
            lines = lines[:3] + ['...'] + lines[-3:]
        return metastr.getvalue() + '\n' + '\n'.join(lines)

    def __del__(self):
        if self.ts_handle is None:
            return
        if self.ts_handle.value != 0:
            self.__dickinson.ts_free(self.ts_handle)
        self.ts_handle.value = 0

    def __len__(self):
        return dickinson.ts_length(self.ts_handle)

    def __delitem__(self, key):
        index_c = dickinson.ts_get_i(
            self.ts_handle, c_longlong(self.__datetime_to_time_t(key)))
        if index_c < 0:
            raise KeyError(
                'No such record: ' + (isoformat_nosecs(key, ' ')
                                      if isinstance(key, datetime)
                                      else key))
        dickinson.ts_delete_item(self.ts_handle, index_c)

    def __contains__(self, key):
        index_c = dickinson.ts_get_i(
            self.ts_handle, c_longlong(self.__datetime_to_time_t(key)))
        if index_c < 0:
            return False
        else:
            return True

    def __setitem__(self, key, value):
        timestamp_c = c_longlong(self.__datetime_to_time_t(key))
        index_c = dickinson.ts_get_i(self.ts_handle, timestamp_c)
        if isinstance(value, _Tsvalue):
            tsvalue = value
        elif isinstance(value, tuple):
            tsvalue = _Tsvalue(value[0], value[1])
        elif index_c >= 0:
            tsvalue = _Tsvalue(value, self[key].flags)
        else:
            tsvalue = _Tsvalue(value, [])
        if math.isnan(tsvalue):
            null_c = 1
            value_c = c_double(0)
        else:
            null_c = 0
            value_c = c_double(tsvalue)
        flags_c = c_char_p((' '.join(tsvalue.flags)).encode('ascii'))
        err_str_c = c_char_p()
        index_c = c_int()
        err_no_c = dickinson.ts_insert_record(
            self.ts_handle, timestamp_c, null_c, value_c, flags_c, c_int(1),
            byref(index_c), byref(err_str_c))
        if err_no_c != 0:
            raise Exception('Something wrong occured in dickinson '
                            'function when setting a time series value. '
                            'Error message: ' + repr(err_str_c.value))

    def __getitem__(self, key):
        if not isinstance(key, datetime) and (
                (not isinstance(key, six.string_types[0]) and
                 not isinstance(key, six.text_type))
                or len(key) < 4 or not key[0].isdigit()):
            raise KeyError(key)
        timestamp_c = c_longlong(self.__datetime_to_time_t(key))
        index_c = dickinson.ts_get_i(self.ts_handle, timestamp_c)
        if index_c < 0:
            raise KeyError(
                'No such record: ' + (isoformat_nosecs(key, ' ')
                                      if isinstance(key, datetime)
                                      else key))
        arec = dickinson.ts_get_item(self.ts_handle, index_c)
        if arec.null == 1:
            value = float('NaN')
        else:
            value = arec.value
        flags = arec.flags.decode('ascii')
        flags = flags.split()
        return _Tsvalue(value, flags)

    def __datetime_to_time_t(self, d):
        """Return a time_t key for the time series.

        d is an object that is being used as an index. If either d or the
        Timeseries object is naive, any time zone information is ignored.  If
        both are aware, the time zones of both are taken into account when
        converting d to time_t.
        """
        if not self.timezone or not isinstance(d, datetime) or not is_aware(d):
            # Either the Timeseries object or d is naive. In this case, ignore
            # time zones altogether and convert d to time_t.
            if isinstance(d, datetime):
                d = d.replace(tzinfo = None)
            return _datetime_to_time_t(d)
        else:
            # Both the Timeseries object and d are aware. However, the
            # Timeseries object timestamps are always stored naively, so we
            # must add the timeseries' utcoffset to d to make it
            # consistent.
            return _datetime_to_time_t(d) + int(TzinfoFromString(
                self.timezone).utcoffset(None).total_seconds())

    def __time_t_to_datetime(self, t):
        """Return a datetime key for the time series.

        t is a time_t internally stored as an index for the time series. This
        function returns the datetime that corresponds to it. If the Timeseries
        object is naive, the datetime object returned is naive. Otherwise,
        an aware datetime object is returned.
        """
        result = _time_t_to_datetime(t)
        if self.timezone:
            result = result.replace(tzinfo=TzinfoFromString(self.timezone))
        return result

    def delete_items(self, date1, date2):
        bd = self.bounding_dates()
        if not bd:
            return
        if not date1:
            date1 = bd[0]
        if not date2:
            date2 = bd[1]
        timestamp_c1 = c_longlong(self.__datetime_to_time_t(date1))
        timestamp_c2 = c_longlong(self.__datetime_to_time_t(date2))
        p1 = dickinson.ts_get_next(self.ts_handle, timestamp_c1)
        p2 = dickinson.ts_get_prev(self.ts_handle, timestamp_c2)
        if p1 and p2:
            dickinson.ts_delete_records(self.ts_handle, p1, p2)

    def get(self, key, default=None):
        if self.__contains__(key):
            return self.__getitem__(key)
        else:
            return default

    def keys(self):
        a = []
        i = 0
        while i < dickinson.ts_length(self.ts_handle):
            rec = dickinson.ts_get_item(self.ts_handle, c_int(i))
            a.append(self.__time_t_to_datetime(rec.timestamp))
            i += 1
        return a

    def iterkeys(self):
        i = 0
        while i < dickinson.ts_length(self.ts_handle):
            rec = dickinson.ts_get_item(self.ts_handle, c_int(i))
            yield self.__time_t_to_datetime(rec.timestamp)
            i += 1
    __iter__ = iterkeys

    def clear(self):
        i = dickinson.ts_length(self.ts_handle)
        while i >= 0:
            dickinson.ts_delete_item(self.ts_handle, i)
            i -= 1

    def read(self, fp, line_number=1):
        err_str_c = c_char_p()
        errline = c_int()
        try:
            if dickinson.ts_readfromstring(
                    c_char_p(fp.read().encode('ascii')), self.ts_handle,
                    byref(errline), byref(err_str_c)):
                line_number += errline.value - 1
                raise ValueError('Error when reading time series '
                                 'line from I/O: ' + repr(err_str_c.value))
            line_number += errline.value - 1
        except Exception as e:
            e.args = e.args + (line_number,)
            raise

    def write(self, fp, start=None, end=None):
        errstr = c_char_p()
        start_date = c_longlong.in_dll(dickinson, "LONG_TIME_T_MIN") \
            if start is None else c_longlong(self.__datetime_to_time_t(start))
        end_date = c_longlong.in_dll(dickinson, "LONG_TIME_T_MAX") \
            if end is None else c_longlong(self.__datetime_to_time_t(end))
        text = dickinson.ts_write(
            self.ts_handle,
            c_int(self.precision if self.precision is not None else -9999),
            start_date, end_date, byref(errstr))
        if not text:
            if not errstr:
                fp.write('')
                return
            raise IOError('Error when writing time series: %s' %
                          (errstr.value,))
        try:
            fp.write(string_at(text).decode('ascii'))
        finally:
            dickinson.freemem(text)

    def write_plain_values(self, fp, nullstr=''):
        i = 0
        lines = []
        while i < dickinson.ts_length(self.ts_handle):
            rec = dickinson.ts_get_item(self.ts_handle, c_int(i))
            lines.append(nullstr if rec.null else str(rec.value))
            i += 1
        fp.write('\r\n'.join(lines))

    def delete_from_db(self, db):
        c = db.cursor()
        c.execute("""DELETE FROM ts_records
                     WHERE id=%d""" % (self.id))
        self.clear()
        c.close()

    def __read_meta_line(self, fp):
        """Read one line from a file format header and return a (name, value)
        tuple, where name is lowercased. Returns ('', '') if the next line is
        blank. Raises ParsingError if next line in fp is not a valid header
        line."""
        line = fp.readline()
        if isinstance(line, six.binary_type):
            line = line.decode('utf-8-sig')
        name, value = '', ''
        if line.isspace():
            return (name, value)
        if line.find('=') > 0:
            name, value = line.split('=', 1)
            name = name.rstrip().lower()
            value = value.strip()
        name = '' if any([c.isspace() for c in name]) else name
        if not name:
            raise ParsingError("Invalid file header line")
        return (name, value)

    def read_meta(self, fp):
        """Read the headers of a file in file format into the instance
        attributes and return the line number of the first data line of the
        file.
        """
        if not isinstance(fp, BacktrackableFile):
            fp = BacktrackableFile(fp)

        def read_minutes_months(s):
            """Return a (minutes, months) tuple after parsing a "M,N" string.
            """
            try:
                (minutes, months) = [int(x.strip()) for x in s.split(',')]
                return minutes, months
            except Exception:
                raise ParsingError(('Value should be "minutes, months"'))

        try:
            self.comment = ''
            (name, value) = self.__read_meta_line(fp)
            while name:
                name = (name == 'nominal_offset' and 'timestamp_rounding' or
                        name)
                name = (name == 'actual_offset' and 'timestamp_offset' or name)
                if name in ('unit', 'title', 'timezone', 'variable'):
                    self.__dict__[name] = value
                elif name == 'time_step':
                    minutes, months = read_minutes_months(value)
                    self.time_step.length_minutes = minutes
                    self.time_step.length_months = months
                elif name in ('timestamp_rounding', 'timestamp_offset'):
                    self.time_step.__dict__[name] = read_minutes_months(value)
                elif name == 'interval_type':
                    try:
                        self.time_step.interval_type = IntervalType.__dict__[
                            value.upper()]
                    except KeyError:
                        raise ParsingError(("Invalid interval type"))
                elif name == 'precision':
                    try:
                        self.precision = int(value)
                    except ValueError as e:
                        raise ParsingError(e.args)
                elif name == 'comment':
                    if self.comment:
                        self.comment += '\n'
                    self.comment += value
                elif name == 'location':
                    try:
                        items = value.split()
                        (self.location['abscissa'],
                         self.location['ordinate'],
                         self.location['srid']) = (float(items[0]),
                                                   float(items[1]),
                                                   int(items[2]))
                    except (IndexError, ValueError):
                        raise ParsingError("Invalid location")
                elif name == 'altitude':
                    try:
                        items = value.split()
                        self.location['altitude'] = float(items[0])
                        self.location['asrid'] = int(items[1]) \
                            if len(items) > 1 else None
                    except (IndexError, ValueError):
                        raise ParsingError("Invalid altitude")
                else:
                    pass
                name, value = self.__read_meta_line(fp)
                if not name and not value:
                    return
        except ParsingError as e:
            e.args = e.args + (fp.line_number,)
            raise

    def read_file(self, fp):
        fp = BacktrackableFile(fp)

        # Check if file contains headers
        first_line = fp.readline()
        fp.backtrack(first_line)
        if isinstance(first_line, six.binary_type):
            first_line = first_line.decode('utf-8-sig')
        has_headers = not first_line[0].isdigit()

        # Read file, with its headers if needed
        if has_headers:
            self.read_meta(fp)
        self.read(fp)

    def write_meta(self, fp, version):
        if version == 2:
            fp.write(u("Version=2\r\n"))
        timestamp_rounding_name = (version >= 4 and 'Timestamp_rounding' or
                                   'Nominal_offset')
        timestamp_offset_name = (version >= 4 and 'Timestamp_offset' or
                                 'Actual_offset')
        if self.unit:
            fp.write(u("Unit=%s\r\n") % (self.unit,))
        fp.write(u("Count=%d\r\n") % (len(self),))
        if self.title:
            fp.write(u("Title=%s\r\n") % (self.title,))
        for line in self.comment.splitlines():
            fp.write(u("Comment=%s\r\n") % (line,))
        if self.timezone:
            fp.write(u("Timezone=%s\r\n") % (self.timezone,))
        if self.time_step.length_minutes or self.time_step.length_months:
            fp.write(u("Time_step=%d,%d\r\n") % (self.time_step.length_minutes,
                                                 self.time_step.length_months))
            if self.time_step.timestamp_rounding:
                fp.write(u("{n}={o[0]},{o[1]}\r\n").format(
                    n=timestamp_rounding_name,
                    o=self.time_step.timestamp_rounding))

            fp.write(u("{n}={o[0]},{o[1]}\r\n").format(
                n=timestamp_offset_name,
                o=self.time_step.timestamp_offset))
        if self.time_step.interval_type:
            fp.write(
                u("Interval_type={}\r\n").format({
                    IntervalType.SUM: u("sum"),
                    IntervalType.AVERAGE: u("average"),
                    IntervalType.MAXIMUM: u("maximum"),
                    IntervalType.MINIMUM: u("minimum"),
                    IntervalType.VECTOR_AVERAGE: u("vector_average")
                }[self.time_step.interval_type]))
        if self.variable:
            fp.write(u("Variable=%s\r\n") % (self.variable,))
        if self.precision is not None:
            fp.write(u("Precision=%d\r\n") % (self.precision,))
        if (version > 2) and self.location:
            try:
                fp.write(
                    u("Location={:.6f} {:.6f} {}\r\n")
                    .format(*[self.location[x]
                            for x in ['abscissa', 'ordinate', 'srid']]))
            except KeyError:
                pass

            # Write location
            loc = self.location  # Nickname
            altitude = loc['altitude'] if 'altitude' in loc else None
            asrid = loc['asrid'] if 'asrid' in loc else None
            fmt = u("Altitude={altitude:.2f} {asrid}\r\n") \
                if asrid else u("Altitude={altitude:.2f}\r\n")
            if altitude is not None:
                fp.write(fmt.format(altitude=altitude, asrid=asrid))

    def write_file(self, fp, version=2):
        self.write_meta(fp, version)
        fp.write("\r\n")
        self.write(fp)

    def read_from_db(self, db, bottom_only=False):
        c = db.cursor()
        if not bottom_only:
            querystr = """SELECT top, middle, bottom FROM ts_records
                          WHERE id=%d"""
        else:
            querystr = """SELECT bottom FROM ts_records WHERE id=%d"""
        c.execute(querystr % (self.id))
        r = c.fetchone()
        self.clear()
        if r:
            if bottom_only:
                (bottom,) = r
            else:
                (top, middle, bottom) = r
            if not bottom_only and top:
                self.read(StringIO(top))
                self.read(StringIO(zlib.decompress(middle)))
            self.read(StringIO(bottom))
        c.close()

    def blob_create(self, s):
        if self.driver == self.SQLDRIVER_NONE:
            return ''
        elif self.driver == self.SQLDRIVER_PSYCOPG2:
            global psycopg2
            if psycopg2 is None:
                import psycopg2
            return psycopg2.Binary(s)
        else:
            assert(False)

    def write_to_db(self, db, transaction=None, commit=True):
        if transaction is None:
            transaction = db
        fp = StringIO()
        if len(self) < Timeseries.MAX_ALL_BOTTOM:
            top = ''
            middle = None
            self.write(fp)
            bottom = fp.getvalue()
        else:
            dates = sorted(self.keys())
            self.write(fp, end=dates[Timeseries.ROWS_IN_TOP_BOTTOM - 1])
            top = fp.getvalue()
            fp.truncate(0)
            fp.seek(0)
            self.write(fp, start=dates[Timeseries.ROWS_IN_TOP_BOTTOM],
                       end=dates[-(Timeseries.ROWS_IN_TOP_BOTTOM + 1)])
            middle = self.blob_create(
                zlib.compress(fp.getvalue().encode('ascii')))
            fp.truncate(0)
            fp.seek(0)
            self.write(fp, start=dates[-Timeseries.ROWS_IN_TOP_BOTTOM])
            bottom = fp.getvalue()
        fp.close()
        c = db.cursor()
        c.execute("DELETE FROM ts_records WHERE id=%d" % (self.id))
        c.execute("""INSERT INTO ts_records (id, top, middle, bottom)
                     VALUES (%s, %s, %s, %s)""", (self.id, top, middle,
                  bottom))
        c.close()
        if commit:
            transaction.commit()

    def append_to_db(self, db, transaction=None, commit=True):
        """Append the contained records to the timeseries stored in the
        database."""
        if transaction is None:
            transaction = db
        if not len(self):
            return
        c = db.cursor()
        bottom_ts = Timeseries()
        c.execute("SELECT bottom FROM ts_records WHERE id=%d" %
                  (self.id))
        r = c.fetchone()
        if r:
            bottom_ts.read(StringIO(r[0]))
            if bottom_ts.keys() and max(bottom_ts.keys()) >= min(self.keys()):
                raise ValueError((
                    "Cannot append time series: "
                    "its first record (%s) has a date earlier than the last "
                    "record (%s) of the timeseries to append to.")
                    % (str(min(self.keys())), str(max(bottom_ts.keys()))))
        max_bottom = Timeseries.MAX_BOTTOM + random.randrange(
            -Timeseries.MAX_BOTTOM_NOISE, Timeseries.MAX_BOTTOM_NOISE)
        if len(bottom_ts) and len(bottom_ts) + len(self) < max_bottom:
            fp = StringIO()
            bottom_ts.write(fp)
            self.write(fp)
            c.execute("""UPDATE ts_records SET bottom=%s
                         WHERE id=%s""", (fp.getvalue(), self.id))
            fp.close()
            if commit:
                transaction.commit()
        else:
            ts = Timeseries(self.id)
            ts.read_from_db(db)
            ts.append(self)
            ts.write_to_db(db, transaction=transaction, commit=commit)
        c.close()

    def append(self, b):
        if len(self) and len(b) and max(self.keys()) >= min(b.keys()):
            raise ValueError(
                "Cannot append: the first record (%s) of the "
                "time series to append has a date earlier than the last "
                "record (%s) of the timeseries to append to."
                % (str(min(b.keys())), str(max(self.keys()))))
        err_str_c = c_char_p()
        if dickinson.ts_merge(self.ts_handle, b.ts_handle, byref(err_str_c)) \
                != 0:
            raise Exception('An exception has occured when trying to '
                            'merge time series. Error message: ' +
                            repr(err_str_c.value))

    def bounding_dates(self):
        if len(self):
            rec1 = dickinson.ts_get_item(self.ts_handle, c_int(0))
            rec2 = dickinson.ts_get_item(self.ts_handle, c_int(len(self) - 1))
            return self.__time_t_to_datetime(rec1.timestamp),\
                self.__time_t_to_datetime(rec2.timestamp)
        else:
            return None

    def items(self, pos=None):
        a = []
        i = 0
        if pos is not None:
            if pos < 0 or pos >= dickinson.ts_length(self.ts_handle):
                raise IndexError(
                    "Index (%d) out of bounds (%d, %d)" % (
                        pos, 0, dickinson.ts_length(self.ts_handle) - 1,))
            i = pos
        while i < dickinson.ts_length(self.ts_handle):
            rec = dickinson.ts_get_item(self.ts_handle, c_int(i))
            a.append((self.__time_t_to_datetime(rec.timestamp),
                     _Tsvalue(float('NaN') if rec.null else rec.value,
                              rec.flags.split())))
            if pos is not None:
                break
            i += 1
        return a if pos is None else a[0]

    def index(self, date, downwards=False):
        timestamp_c = c_longlong(self.__datetime_to_time_t(date))
        if not downwards:
            pos = dickinson.ts_get_next_i(self.ts_handle, timestamp_c)
        else:
            pos = dickinson.ts_get_prev_i(self.ts_handle, timestamp_c)
        if pos < 0:
            raise IndexError(
                "There is no item in the timeseries on or %s %s"
                % ("before" if downwards else "after", str(date)))
        return pos

    def item(self, date, downwards=False):
        rec = dickinson.ts_get_item(self.ts_handle, c_int(self.index(date,
                                    downwards)))
        return (
            self.__time_t_to_datetime(rec.timestamp),
            _Tsvalue(float('NaN') if rec.null else rec.value,
                     rec.flags.decode('ascii').split()))

    def _get_bounding_indexes(self, start_date, end_date):
        """Return a tuple, (start_index, end_index).  If arguments are None,
        the respective bounding date is considered. The results are the start
        and end indexes in items() of all items that are in the specified
        interval.
        """
        (s, e) = self.bounding_dates()
        if not start_date:
            start_date = s
        if not end_date:
            end_date = e
        return (self.index(start_date), self.index(end_date, downwards=True))

    def min(self, start_date=None, end_date=None):
        start_date = c_longlong.in_dll(dickinson, "LONG_TIME_T_MIN") \
            if start_date is None \
            else c_longlong(self.__datetime_to_time_t(start_date))
        end_date = c_longlong.in_dll(dickinson, "LONG_TIME_T_MAX") \
            if end_date is None \
            else c_longlong(self.__datetime_to_time_t(end_date))
        return dickinson.ts_min(self.ts_handle, start_date, end_date)

    def max(self, start_date=None, end_date=None):
        start_date = c_longlong.in_dll(dickinson, "LONG_TIME_T_MIN") \
            if start_date is None \
            else c_longlong(self.__datetime_to_time_t(start_date))
        end_date = c_longlong.in_dll(dickinson, "LONG_TIME_T_MAX") \
            if end_date is None \
            else c_longlong(self.__datetime_to_time_t(end_date))
        return dickinson.ts_max(self.ts_handle, start_date, end_date)

    def average(self, start_date=None, end_date=None):
        start_date = c_longlong.in_dll(dickinson, "LONG_TIME_T_MIN") \
            if start_date is None \
            else c_longlong(self.__datetime_to_time_t(start_date))
        end_date = c_longlong.in_dll(dickinson, "LONG_TIME_T_MAX") \
            if end_date is None \
            else c_longlong(self.__datetime_to_time_t(end_date))
        return dickinson.ts_average(self.ts_handle, start_date, end_date)

    def sum(self, start_date=None, end_date=None):
        start_date = c_longlong.in_dll(dickinson, "LONG_TIME_T_MIN") \
            if start_date is None \
            else c_longlong(self.__datetime_to_time_t(start_date))
        end_date = c_longlong.in_dll(dickinson, "LONG_TIME_T_MAX") \
            if end_date is None \
            else c_longlong(self.__datetime_to_time_t(end_date))
        return dickinson.ts_sum(self.ts_handle, start_date, end_date)

    def aggregate(self, target_step, missing_allowed=0.0, missing_flag="",
                  last_incomplete=False, all_incomplete=False):

        def aggregate_one_step(d, test_run=False, explicit_components=0):
            """Return tuple of ((result value, flags), missing) for a single
            target stamp d."""

            def timedeltadivide(a, b):
                """Divide timedelta a by timedelta b."""
                a = a.days * 86400 + a.seconds
                b = b.days * 86400 + b.seconds
                return a / b

            d_start_date, d_end_date = target_step.interval_endpoints(d)
            start_nominal = self.time_step.containing_interval(d_start_date)
            end_nominal = self.time_step.containing_interval(d_end_date)
            s = start_nominal
            it = target_step.interval_type
            if it in (IntervalType.SUM, IntervalType.AVERAGE):
                aggregate_value = 0.0
            elif it == IntervalType.MAXIMUM:
                aggregate_value = -1e38
            elif it == IntervalType.MINIMUM:
                aggregate_value = 1e38
            elif it == IntervalType.VECTOR_AVERAGE:
                aggregate_value = (0, 0)
            elif it is None:
                aggregate_value = float('NaN')
            else:
                assert(False)
            missing = 0.0
            total_components = 0.0
            divider = 0.0
            source_has_missing = False
            while s <= end_nominal:
                s_start_date, s_end_date = self.time_step.interval_endpoints(s)
                used_interval = s_end_date - s_start_date
                unused_interval = timedelta()
                if s_start_date < d_start_date:
                    out = d_start_date - s_start_date
                    unused_interval += out
                    used_interval -= out
                if s_end_date > d_end_date:
                    out = s_end_date - d_end_date
                    unused_interval += out
                    used_interval -= out
                pct_used = timedeltadivide(used_interval,
                                           unused_interval + used_interval)
                total_components += pct_used
                if math.isnan(self.get(s, float('NaN'))):
                    missing += pct_used
                    if last_incomplete or all_incomplete:
                        if s > self.bounding_dates()[1]:
                            missing -= pct_used
                            if test_run:
                                explicit_components = \
                                    total_components - pct_used
                                break
                    s = self.time_step.next(s)
                    continue
                divider += pct_used
                if missing_flag in self[s].flags:
                    source_has_missing = True
                if it in (IntervalType.SUM, IntervalType.AVERAGE):
                    aggregate_value += self.get(s, 0) * pct_used
                elif it == IntervalType.MAXIMUM:
                    if pct_used > 0:
                        aggregate_value = max(aggregate_value, self[s])
                elif it == IntervalType.MINIMUM:
                    if pct_used > 0:
                        aggregate_value = min(aggregate_value, self[s])
                elif it == IntervalType.VECTOR_AVERAGE:
                    aggregate_value = (
                        aggregate_value[0] + cos(self[s] / 180 * pi)
                        * pct_used,
                        aggregate_value[1] + sin(self[s] / 180 * pi)
                        * pct_used)
                elif it is None:
                    total_components, missing = 1, 1
                    aggregate_value = self.get(end_nominal, float('NaN'))
                    if not math.isnan(aggregate_value):
                        missing = 0
                    break
                else:
                    assert(False)
                if all_incomplete and not test_run:
                    if total_components >= explicit_components:
                        break
                s = self.time_step.next(s)
            flag = []
            if not test_run and (missing / total_components > \
                    missing_allowed + 1e-10 \
                    or abs(missing - total_components) < 1e-10):
                aggregate_value = float('NaN')
            else:
                if (missing / total_components > 1e-36) or \
                        source_has_missing:
                    flag = [missing_flag]
                if it == IntervalType.AVERAGE:
                    aggregate_value /= divider
                elif it == IntervalType.VECTOR_AVERAGE:
                    aggregate_value = atan2(aggregate_value[1],
                                            aggregate_value[0]) / pi * 180
                    while aggregate_value < 0:
                        aggregate_value += 360
                    if abs(aggregate_value - 360) < 1e-7:
                        aggregate_value = 0
            return (aggregate_value, flag), missing, explicit_components

        result = Timeseries(time_step=target_step)
        result.timezone = self.timezone
        missing = Timeseries(time_step=target_step)
        bounding_dates = self.bounding_dates()
        if not bounding_dates:
            return result, missing
        source_start_date, source_end_date = bounding_dates
        target_start_date = target_step.previous(source_start_date)
        target_end_date = target_step.next(source_end_date)
        ec = 0
        it = 0

        if all_incomplete:
            d = target_end_date
            while d >= target_start_date:
                dummy1, dummy2, ec = aggregate_one_step(
                    d, test_run=True, explicit_components=ec)
                it += 1
                if ec > 0 or it > 3:
                    break
                d = target_step.previous(d)
            if ec == 0:
                ec = 1e9

        d = target_start_date
        while d <= target_end_date:
            result[d], missing[d], dummy3 = aggregate_one_step(
                d, test_run=False, explicit_components=ec)
            d = target_step.next(d)
        while math.isnan(result.get(target_start_date, 0)):
            del result[target_start_date]
            del missing[target_start_date]
            target_start_date = target_step.next(target_start_date)
        while math.isnan(result.get(target_end_date, 0)):
            del result[target_end_date]
            del missing[target_end_date]
            target_end_date = target_step.previous(target_end_date)
        return result, missing


def identify_events(ts_list,
                    start_threshold, ntimeseries_start_threshold,
                    time_separator,
                    end_threshold=None, ntimeseries_end_threshold=None,
                    start_date=None, end_date=None, reverse=False):
    if end_threshold is None:
        end_threshold = start_threshold
    if ntimeseries_end_threshold is None:
        ntimeseries_end_threshold = ntimeseries_start_threshold
    range_start_date = c_longlong.in_dll(dickinson, "LONG_TIME_T_MIN") \
        if start_date is None else c_longlong(_datetime_to_time_t(start_date))
    range_end_date = c_longlong.in_dll(dickinson, "LONG_TIME_T_MAX") \
        if end_date is None else c_longlong(_datetime_to_time_t(end_date))
    search_range = T_INTERVAL(range_start_date, range_end_date)
    try:
        a_timeseries_list = dickinson.tsl_create()
        a_interval_list = dickinson.il_create()
        if (not a_timeseries_list) or (not a_interval_list):
            raise MemoryError('Insufficient memory')
        for t in ts_list:
            if dickinson.tsl_append(a_timeseries_list, t.ts_handle):
                raise MemoryError('Insufficient memory')
        errstr = c_char_p()
        if dickinson.ts_identify_events(
                a_timeseries_list, search_range, c_int(reverse),
                c_double(start_threshold), c_double(end_threshold),
                c_int(ntimeseries_start_threshold),
                c_int(ntimeseries_end_threshold),
                c_longlong(time_separator.days * _SECONDS_PER_DAY +
                           time_separator.seconds),
                a_interval_list, byref(errstr)):
            raise Exception(errstr.value)
        result = []
        for i in range(a_interval_list.contents.n):
            a_interval = a_interval_list.contents.intervals[i]
            result.append((_time_t_to_datetime(a_interval.start_date),
                           _time_t_to_datetime(a_interval.end_date)))
        return result
    finally:
        dickinson.il_free(a_interval_list)
        dickinson.tsl_free(a_timeseries_list)
