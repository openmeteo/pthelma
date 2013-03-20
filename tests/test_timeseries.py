#!/usr/bin/python
# -*- coding: utf8 -*-
"""
Tests for timeseries class.

Copyright (C) 2005-2009 National Technical University of Athens
Copyright (C) 2005 Antonios Christofides

This program is free software; you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation; either version 2 of the License, or
(at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.
"""

from pthelma.timeseries import *
import unittest
import types
import sys
import math
import textwrap
from datetime import datetime, timedelta
from StringIO import StringIO

big_test_timeseries = textwrap.dedent("""\
            2003-07-18 18:53,93,\r
            2003-07-19 19:52,108.7,\r
            2003-07-20 23:59,28.3,HEARTS SPADES\r
            2003-07-21 00:02,,\r
            2003-07-22 00:02,,DIAMONDS\r
            2003-07-23 18:53,93,\r
            2003-07-24 19:52,108.7,\r
            2003-07-25 23:59,28.3,HEARTS SPADES\r
            2003-07-26 00:02,,\r
            2003-07-27 00:02,,DIAMONDS\r
            2003-08-18 18:53,93,\r
            2003-08-19 19:52,108.7,\r
            2003-08-20 23:59,28.3,HEARTS SPADES\r
            2003-08-21 00:02,,\r
            2003-08-22 00:02,,DIAMONDS\r
            2003-08-23 18:53,93,\r
            2003-08-24 19:52,108.7,\r
            2003-08-25 23:59,28.3,HEARTS SPADES\r
            2003-08-26 00:02,,\r
            2003-08-27 00:02,,DIAMONDS\r
            2004-07-18 18:53,93,\r
            2004-07-19 19:52,108.7,\r
            2004-07-20 23:59,28.3,HEARTS SPADES\r
            2004-07-21 00:02,,\r
            2004-07-22 00:02,,DIAMONDS\r
            2004-07-23 18:53,93,\r
            2004-07-24 19:52,108.7,\r
            2004-07-25 23:59,28.3,HEARTS SPADES\r
            2004-07-26 00:02,,\r
            2004-07-27 00:02,,DIAMONDS\r
            2004-08-18 18:53,93,\r
            2004-08-19 19:52,108.7,\r
            2004-08-20 23:59,28.3,HEARTS SPADES\r
            2004-08-21 00:02,,\r
            2004-08-22 00:02,,DIAMONDS\r
            2004-08-23 18:53,93,\r
            2004-08-24 19:52,108.7,\r
            2004-08-25 23:59,28.3,HEARTS SPADES\r
            2004-08-26 00:02,,\r
            2004-08-27 00:02,,DIAMONDS\r
            2005-07-18 18:53,93,\r
            2005-07-19 19:52,108.7,\r
            2005-07-20 23:59,28.3,HEARTS SPADES\r
            2005-07-21 00:02,,\r
            2005-07-22 00:02,,DIAMONDS\r
            2005-07-23 18:53,91,\r
            2005-07-24 19:52,1087,\r
            2005-07-25 23:59,-28.3,HEARTS SPADES\r
            2005-07-26 00:02,,\r
            2005-07-27 00:02,,DIAMONDS\r
            2005-08-18 18:53,95,\r
            2005-08-19 19:52,110.7,\r
            2005-08-20 23:59,8.3,HEARTS SPADES\r
            2005-08-21 00:02,,\r
            2005-08-22 00:02,,DIAMONDS\r
            2005-08-23 18:53,94,\r
            2005-08-24 19:52,109.7,\r
            2005-08-25 23:59,27.3,HEARTS SPADES\r
            2005-08-26 00:02,,\r
            2005-08-27 00:02,,DIAMONDS\r
            """)

tenmin_test_timeseries = textwrap.dedent("""\
            2008-02-07 09:40,10.32,
            2008-02-07 09:50,10.42,
            2008-02-07 10:00,10.51,
            2008-02-07 10:10,10.54,
            2008-02-07 10:20,10.71,
            2008-02-07 10:30,10.96,
            2008-02-07 10:40,10.93,
            2008-02-07 10:50,11.10,
            2008-02-07 11:00,11.23,
            2008-02-07 11:10,11.44,
            2008-02-07 11:20,11.41,
            2008-02-07 11:30,11.42,MISS
            2008-02-07 11:40,11.54,
            2008-02-07 11:50,11.68,
            2008-02-07 12:00,11.80,
            2008-02-07 12:10,11.91,
            2008-02-07 12:20,12.16,
            2008-02-07 12:30,12.16,
            2008-02-07 12:40,12.24,
            2008-02-07 12:50,12.13,
            2008-02-07 13:00,12.17,
            2008-02-07 13:10,12.31,
            """)

tenmin_allmiss_test_timeseries = textwrap.dedent("""\
            2005-05-01 00:10,,
            2005-05-01 00:20,,
            2005-05-01 00:30,,
            2005-05-01 00:40,,
            2005-05-01 00:50,,
            2005-05-01 01:00,,
            2005-05-01 01:10,,
            2005-05-01 01:20,1,
            2005-05-01 01:30,,
            2005-05-01 01:40,1,
            2005-05-01 01:50,,
            2005-05-01 02:00,1,
            """)

tenmin_vector_test_timeseries = textwrap.dedent("""\
            2005-05-01 00:10,350,
            2005-05-01 00:20,355,
            2005-05-01 00:30,358,
            2005-05-01 00:40,2,
            2005-05-01 00:50,10,
            2005-05-01 01:00,5,
            2005-05-01 01:10,272,
            2005-05-01 01:20,268,
            2005-05-01 01:30,275,
            2005-05-01 01:40,265,
            2005-05-01 01:50,264,
            2005-05-01 02:00,276,
            """)

