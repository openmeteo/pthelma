#!/usr/bin/python
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
import textwrap
from datetime import datetime
from cStringIO import StringIO

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
            2008-02-07 11:10,11.45,
            2008-02-07 11:20,11.41,
            2008-02-07 11:30,11.42,
            2008-02-07 11:40,11.54,
            2008-02-07 11:50,11.68,
            2008-02-07 12:00,11.80,
            2008-02-07 12:10,11.91,
            2008-02-07 12:20,12.16,
            2008-02-07 12:30,12.16,
            2008-02-07 12:40,12.25,
            2008-02-07 12:50,12.13,
            2008-02-07 13:00,12.17,
            2008-02-07 13:10,12.31,
            """)

aggregated_hourly_sum = textwrap.dedent("""\
            2008-02-07 10:00,31.25,MISS\r
            2008-02-07 11:00,65.47,\r
            2008-02-07 12:00,69.3,\r
            2008-02-07 13:00,72.78,\r
            """)

aggregated_hourly_average = textwrap.dedent("""\
            2008-02-07 10:00,10.4166666666667,MISS\r
            2008-02-07 11:00,10.911666667,\r
            2008-02-07 12:00,11.55,\r
            2008-02-07 13:00,12.13,\r
            """)

aggregated_hourly_max = textwrap.dedent("""\
            2008-02-07 10:00,10.51,MISS\r
            2008-02-07 11:00,11.23,\r
            2008-02-07 12:00,11.8,\r
            2008-02-07 13:00,12.25,\r
            """)

aggregated_hourly_min = textwrap.dedent("""\
            2008-02-07 10:00,10.32,MISS\r
            2008-02-07 11:00,10.54,\r
            2008-02-07 12:00,11.41,\r
            2008-02-07 13:00,11.91,\r
            """)

aggregated_hourly_missing = textwrap.dedent("""\
            2008-02-07 10:00,3,\r
            2008-02-07 11:00,0,\r
            2008-02-07 12:00,0,\r
            2008-02-07 13:00,0,\r
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
        self.ts[self.date] = fpconst.NaN
        self.assert_(fpconst.isNaN(self.ts[self.date]))

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
        self.ts["2005-08-26 00:02"] = fpconst.NaN
        self.ts["2005-08-27 00:02"] = (fpconst.NaN, ['DIAMONDS'])
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
        self.assert_(fpconst.isNaN(item[1]))
        self.assertEqual(isoformat_nosecs(item[0]), '2005-08-27T00:02')
        self.assertEqual(item[1].flags, set(['DIAMONDS']))
    def test_index_error(self):
        self.assertRaises(IndexError, self.ts.item, '2005-08-27 00:03')
        self.assertRaises(IndexError, self.ts.item, '2003-07-18 18:52',
                                                    downwards=True)

class _Test_Timeseries_min_max_avg(unittest.TestCase):
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
    def test_min_nan(self):
        value = self.ts.min('2004-08-21 00:00', '2004-08-22 12:00')
        self.assert_(fpconst.isNaN(value))
    def test_max_nan(self):
        value = self.ts.max('2004-08-21 00:00', '2004-08-22 12:00')
        self.assert_(fpconst.isNaN(value))
    def test_average_nan(self):
        value = self.ts.average('2004-08-21 00:00', '2004-08-22 12:00')
        self.assert_(fpconst.isNaN(value))

class _Test_Timeseries_aggregate(unittest.TestCase):
    def setUp(self):
        self.ts = Timeseries(time_step=TimeStep(length_minutes=10))
        self.ts.read(StringIO(tenmin_test_timeseries))
    def test_aggregate_hourly_sum(self):
        target_step = TimeStep(length_minutes=60, interval_type=IntervalType.SUM)
        result, missing = self.ts.aggregate(target_step, missing_allowed=3,
            missing_flag="MISS")
        out = StringIO()
        result.write(out)
        self.assertEqual(out.getvalue(),aggregated_hourly_sum)
        out.truncate(0)
        missing.write(out)
        self.assertEqual(out.getvalue(),aggregated_hourly_missing)
    def test_aggregate_hourly_average(self):
        target_step = TimeStep(length_minutes=60,
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
        target_step = TimeStep(length_minutes=60,
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
        target_step = TimeStep(length_minutes=60,
                                interval_type=IntervalType.MINIMUM)
        result, missing = self.ts.aggregate(target_step, missing_allowed=3,
            missing_flag="MISS")
        out = StringIO()
        result.write(out)
        self.assertEqual(out.getvalue(),aggregated_hourly_min)
        out.truncate(0)
        missing.write(out)
        self.assertEqual(out.getvalue(),aggregated_hourly_missing)
    ### def test_aggregate_hourly_vector(self):
        ### pending
