#!/usr/bin/python
"""
Tests for meteologger.

Copyright (C) 2009 National Technical University of Athens

This program is free software; you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation; either version 2 of the License, or
(at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.
"""

import unittest
import textwrap
import os
import sys
from cStringIO import StringIO
import tempfile

import psycopg2
from pthelma.timeseries import Timeseries
from pthelma.meteologger import *

deltacom_data = textwrap.dedent("""\
         2009-03-19T20:10 0.000000  2.413333  2.710526
         2009-03-19T20:20 0.000000  2.320000  2.578947
         2009-03-19T20:30 0.000000  2.386667  2.736842
         2009-03-19T20:40 0.000000  1.746667  2.210526
         2009-03-19T20:50 0.000000  1.680000  2.105263
         2009-03-19T21:00 0.000000  1.546667  1.947368
         2009-03-19T21:10 0.000000  1.520000  2.052632
         2009-03-19T21:20 0.000000  1.520000  1.921053
         2009-03-19T21:30 0.000000  1.386667  1.921053
         2009-03-19T21:40 0.000000  1.466667  1.973684
         2009-03-19T21:50 0.000000  1.053333  1.184211
         2009-03-19T22:00 0.000000  0.973333  1.631579
         2009-03-19T22:10 0.000000  1.746667  2.342105
         2009-03-19T22:20 0.000000  1.866667  2.815789
         2009-03-19T22:30 0.000000  1.546667  2.000000
         2009-03-19T22:40 0.000000  1.640000  1.842105
         2009-03-19T22:50 0.000000  1.693333  1.947368
         2009-03-19T23:00 0.000000  1.466667  1.710526
         2009-03-19T23:10 0.000000  1.613333  2.131579
         2009-03-19T23:20 0.000000  2.146667  2.421053
         2009-03-19T23:30 0.000000  1.586667  2.078947
         2009-03-19T23:40 0.000000  0.840000  1.500000
         2009-03-19T23:50 0.000000  1.453333  2.026316
         2009-03-20T00:00 0.000000  1.746667  2.078947
         2009-03-20T00:10 0.000000  1.120000  1.631579
         2009-03-20T00:20 0.000000  0.400000  0.421053
         2009-03-20T00:30 0.000000  0.520000  1.026316
         2009-03-20T00:40 0.000000  0.786667  1.342105
         2009-03-20T00:50 0.000000  0.733333  1.394737
         2009-03-20T01:00 0.000000  0.506667  1.026316
         2009-03-20T01:10 0.000000  0.866667  1.552632
         2009-03-20T01:20 0.000000  0.413333  0.684211
         2009-03-20T01:30 0.000000  0.400000  0.394737
         2009-03-20T01:40 0.000000  0.426667  0.763158
         2009-03-20T01:50 0.000000  0.400000  0.394737
         2009-03-20T02:00 0.000000  0.400000  0.394737
         2009-03-20T02:10 0.000000  0.400000  0.394737
         2009-03-20T02:20 0.000000  0.400000  0.394737
         2009-03-20T02:30 0.000000  0.400000  0.394737
         2009-03-20T02:40 0.000000  0.480000  0.842105
         2009-03-20T02:50 0.000000  1.066667  2.315789
         2009-03-20T03:00 0.000000  1.280000  2.947368
         2009-03-20T03:10 0.000000  1.706667  2.105263
         2009-03-20T03:20 0.000000  2.133333  3.131579
         2009-03-20T03:30 0.000000  2.093333  2.763158
         2009-03-20T03:40 0.000000  2.040000  2.842105
         2009-03-20T03:50 0.000000  1.986667  3.052632
         2009-03-20T04:00 0.000000  1.826667  2.842105
         2009-03-20T04:10 0.000000  1.573333  2.842105
         2009-03-20T04:20 0.000000  1.906667  2.921053
         2009-03-20T04:30 0.000000  1.973333  2.947368
         2009-03-20T04:40 0.000000  1.960000  3.157895
         2009-03-20T04:50 0.000000  2.053333  2.789474
         2009-03-20T05:00 0.000000  2.213333  3.078947
         2009-03-20T05:10 0.000000  1.466667  3.052632
         2009-03-20T05:20 0.000000  1.506667  3.263158
         2009-03-20T05:30 0.000000  2.266667  2.868421
         2009-03-20T05:40 0.000000  1.840000  2.578947
         2009-03-20T05:50 0.000000  1.866667  2.447368
         2009-03-20T06:00 0.000000  1.066667  2.026316
         2009-03-20T06:10 0.000000  0.586667  1.315789
         2009-03-20T06:20 0.000000  1.040000  1.500000
         2009-03-20T06:30 0.000000  0.546667  1.026316
         2009-03-20T06:40 0.000000  0.720000  2.000000
         2009-03-20T06:50 0.000000  0.853333  1.973684
         2009-03-20T07:00 0.000000  1.186667  1.710526
         2009-03-20T07:10 0.000000  2.160000  3.026316
         2009-03-20T07:20 0.000000  2.306667  3.131579
         2009-03-20T07:30 0.000000  2.280000  3.447368
         2009-03-20T07:40 0.000000  1.906667  2.815789
         2009-03-20T07:50 0.000000  2.493333  4.052632
         2009-03-20T08:00 0.000000  2.546667  4.026316
         2009-03-20T08:10 0.000000  2.773333  3.815789
         2009-03-20T08:20 0.000000  2.480000  3.842105
         2009-03-20T08:30 0.000000  2.373333  3.500000
         2009-03-20T08:40 0.000000  2.373333  3.605263
         2009-03-20T08:50 0.000000  2.746667  3.789474
         2009-03-20T09:00 0.000000  2.960000  4.078947
         2009-03-20T09:10 0.000000  2.866667  4.447368
         2009-03-20T09:20 0.000000  3.266667  4.500000
         2009-03-20T09:30 0.000000  2.360000  3.973684
         2009-03-20T09:40 0.000000  2.373333  4.789474
         2009-03-20T09:50 0.000000  3.066667  4.763158
         2009-03-20T10:00 0.000000  3.653333  5.421053
         2009-03-20T10:10 0.000000  3.600000  5.526316
         2009-03-20T10:20 0.000000  2.640000  5.052632
         2009-03-20T10:30 0.000000  3.400000  6.026316
         2009-03-20T10:40 0.000000  3.680000  5.184211
         2009-03-20T10:50 0.000000  4.013333  6.026316
         2009-03-20T11:00 0.000000  4.226667  6.631579
         2009-03-20T11:10 0.000000  2.706667  5.657895
         2009-03-20T11:20 0.000000  3.600000  5.131579
         2009-03-20T11:30 0.000000  4.693333  7.052632
         2009-03-20T11:40 0.000000  4.560000  6.078947
         2009-03-20T11:50 0.000000  4.306667  6.394737
         2009-03-20T12:00 0.000000  4.066667  6.236842
         2009-03-20T12:10 0.000000  4.133333  5.868421
         2009-03-20T12:20 0.000000  4.146667  6.394737
         2009-03-20T12:30 0.000000  4.466667  6.000000
         2009-03-20T12:40 0.000000  4.946667  7.184211
         """)