tenmin_test_timeseries_file = textwrap.dedent(u"""\
            Version=2\r
            Unit=°C\r
            Count=22\r
            Title=A test 10-min time series\r
            Comment=This timeseries is extremely important\r
            Comment=because the comment that describes it\r
            Comment=spans five lines.\r
            Comment=\r
            Comment=These five lines form two paragraphs.\r
            Timezone=EET (UTC+0200)\r
            Time_step=10,0\r
            Nominal_offset=0,0\r
            Actual_offset=0,0\r
            Variable=temperature\r
            Precision=1\r
            \r
            2008-02-07 09:40,10.3,\r
            2008-02-07 09:50,10.4,\r
            2008-02-07 10:00,10.5,\r
            2008-02-07 10:10,10.5,\r
            2008-02-07 10:20,10.7,\r
            2008-02-07 10:30,11.0,\r
            2008-02-07 10:40,10.9,\r
            2008-02-07 10:50,11.1,\r
            2008-02-07 11:00,11.2,\r
            2008-02-07 11:10,11.4,\r
            2008-02-07 11:20,11.4,\r
            2008-02-07 11:30,11.4,MISS\r
            2008-02-07 11:40,11.5,\r
            2008-02-07 11:50,11.7,\r
            2008-02-07 12:00,11.8,\r
            2008-02-07 12:10,11.9,\r
            2008-02-07 12:20,12.2,\r
            2008-02-07 12:30,12.2,\r
            2008-02-07 12:40,12.2,\r
            2008-02-07 12:50,12.1,\r
            2008-02-07 13:00,12.2,\r
            2008-02-07 13:10,12.3,\r
            """)

aggregated_hourly_sum = textwrap.dedent("""\
            2008-02-07 10:00,31.25,MISS\r
            2008-02-07 11:00,65.47,\r
            2008-02-07 12:00,69.29,MISS\r
            2008-02-07 13:00,72.77,\r
            """)

aggregated_hourly_average = textwrap.dedent("""\
            2008-02-07 10:00,10.4166666666667,MISS\r
            2008-02-07 11:00,10.911666667,\r
            2008-02-07 12:00,11.548333333,MISS\r
            2008-02-07 13:00,12.128333333,\r
            """)

aggregated_hourly_max = textwrap.dedent("""\
            2008-02-07 10:00,10.51,MISS\r
            2008-02-07 11:00,11.23,\r
            2008-02-07 12:00,11.8,MISS\r
            2008-02-07 13:00,12.24,\r
            """)

aggregated_hourly_min = textwrap.dedent("""\
            2008-02-07 10:00,10.32,MISS\r
            2008-02-07 11:00,10.54,\r
            2008-02-07 12:00,11.41,MISS\r
            2008-02-07 13:00,11.91,\r
            """)

aggregated_hourly_missing = textwrap.dedent("""\
            2008-02-07 10:00,3,\r
            2008-02-07 11:00,0,\r
            2008-02-07 12:00,0,\r
            2008-02-07 13:00,0,\r
            """)

aggregated_hourly_vector_average = textwrap.dedent("""\
            2005-05-01 01:00,0,\r
            2005-05-01 02:00,270,\r
            """)

aggregated_hourly_allmiss = textwrap.dedent("""\
            2005-05-01 02:00,3,MISS\r
            """)

aggregated_hourly_vector_missing = textwrap.dedent("""\
            2005-05-01 01:00,0,\r
            2005-05-01 02:00,0,\r
            """)

def extract_lines(s, from_, to):
    return ''.join(s.splitlines(True)[from_:to])

class _Test_timestep_utilities(unittest.TestCase):
    def setUp(self):
        self.dailystep = TimeStep(length_minutes=1440, nominal_offset=(480,0),
            actual_offset=(0,0))
        self.bimonthlystep = TimeStep(length_months=2, nominal_offset=(0,0),
            actual_offset=(-1442,2))
    def test_up1(self):
        self.assertEqual(self.dailystep.up(datetime(1964, 2, 29, 18, 35)),
            datetime(1964, 3, 1, 8, 0))
    def test_up2(self):
        self.assertEqual(self.dailystep.up(datetime(1964, 3, 1, 7, 59)),
            datetime(1964, 3, 1, 8, 0))
    def test_up3(self):
        self.assertEqual(self.dailystep.up(datetime(1964, 3, 1, 8, 0)),
            datetime(1964, 3, 1, 8, 0))
    def test_up4(self):
        self.assertEqual(self.bimonthlystep.up(datetime(1964, 2, 29, 18, 35)),
            datetime(1964, 3, 1, 0, 0))
    def test_up5(self):
        self.assertEqual(self.bimonthlystep.up(datetime(1963, 12, 31, 18, 35)),
            datetime(1964, 1, 1, 0, 0))
    def test_down1(self):
        self.assertEqual(self.dailystep.down(datetime(1964, 2, 29, 18, 35)),
            datetime(1964, 2, 29, 8, 0))
    def test_down2(self):
        self.assertEqual(self.dailystep.down(datetime(1964, 3, 1, 7, 59)),
            datetime(1964, 2, 29, 8, 0))
    def test_down3(self):
        self.assertEqual(self.dailystep.down(datetime(1964, 3, 1, 8, 0)),
            datetime(1964, 3, 1, 8, 0))
    def test_down4(self):
        self.assertEqual(self.bimonthlystep.down(datetime(1964, 2, 29, 18,
            35)), datetime(1964, 1, 1, 0, 0))
    def test_down5(self):
        self.assertEqual(self.bimonthlystep.down(datetime(1963, 12, 31, 18,
            35)), datetime(1963, 11, 1, 0, 0))
    def test_next1(self):
        self.assertEqual(self.dailystep.next(datetime(1964, 2, 29, 15, 12)),
            datetime(1964, 3, 2, 8, 0))
    def test_next2(self):
        self.assertEqual(self.dailystep.next(datetime(1964, 3, 2, 8, 0)),
            datetime(1964, 3, 3, 8, 0))
    def test_next3(self):
        self.assertEqual(self.bimonthlystep.next(datetime(1964, 2, 29, 15, 12)),
            datetime(1964, 5, 1, 0, 0))
    def test_next4(self):
        self.assertEqual(self.bimonthlystep.next(datetime(1964, 5, 1, 0, 0)),
            datetime(1964, 7, 1, 0, 0))
    def test_previous1(self):
        self.assertEqual(self.dailystep.previous(datetime(1964, 2, 29, 15, 12)),
            datetime(1964, 2, 28, 8, 0))
    def test_previous2(self):
        self.assertEqual(self.dailystep.previous(datetime(1964, 2, 29, 8, 0)),
            datetime(1964, 2, 28, 8, 0))
    def test_previous3(self):
        self.assertEqual(self.bimonthlystep.previous(datetime(1964, 2, 29, 15, 12)),
            datetime(1963, 11, 1, 0, 0))
    def test_previous4(self):
        self.assertEqual(self.bimonthlystep.previous(datetime(1963, 11, 1, 0, 0)),
            datetime(1963, 9, 1, 0, 0))
    def test_actual_timestamp1(self):
        self.assertEqual(self.dailystep.actual_timestamp(datetime(1964, 2, 29,
            8, 0)), datetime(1964, 2, 29, 8, 0))
    def test_actual_timestamp2(self):
        self.assertEqual(self.bimonthlystep.actual_timestamp(datetime(1964, 3,
            1, 0, 0)), datetime(1964, 4, 29, 23, 58))
    def test_containing_interval1(self):
        self.assertEqual(self.dailystep.containing_interval(datetime(
            1964, 2, 29, 15, 12)), datetime(1964, 3, 1, 8, 0))
    def test_containing_interval2(self):
        self.assertEqual(self.bimonthlystep.containing_interval(datetime(
            1964, 2, 29, 15, 12)), datetime(1964, 3, 1, 0, 0))
    def test_containing_interval3(self):
        self.assertEqual(self.bimonthlystep.containing_interval(datetime(
            1964, 4, 18, 15, 12)), datetime(1964, 3, 1, 0, 0))
    def test_interval_endpoints1(self):
        self.assertEqual(self.bimonthlystep.interval_endpoints(datetime(
            1964, 3, 1, 0, 0)),
            (datetime(1964, 2, 28, 23, 58), datetime(1964, 4, 29, 23, 58)))


class _Test_datetime_utilities(unittest.TestCase):
    def setUp(self):
        self.d = datetime(1964, 2, 29, 18, 35)
    def test_datetime_from_iso1(self):
        self.assertEqual(self.d, datetime_from_iso("1964-02-29 18:35"))
    def test_datetime_from_iso2(self):
        self.assertEqual(self.d, datetime_from_iso("1964-02-29T18:35"))
    def test_datetime_from_iso3(self):
        self.assertEqual(self.d, datetime_from_iso("1964-02-29t18:35"))
    def test_datetime_from_iso4(self):
        self.assertRaises(ValueError, datetime_from_iso, "1964")
    def test_datetime_from_iso5(self):
        self.assertRaises(ValueError, datetime_from_iso, "1965-29-29 18:35")
    def test_date_time_from_iso6(self):
        self.assertEqual(datetime(1964, 2, 29), datetime_from_iso("1964-02-29"))
    def test_isoformat_nosecs1(self):
        self.assertEqual(isoformat_nosecs(self.d), "1964-02-29T18:35")
    def test_isoformat_nosecs2(self):
        self.assertEqual(isoformat_nosecs(self.d, ' '), "1964-02-29 18:35")

class _Test_strip_trailing_zeros(unittest.TestCase):
    def test1(self): self.assertEqual(strip_trailing_zeros('hello'), 'hello')
    def test2(self): self.assertEqual(strip_trailing_zeros('hello0'), 'hello0')
    def test3(self): self.assertEqual(strip_trailing_zeros('850'), '850')
    def test4(self): self.assertEqual(strip_trailing_zeros('8500'), '8500')
    def test5(self): self.assertEqual(strip_trailing_zeros('0.0'), '0')
    def test6(self): self.assertEqual(strip_trailing_zeros('0.00'), '0')
    def test7(self): self.assertEqual(strip_trailing_zeros('18.3500'), '18.35')
    def test8(self): self.assertEqual(strip_trailing_zeros('18.000'), '18')

class _Test_Timeseries_setitem(unittest.TestCase):
    def setUp(self):
        self.ts = Timeseries()
        self.date = datetime_from_iso("1970-05-23 08:00")
    def test1(self):
        self.ts[self.date] = 8.2
        self.assertEqual(self.ts[self.date], 8.2)
        self.assertEqual(self.ts[self.date].flags, set([]))
    def test2(self):
        self.ts[self.date] = (9.3, ['RANGE', 'SPADE'])
        self.assertEqual(self.ts[self.date], 9.3)
        self.assertEqual(self.ts[self.date].flags, set(['RANGE', 'SPADE']))
        self.ts[self.date] = 8.2
        self.assertEqual(self.ts[self.date], 8.2)
        self.assertEqual(self.ts[self.date].flags, set(['RANGE', 'SPADE']))
    def test3(self):
        self.ts[self.date] = float('NaN')
        self.assert_(math.isnan(self.ts[self.date]))