class database_test_metaclass(type):
    warning = textwrap.dedent("""\
        WARNING: Database tests not run. If you want to run the database
                 tests, set the PSYCOPG_CONNECTION environment variable
                 to "host=... dbname=... user=... password=...".
        """)
    def __new__(mcs, name, bases, dict):
        psycopg_string = os.getenv("PSYCOPG_CONNECTION")
        if not psycopg_string:
            sys.stderr.write(mcs.warning)
            return None
        return type.__new__(mcs, name, bases, dict)

class _Test_deltacom(unittest.TestCase):
    __metaclass__ = database_test_metaclass
    def setUp(self):
        # First 60 lines of test go to file1
        (fd, self.file1) = tempfile.mkstemp(text=True)
        import os
        fp = os.fdopen(fd, 'w')
        for i, line in enumerate(StringIO(deltacom_data)):
            if i>=60: break
            fp.write(line)
        fp.close()

        # All lines of test go to file2
        (fd, self.file2) = tempfile.mkstemp(text=True)
        fp = os.fdopen(fd, 'w')
        fp.write(deltacom_data)
        fp.close

        # DB connect and create two fake timeseries
        import os, psycopg2
        self.db = psycopg2.connect(os.getenv("PSYCOPG_CONNECTION"))
        c = self.db.cursor()
        c.execute('SET CONSTRAINTS ALL DEFERRED')
        c.execute('SELECT MAX(id)+1, MAX(id)+2 FROM ts_records')
        (self.timeseries_id1, self.timeseries_id2) = c.fetchone()
        c.close()

        self.datafile_fields = "0,%d,%d" % (self.timeseries_id1,
                                                    self.timeseries_id2)
        self.ts1 = Timeseries(self.timeseries_id1)
        self.ts2 = Timeseries(self.timeseries_id2)
        self.reference_ts1 = Timeseries()
        self.reference_ts2 = Timeseries()
        for i, line in enumerate(StringIO(deltacom_data)):
            items = line.split()
            self.reference_ts1[items[0]] = items[2]
            self.reference_ts2[items[0]] = items[3]
    def tearDown(self):
        self.db.rollback()
        self.db.close()
        os.unlink(self.file1)
        os.unlink(self.file2)
    def test_deltacom(self):
        logger = None
        df = Datafile_deltacom(self.db, { 'filename': self.file1,
            'datafile_fields': self.datafile_fields }, logger=logger)
        df.update_database()
        self.ts1.read_from_db(self.db)
        self.ts2.read_from_db(self.db)
        self.assertEqual(len(self.ts1), 60)
        self.assertEqual(len(self.ts2), 60)
        (items1, items2, ritems1, ritems2) = [ x.items() for x in (self.ts1,
                            self.ts2, self.reference_ts1, self.reference_ts2)]
        for i in range(0, 60):
            self.assertEqual(items1[i][0], ritems1[i][0])
            a = items1[i][1]
            b = ritems1[i][1]
            self.assertAlmostEqual(items1[i][1], ritems1[i][1], 4)
            self.assertEqual(items1[i][1].flags, ritems1[i][1].flags)
            self.assertEqual(items2[i][0], ritems2[i][0])
            self.assertAlmostEqual(items2[i][1], ritems2[i][1], 4)
            self.assertEqual(items2[i][1].flags, ritems2[i][1].flags)
        df = Datafile_deltacom(self.db, { 'filename': self.file2,
            'datafile_fields': self.datafile_fields }, logger=logger)
        df.update_database()
        self.ts1.read_from_db(self.db)
        self.ts2.read_from_db(self.db)
        self.assertEqual(len(self.ts1), 100)
        self.assertEqual(len(self.ts2), 100)
        (items1, items2, ritems1, ritems2) = [ x.items() for x in (self.ts1,
                            self.ts2, self.reference_ts1, self.reference_ts2)]
        for i in range(0, 100):
            self.assertEqual(items1[i][0], ritems1[i][0])
            self.assertAlmostEqual(items1[i][1], ritems1[i][1], 4)
            self.assertEqual(items1[i][1].flags, ritems1[i][1].flags)
            self.assertEqual(items2[i][0], ritems2[i][0])
            self.assertAlmostEqual(items2[i][1], ritems2[i][1], 4)
            self.assertEqual(items2[i][1].flags, ritems2[i][1].flags)

class _Test_pc208w(unittest.TestCase):
    def test_pc208w(self):
        sys.stderr.write('\nWARNING: No test for Deltacom_pc208w has been written yet\n')

class _Test_lastem(unittest.TestCase):
    def test_lastem(self):
        sys.stderr.write('\nWARNING: No test for Deltacom_lastem has been written yet\n')