class _Test_Timeseries_write_empty(unittest.TestCase):
    def setUp(self):
        self.ts = Timeseries()
        self.c = StringIO()
    def test(self):
        self.ts.write(self.c)
        self.assertEqual(self.c.getvalue(), '')

class _Test_Timeseries_write_nonempty(unittest.TestCase):
    def setUp(self):
        self.ts = Timeseries()
        self.c = StringIO()
        self.ts["2005-08-23 18:53"] = 93
        self.ts["2005-08-24 19:52"] = 108.7
        self.ts["2005-08-25 23:59"] = (28.3, ['HEARTS', 'SPADES'])
        self.ts["2005-08-26 00:02"] = float('NaN')
        self.ts["2005-08-27 00:02"] = (float('NaN'), ['DIAMONDS'])
    def test_all(self):
        self.ts.write(self.c)
        self.assertEqual(self.c.getvalue(), textwrap.dedent("""\
            2005-08-23 18:53,93,\r
            2005-08-24 19:52,108.7,\r
            2005-08-25 23:59,28.3,HEARTS SPADES\r
            2005-08-26 00:02,,\r
            2005-08-27 00:02,,DIAMONDS\r
            """))
    def test_with_start1(self):
        self.ts.write(self.c, start=datetime_from_iso("2005-08-24 19:52"))
        self.assertEqual(self.c.getvalue(), textwrap.dedent("""\
            2005-08-24 19:52,108.7,\r
            2005-08-25 23:59,28.3,HEARTS SPADES\r
            2005-08-26 00:02,,\r
            2005-08-27 00:02,,DIAMONDS\r
            """))
    def test_with_start2(self):
        self.ts.write(self.c, start=datetime_from_iso("2005-08-24 19:51"))
        self.assertEqual(self.c.getvalue(), textwrap.dedent("""\
            2005-08-24 19:52,108.7,\r
            2005-08-25 23:59,28.3,HEARTS SPADES\r
            2005-08-26 00:02,,\r
            2005-08-27 00:02,,DIAMONDS\r
            """))
    def test_with_start3(self):
        self.ts.write(self.c, start=datetime_from_iso("2000-08-24 19:51"))
        self.assertEqual(self.c.getvalue(), textwrap.dedent("""\
            2005-08-23 18:53,93,\r
            2005-08-24 19:52,108.7,\r
            2005-08-25 23:59,28.3,HEARTS SPADES\r
            2005-08-26 00:02,,\r
            2005-08-27 00:02,,DIAMONDS\r
            """))
    def test_with_end1(self):
        self.ts.write(self.c, end=datetime_from_iso("2005-08-27 00:02"))
        self.assertEqual(self.c.getvalue(), textwrap.dedent("""\
            2005-08-23 18:53,93,\r
            2005-08-24 19:52,108.7,\r
            2005-08-25 23:59,28.3,HEARTS SPADES\r
            2005-08-26 00:02,,\r
            2005-08-27 00:02,,DIAMONDS\r
            """))
    def test_with_end2(self):
        self.ts.write(self.c, end=datetime_from_iso("3005-08-27 00:02"))
        self.assertEqual(self.c.getvalue(), textwrap.dedent("""\
            2005-08-23 18:53,93,\r
            2005-08-24 19:52,108.7,\r
            2005-08-25 23:59,28.3,HEARTS SPADES\r
            2005-08-26 00:02,,\r
            2005-08-27 00:02,,DIAMONDS\r
            """))
    def test_with_end3(self):
        self.ts.write(self.c, end=datetime_from_iso("2005-08-26 00:03"))
        self.assertEqual(self.c.getvalue(), textwrap.dedent("""\
            2005-08-23 18:53,93,\r
            2005-08-24 19:52,108.7,\r
            2005-08-25 23:59,28.3,HEARTS SPADES\r
            2005-08-26 00:02,,\r
            """))
    def test_with_start_and_end1(self):
        self.ts.write(self.c, start=datetime_from_iso("2005-08-24 19:50"),
                      end=datetime_from_iso("2005-08-26 00:03"))
        self.assertEqual(self.c.getvalue(), textwrap.dedent("""\
            2005-08-24 19:52,108.7,\r
            2005-08-25 23:59,28.3,HEARTS SPADES\r
            2005-08-26 00:02,,\r
            """))
    def test_with_start_and_end2(self):
        self.ts.write(self.c, start=datetime_from_iso("2005-08-24 19:53"),
                      end=datetime_from_iso("2005-08-24 19:54"))
        self.assertEqual(self.c.getvalue(), "")

class _Test_Timeseries_file(unittest.TestCase):
    def setUp(self):
        self.reference_ts = Timeseries(
            time_step=TimeStep(length_minutes=10, length_months=0,
                                                    nominal_offset=(0,0)),
            unit=u'°C', title=u"A test 10-min time series", precision=1,
            timezone=u"EET (UTC+0200)", variable=u"temperature",
            comment=u"This timeseries is extremely important\n" 
                + u"because the comment that describes it\n"
                + u"spans five lines.\n\n"
                + u"These five lines form two paragraphs.")
        self.reference_ts.read(StringIO(tenmin_test_timeseries))
    def test_write_file(self):
        outstring = StringIO()
        self.reference_ts.write_file(outstring)
        self.assertEqual(outstring.getvalue(), tenmin_test_timeseries_file)
    def test_read_file(self):
        instring = StringIO(tenmin_test_timeseries_file)
        ts = Timeseries()
        ts.read_file(instring)
        self.assertEqual(ts.time_step.length_minutes,
                                self.reference_ts.time_step.length_minutes)
        self.assertEqual(ts.time_step.length_months,
                                self.reference_ts.time_step.length_months)
        self.assertEqual(ts.time_step.nominal_offset,
                                self.reference_ts.time_step.nominal_offset)
        self.assertEqual(ts.time_step.actual_offset,
                                self.reference_ts.time_step.actual_offset)
        self.assertEqual(ts.time_step.interval_type,
                                self.reference_ts.time_step.interval_type)
        self.assertEqual(ts.unit, self.reference_ts.unit)
        self.assertEqual(ts.title, self.reference_ts.title)
        self.assertEqual(ts.precision, self.reference_ts.precision)
        self.assertEqual(ts.timezone, self.reference_ts.timezone)
        self.assertEqual(ts.variable, self.reference_ts.variable)
        self.assertEqual(ts.comment, self.reference_ts.comment)
        self.assertEqual(len(ts), len(self.reference_ts))
        for d in self.reference_ts:
            self.assertAlmostEqual(ts[d], self.reference_ts[d], 1)
    
class _Test_Timeseries_read(unittest.TestCase):
    # This test trusts Timeseries.write, so it must be independently tested.
    def check(self, s):
        ts = Timeseries()
        instring = StringIO(s)
        outstring = StringIO()
        ts.read(instring)
        ts.write(outstring)
        self.assertEqual(outstring.getvalue(), instring.getvalue())
    def test_read_empty(self):
        self.check('')
    def test_read_nonempty(self):
        self.check(textwrap.dedent("""\
            2005-08-23 18:53,93,\r
            2005-08-24 19:52,108.7,\r
            2005-08-25 23:59,28.3,HEARTS SPADES\r
            2005-08-26 00:02,,\r
            2005-08-27 00:02,,DIAMONDS\r
            """))
    def test_error1(self):
        self.assertRaises(ValueError, Timeseries.read, Timeseries(),
                          StringIO('85'))
    def test_error2(self):
        self.assertRaises(ValueError, Timeseries.read, Timeseries(),
                          StringIO("""\
            2005-08-23 18:53,93,
            2005-08-24 19:52,108.7,
            2005-08-25 23:59,28.3,HEARTS SPADES
            2005-08-26 00:02,
            2005-08-27 00:02,,DIAMONDS
            """)) # Has only one comma in line four
    def test_error3(self):
        self.assertRaises(ValueError, Timeseries.read, Timeseries(),
                          StringIO('abcd,,'))
    
class database_test_metaclass(type):
    warning = textwrap.dedent("""\
        WARNING: Database tests not run. If you want to run the database
                 tests, set the PSYCOPG_CONNECTION environment variable
                 to "host=... dbname=... user=... password=...".
        """)
    def __new__(mcs, name, bases, dict):
        import os
        psycopg_string = os.getenv("PSYCOPG_CONNECTION")
        if not psycopg_string:
            sys.stderr.write(mcs.warning)
            return None
        return type.__new__(mcs, name, bases, dict)

class _Test_Timeseries_write_to_db(unittest.TestCase):
    __metaclass__ = database_test_metaclass
    def setUp(self):
        import os, psycopg2
        self.db = psycopg2.connect(os.getenv("PSYCOPG_CONNECTION"))
        c = self.db.cursor()
        c.execute('SET CONSTRAINTS ALL DEFERRED')
        c.close()
    def tearDown(self):
        self.db.rollback()
        self.db.close()
    def test_bottom_only(self):
        ts = Timeseries(0)
        ts.read(StringIO(textwrap.dedent("""\
            2005-08-23 18:53,93,
            2005-08-24 19:52,108.7,
            2005-08-25 23:59,28.3,HEARTS SPADES
            2005-08-26 00:02,,
            2005-08-27 00:02,,DIAMONDS
            """)))
        ts.write_to_db(self.db, commit=False)
        c = self.db.cursor()
        c.execute("""SELECT top, middle, bottom FROM ts_records
                     WHERE id=%d""" % (ts.id))
        (top, middle, bottom) = c.fetchone()
        c.close()
        sys.stderr.write('------------------\n'+top+'--------------------\n')
        self.assertFalse(top)
        self.assert_(middle is None)
        self.assertEqual(bottom, textwrap.dedent("""\
            2005-08-23 18:53,93,\r
            2005-08-24 19:52,108.7,\r
            2005-08-25 23:59,28.3,HEARTS SPADES\r
            2005-08-26 00:02,,\r
            2005-08-27 00:02,,DIAMONDS\r
            """))
    def test_top_middle_bottom(self):
        saved_max_all_bottom = Timeseries.MAX_BOTTOM
        Timeseries.MAX_ALL_BOTTOM = 20
        try:
            ts = Timeseries(0)
            ts.read(StringIO(big_test_timeseries))
            ts.write_to_db(self.db, commit=False)
            c = self.db.cursor()
            c.execute("""SELECT top, middle, bottom FROM ts_records
                         WHERE id=%d""" % (ts.id))
            (db_top, db_middle, db_bottom) = c.fetchone()
            c.close()
            actual_top = extract_lines(big_test_timeseries, None, 
                                       Timeseries.ROWS_IN_TOP_BOTTOM)
            actual_bottom = extract_lines(big_test_timeseries, 
                                          -Timeseries.ROWS_IN_TOP_BOTTOM, None)
            actual_middle = extract_lines(big_test_timeseries,
                Timeseries.ROWS_IN_TOP_BOTTOM, -Timeseries.ROWS_IN_TOP_BOTTOM)
            self.assertEqual(db_top, actual_top)
            self.assertEqual(zlib.decompress(str(db_middle)), actual_middle)
            self.assertEqual(db_bottom, actual_bottom)
        finally:
            Timeseries.MAX_ALL_BOTTOM = saved_max_all_bottom

class _Test_Timeseries_read_from_db(unittest.TestCase):
    __metaclass__ = database_test_metaclass
    # This test trusts Timeseries.write_to_db, so it must be independently tested
    def setUp(self):
        import os, psycopg2
        self.db = psycopg2.connect(os.getenv("PSYCOPG_CONNECTION"))
        c = self.db.cursor()
        c.execute('SET CONSTRAINTS ALL DEFERRED')
        c.close()
    def tearDown(self):
        self.db.rollback()
        self.db.close()
    def check(self, s):
        ts1 = Timeseries(0)
        instring = StringIO(s)
        outstring = StringIO()
        ts1.read(instring)
        ts1.write_to_db(self.db, commit=False)
        ts2 = Timeseries(0)
        ts2.read_from_db(self.db)
        ts2.write(outstring)
        self.assertEqual(outstring.getvalue(), instring.getvalue())
    def test_read_empty(self):
        self.check('')
    def test_read_nonempty_small(self):
        self.check(textwrap.dedent("""\
            2005-08-23 18:53,93,\r
            2005-08-24 19:52,108.7,\r
            2005-08-25 23:59,28.3,HEARTS SPADES\r
            2005-08-26 00:02,,\r
            2005-08-27 00:02,,DIAMONDS\r
            """))
    def test_read_nonempty_big(self):
        self.check(big_test_timeseries)
        
class _Test_Timeseries_append(unittest.TestCase):
    def test_append(self):
        ts1 = Timeseries()
        ts1.read(StringIO(extract_lines(big_test_timeseries, 0, 5)))
        ts2 = Timeseries()
        ts2.read(StringIO(extract_lines(big_test_timeseries, 5, 10)))
        ts1.append(ts2)
        out = StringIO()
        ts1.write(out)
        self.assertEqual(out.getvalue(),
                         extract_lines(big_test_timeseries, 0, 10))
        ts3 = Timeseries()
        ts3.read(StringIO(extract_lines(big_test_timeseries, 9, 10)))
        self.assertRaises(Exception, Timeseries.append, ts1, ts3)

class _Test_Timeseries_append_to_db(unittest.TestCase):
    __metaclass__ = database_test_metaclass
    # This trusts everything else, so no other test should trust append and
    # append_to_db.
    def setUp(self):
        import os, psycopg2
        self.db = psycopg2.connect(os.getenv("PSYCOPG_CONNECTION"))
        c = self.db.cursor()
        c.execute('SET CONSTRAINTS ALL DEFERRED')
        c.close()
    def tearDown(self):
        self.db.rollback()
        self.db.close()
    def test_append_to_db(self):
        out = StringIO()
        ts1 = Timeseries(0)
        ts1.read(StringIO(extract_lines(big_test_timeseries, 0, 5)))
        ts1.write_to_db(self.db, commit=False)
        ts1.clear()
        ts1.read(StringIO(extract_lines(big_test_timeseries, 5, 10)))
        ts1.append_to_db(self.db, commit=False)
        ts1.clear()
        ts1.read_from_db(self.db)
        ts1.write(out)
        self.assertEqual(out.getvalue(),
                         extract_lines(big_test_timeseries, 0, 10))
        ts1.clear()
        ts1.read(StringIO(extract_lines(big_test_timeseries, 10, None)))
        ts1.append_to_db(self.db, commit=False)
        ts1.clear()
        ts1.read_from_db(self.db)
        out.truncate(0)
        ts1.write(out)
        self.assertEqual(out.getvalue(), big_test_timeseries)
        ts1.clear()
        ts1.read(StringIO(extract_lines(big_test_timeseries, 10, None)))
        self.assertRaises(Exception, Timeseries.append_to_db, ts1, self.db,
                     commit=False)

class _Test_Timeseries_item(unittest.TestCase):
    def setUp(self):
        self.ts = Timeseries()
        self.ts.read(StringIO(big_test_timeseries))
    def test_matches_exactly(self):
        item = self.ts.item('2003-07-24 19:52')
        self.assertAlmostEqual(item[1], 108.7)
        self.assertEqual(isoformat_nosecs(item[0]), '2003-07-24T19:52')
    def test_matches_next(self):
        item = self.ts.item('2003-07-24 00:00')
        self.assertAlmostEqual(item[1], 108.7)
        self.assertEqual(isoformat_nosecs(item[0]), '2003-07-24T19:52')
    def test_matches_previous(self):
        item = self.ts.item('2003-07-25 00:00', downwards=True)
        self.assertAlmostEqual(item[1], 108.7)
        self.assertEqual(isoformat_nosecs(item[0]), '2003-07-24T19:52')
    def test_matches_first(self):
        item = self.ts.item('1999-02-28 17:03')
        self.assertAlmostEqual(item[1], 93)
        self.assertEqual(isoformat_nosecs(item[0]), '2003-07-18T18:53')
    def test_matches_last(self):
        item = self.ts.item('2009-02-28 17:03', downwards=True)
        self.assert_(math.isnan(item[1]))
        self.assertEqual(isoformat_nosecs(item[0]), '2005-08-27T00:02')
        self.assertEqual(item[1].flags, set(['DIAMONDS']))
    def test_index_error(self):
        self.assertRaises(IndexError, self.ts.item, '2005-08-27 00:03')
        self.assertRaises(IndexError, self.ts.item, '2003-07-18 18:52',
                                                    downwards=True)

class _Test_Timeseries_min_max_avg_sum(unittest.TestCase):
    def setUp(self):
        self.ts = Timeseries(time_step=TimeStep(length_minutes=10))
        self.ts.read(StringIO(big_test_timeseries))
    def test_min(self):
        value = self.ts.min('2004-08-18 00:00', '2004-08-22 00:00')
        self.assertAlmostEqual(value, 28.3)
    def test_max(self):
        value = self.ts.max('2004-08-18 00:00', '2004-08-22 00:00')
        self.assertAlmostEqual(value, 108.7)
    def test_average(self):
        value = self.ts.average('2004-08-18 00:00', '2004-08-22 00:00')
        self.assertAlmostEqual(value, 76.66666666667)
    def test_sum(self):
        value = self.ts.sum('2004-08-18 00:00', '2004-08-22 00:00')
        self.assertAlmostEqual(value, 230.0)
    def test_min_nan(self):
        value = self.ts.min('2004-08-21 00:00', '2004-08-22 12:00')
        self.assert_(math.isnan(value))
    def test_max_nan(self):
        value = self.ts.max('2004-08-21 00:00', '2004-08-22 12:00')
        self.assert_(math.isnan(value))
    def test_average_nan(self):
        value = self.ts.average('2004-08-21 00:00', '2004-08-22 12:00')
        self.assert_(math.isnan(value))
    def test_sum_nan(self):
        value = self.ts.sum('2004-08-21 00:00', '2004-08-22 12:00')
        self.assert_(math.isnan(value))


class _Test_Timeseries_aggregate(unittest.TestCase):
    def setUp(self):
        self.ts = Timeseries(time_step=TimeStep(length_minutes=10,
            nominal_offset=(0,0)))
        self.ts.read(StringIO(tenmin_test_timeseries))
    def test_aggregate_hourly_sum(self):
        target_step = TimeStep(length_minutes=60, nominal_offset=(0,0),
                                        interval_type=IntervalType.SUM)
        result, missing = self.ts.aggregate(target_step, missing_allowed=3,
            missing_flag="MISS")
        out = StringIO()
        result.write(out)
        self.assertEqual(out.getvalue(),aggregated_hourly_sum)
        out.truncate(0)
        missing.write(out)
        self.assertEqual(out.getvalue(),aggregated_hourly_missing)
    def test_aggregate_hourly_average(self):
        target_step = TimeStep(length_minutes=60, nominal_offset=(0,0),
                                    interval_type=IntervalType.AVERAGE)
        result, missing = self.ts.aggregate(target_step, missing_allowed=3,
            missing_flag="MISS")
        correct_ts = Timeseries()
        correct_ts.read(StringIO(aggregated_hourly_average))
        self.assertEqual(len(correct_ts.keys()), len(result.keys()))
        for d in correct_ts.keys():
            self.assertAlmostEqual(result[d], correct_ts[d], 4)
        out = StringIO()
        missing.write(out)
        self.assertEqual(out.getvalue(),aggregated_hourly_missing)
    def test_aggregate_hourly_max(self):
        target_step = TimeStep(length_minutes=60, nominal_offset=(0,0),
                                interval_type=IntervalType.MAXIMUM)
        result, missing = self.ts.aggregate(target_step, missing_allowed=3,
            missing_flag="MISS")
        out = StringIO()
        result.write(out)
        self.assertEqual(out.getvalue(),aggregated_hourly_max)
        out.truncate(0)
        missing.write(out)
        self.assertEqual(out.getvalue(),aggregated_hourly_missing)
    def test_aggregate_hourly_min(self):
        target_step = TimeStep(length_minutes=60, nominal_offset=(0,0),
                                interval_type=IntervalType.MINIMUM)
        result, missing = self.ts.aggregate(target_step, missing_allowed=3,
            missing_flag="MISS")
        out = StringIO()
        result.write(out)
        self.assertEqual(out.getvalue(),aggregated_hourly_min)
        out.truncate(0)
        missing.write(out)
        self.assertEqual(out.getvalue(),aggregated_hourly_missing)

class _Test_Timeseries_vector_aggregate(unittest.TestCase):
    def setUp(self):
        self.ts = Timeseries(time_step=TimeStep(length_minutes=10,
            nominal_offset=(0,0)))
        self.ts.read(StringIO(tenmin_vector_test_timeseries))
    def test_aggregate_hourly_vector(self):
        target_step = TimeStep(length_minutes=60, nominal_offset=(0,0),
                                interval_type=IntervalType.VECTOR_AVERAGE)
        result = (self.ts.aggregate(target_step, missing_allowed=0,
                                missing_flag="MISS"))[0]
        out = StringIO()
        result.write(out)
        self.assertEqual(out.getvalue(),aggregated_hourly_vector_average)

class _Test_Timeseries_allmiss_aggregate(unittest.TestCase):
    def setUp(self):
        self.ts = Timeseries(time_step=TimeStep(length_minutes=10,
            nominal_offset=(0,0)))
        self.ts.read(StringIO(tenmin_allmiss_test_timeseries))
    def test_aggregate_hourly_allmiss(self):
        target_step = TimeStep(length_minutes=60, nominal_offset=(0,0),
                                interval_type=IntervalType.SUM)
        result = (self.ts.aggregate(target_step, missing_allowed=6,
                                missing_flag="MISS"))[0]
        out = StringIO()
        result.write(out)
        self.assertEqual(out.getvalue(),aggregated_hourly_allmiss)

events_test_timeseries_1 = textwrap.dedent("""\
                    2008-02-07 09:40,-2.33,
                    2008-02-07 09:50,7.43,
                    2008-02-07 10:00,2.17,
                    2008-02-07 10:10,-0.70,
                    2008-02-07 10:20,-8.32,
                    2008-02-07 10:30,-1.20,
                    2008-02-07 10:40,5.53,
                    2008-02-07 10:50,4.80,
                    2008-02-07 11:00,-8.28,
                    2008-02-07 11:10,3.28,
                    2008-02-07 11:20,-9.56,
                    2008-02-07 11:30,-1.13,
                    2008-02-07 11:40,7.41,
                    2008-02-07 11:50,-0.57,
                    2008-02-07 12:00,5.82,
                    2008-02-07 12:10,-8.92,
                    2008-02-07 12:20,9.19,
                    2008-02-07 12:30,-2.79,
                    2008-02-07 12:40,-5.24,
                    2008-02-07 12:50,-4.87,
                    2008-02-07 13:00,-2.51,
                    2008-02-07 13:10,5.26,
                    """)

events_test_timeseries_2 = textwrap.dedent("""\
                    2008-02-07 09:40,-0.58,
                    2008-02-07 09:50,-6.50,
                    2008-02-07 10:00,-8.14,
                    2008-02-07 10:10,2.78,
                    2008-02-07 10:20,-9.38,
                    2008-02-07 10:30,-5.28,
                    2008-02-07 10:40,7.41,
                    2008-02-07 10:50,3.02,
                    2008-02-07 11:00,5.87,
                    2008-02-07 11:10,0.66,
                    2008-02-07 11:20,-8.72,
                    2008-02-07 11:30,6.05,
                    2008-02-07 11:40,1.65,
                    2008-02-07 11:50,-1.01,
                    2008-02-07 12:00,-6.26,
                    2008-02-07 12:10,-8.62,
                    2008-02-07 12:20,-9.28,
                    2008-02-07 12:30,9.28,
                    2008-02-07 12:40,2.83,
                    2008-02-07 12:50,-0.43,
                    2008-02-07 13:00,5.59,
                    2008-02-07 13:10,-4.87,
                    """)

events_test_timeseries_3 = textwrap.dedent("""\
                    2008-02-07 09:40,4.06,
                    2008-02-07 09:50,2.60,
                    2008-02-07 10:00,5.05,
                    2008-02-07 10:10,-9.76,
                    2008-02-07 10:20,-1.39,
                    2008-02-07 10:30,-9.11,
                    2008-02-07 10:40,-8.25,
                    2008-02-07 10:50,-2.26,
                    2008-02-07 11:00,-7.57,
                    2008-02-07 11:10,1.42,
                    2008-02-07 11:20,-4.30,
                    2008-02-07 11:30,6.54,
                    2008-02-07 11:40,-5.13,
                    2008-02-07 11:50,-6.28,
                    2008-02-07 12:00,8.07,
                    2008-02-07 12:10,-5.70,
                    2008-02-07 12:20,-5.42,
                    2008-02-07 12:30,-1.98,
                    2008-02-07 12:40,5.70,
                    2008-02-07 12:50,4.37,
                    2008-02-07 13:00,-7.03,
                    2008-02-07 13:10,-7.34,
                    """)


class _Test_Timeseries_identify_events(unittest.TestCase):

    def setUp(self):
        self.ts1 = Timeseries(time_step=TimeStep(length_minutes=10,
                                                    nominal_offset=(0,0)))
        self.ts2 = Timeseries(time_step=TimeStep(length_minutes=10,
                                                    nominal_offset=(0,0)))
        self.ts3 = Timeseries(time_step=TimeStep(length_minutes=10,
                                                    nominal_offset=(0,0)))
        self.ts1.read(StringIO(events_test_timeseries_1))
        self.ts2.read(StringIO(events_test_timeseries_2))
        self.ts3.read(StringIO(events_test_timeseries_3))

    def test_find_events_more_than_4(self):
        events = identify_events((self.ts1, self.ts2, self.ts3), 4.0, 2,
                        timedelta(minutes=30), ntimeseries_end_threshold=1)
        self.assertEqual(len(events), 2)
        self.assertEqual(events[0][0], datetime(2008, 2, 7, 10, 40))
        self.assertEqual(events[0][1], datetime(2008, 2, 7, 11, 0))
        self.assertEqual(events[1][0], datetime(2008, 2, 7, 11, 30))
        self.assertEqual(events[1][1], datetime(2008, 2, 7, 13, 10))
    def test_find_events_less_than_zero(self):
        events = identify_events((self.ts1, self.ts2, self.ts3), 0.0, 3,
                        timedelta(minutes=20), ntimeseries_end_threshold=2,
                        reverse=True)
        self.assertEqual(len(events), 4)
        self.assertEqual(events[0][0], datetime(2008, 2, 7, 10, 20))
        self.assertEqual(events[0][1], datetime(2008, 2, 7, 10, 30))
        self.assertEqual(events[1][0], datetime(2008, 2, 7, 11, 20))
        self.assertEqual(events[1][1], datetime(2008, 2, 7, 11, 20))
        self.assertEqual(events[2][0], datetime(2008, 2, 7, 11, 50))
        self.assertEqual(events[2][1], datetime(2008, 2, 7, 11, 50))
        self.assertEqual(events[3][0], datetime(2008, 2, 7, 12, 10))
        self.assertEqual(events[3][1], datetime(2008, 2, 7, 12, 30))
    def test_find_events_in_only_one_timeseries(self):
        events = identify_events((self.ts1,), 4.0, 1, timedelta(minutes=30),
                    start_date=datetime(2008, 2, 7, 10,0))
        self.assertEqual(len(events), 3)
        self.assertEqual(events[0][0], datetime(2008, 2, 7, 10, 40))
        self.assertEqual(events[0][1], datetime(2008, 2, 7, 10, 50))
        self.assertEqual(events[1][0], datetime(2008, 2, 7, 11, 40))
        self.assertEqual(events[1][1], datetime(2008, 2, 7, 12, 20))
        self.assertEqual(events[2][0], datetime(2008, 2, 7, 13, 10))
        self.assertEqual(events[2][1], datetime(2008, 2, 7, 13, 10))

