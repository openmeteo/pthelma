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
import os
from cStringIO import StringIO
import tempfile
import cookielib
from urllib2 import build_opener, HTTPCookieProcessor, Request, HTTPError
import json
import sys
from datetime import time, datetime

from pthelma.timeseries import Timeseries
from pthelma.meteologger import Datafile, Datafile_deltacom, Datafile_simple, \
                                _parse_dst_spec, DSTSpecificationParseError, \
                                _decode_dst_dict


def get_data(filename):
    current_directory = os.path.dirname(os.path.abspath(__file__))
    full_pathname = os.path.join(current_directory, 'data', filename)
    return open(full_pathname).read()


class RequestWithMethod(Request):
    """
    See http://benjamin.smedbergs.us/blog/2008-10-21/putting-and-deleteing-in-python-urllib2/
    """
    def __init__(self, method, *args, **kwargs):
        self._method = method
        Request.__init__(self, *args, **kwargs)

    def get_method(self):
        return self._method


_connection_instructions = """
Omitting the tests for meteologger; in order to run these tests, you
must specify the PTHELMA_TEST_METEOLOGGER variable to contain a
json-formatted string of parameters, like this (but it may be in one
line):

    { "base_url": "http://localhost:8001/",
      "username": "admin",
      "password": "secret",
      "station_id": 1334,
      "variable_id": 1,
      "unit_of_measurement_id": 1,
      "time_zone_id": 1 }

The first three parameters are for connecting to an appropriate
database. Don't use a production database for that; although things
are normally cleaned up (e.g. test timeseries created are deleted), id
serial numbers will be affected and things might not be cleaned up if
there is an error.

The rest of the parameters are used when test timeseries are created.
"""

class _Test_logger(unittest.TestCase):
    class_being_tested = None
    testdata = None
    datafiledict = {}
    ref_ts1 = Timeseries(0)
    ref_ts1.read(get_data('timeseries1.txt'))
    ref_ts2 = Timeseries(0)
    ref_ts2.read(get_data('timeseries2.txt'))
    base_url = None
    try:
        __v = json.loads(os.getenv("PTHELMA_TEST_METEOLOGGER"))
        base_url = __v['base_url']
        username = __v['username']
        password = __v['password']
        station_id = __v['station_id']
        variable_id = __v['variable_id']
        unit_of_measurement_id = __v['unit_of_measurement_id']
        time_zone_id = __v['time_zone_id']
    except TypeError:
        sys.stderr.write(_connection_instructions)

    def setUp(self):

        if not self.class_being_tested or not self.base_url:
            return

        # First 60 nonempty lines of test go to self.file1
        (fd, self.file1) = tempfile.mkstemp(text=True)
        fp = os.fdopen(fd, 'w')
        i = 0
        for line in StringIO(self.testdata):
            if i>=60: break
            if not line.strip(): continue
            i += 1
            fp.write(line)
        fp.close()

        # All lines of test go to self.file2
        (fd, self.file2) = tempfile.mkstemp(text=True)
        fp = os.fdopen(fd, 'w')
        fp.write(self.testdata)
        fp.close

        # Connect to server
        cookiejar = cookielib.CookieJar()
        self.opener = build_opener(HTTPCookieProcessor(cookiejar))
        self.opener.open(self.base_url + 'accounts/login/').read()
        self.opener.addheaders = [('X-CSRFToken', cookie.value)
                                  for cookie in cookiejar
                                  if cookie.name == 'csrftoken']
        data = 'username={0}&password={1}'.format(self.username, self.password)
        self.opener.open(self.base_url + 'accounts/login/', data)

        # Create two timeseries
        self.timeseries_id1 = self._create_timeseries()
        self.timeseries_id2 = self._create_timeseries()
        self.datafile_fields = "0,{0},{1}".format(self.timeseries_id1,
                                                  self.timeseries_id2)
        self.ts1 = Timeseries(self.timeseries_id1)
        self.ts2 = Timeseries(self.timeseries_id2)

    def tearDown(self):
        if not self.class_being_tested or not self.base_url:
            return
        self._delete_timeseries(self.timeseries_id2)
        self._delete_timeseries(self.timeseries_id1)

    def _create_timeseries(self):
        # Create a timeseries on the server and return its id
        j = { 'gentity': self.station_id,
              'variable': self.variable_id,
              'unit_of_measurement': self.unit_of_measurement_id,
              'time_zone': self.time_zone_id,
            }
        r = Request(self.base_url + 'api/Timeseries/', data=json.dumps(j),
                    headers = { 'Content-type': 'application/json' })
        fp = self.opener.open(r)
        response_text = fp.read()
        return json.loads(response_text)['id']

    def _delete_timeseries(self, ts_id):
        url = self.base_url + 'api/Timeseries/{0}/'.format(ts_id)
        r = RequestWithMethod('DELETE', url)
        try:
            self.opener.open(r)
            # According to the theory at
            # http://stackoverflow.com/questions/7032890/ and elsewhere,
            # we shouldn't reach this point; in practice, however, I see
            # that a 204 response results in coming here, not in raising an
            # exception (and with no way to check the status code). I assume
            # that if we come here everything was OK.
        except HTTPError as e:
            # But just to be sure, also assume that a 204 response might
            # lead us here as well.
            if e.code != 204:
                raise

    def _read_timeseries(self, ts):
        r = Request(self.base_url + 'api/tsdata/{0}/'.format(ts.id))
        fp = self.opener.open(r)
        ts.read(fp)
        
    def runTest(self):
        if not self.class_being_tested or not self.base_url:
            return
        d = { 'filename': self.file1,
              'datafile_fields': self.datafile_fields,
            }
        d.update(self.datafiledict)
        df = self.class_being_tested(self.base_url, self.opener, d)
        df.update_database()
        self._read_timeseries(self.ts1)
        self._read_timeseries(self.ts2)
        self.assertEqual(len(self.ts1), 60)
        self.assertEqual(len(self.ts2), 60)
        (items1, items2, ritems1, ritems2) = [ x.items() for x in (self.ts1,
                                        self.ts2, self.ref_ts1, self.ref_ts2)]
        for i in range(0, 60):
            self.assertEqual(items1[i][0], ritems1[i][0])
            self.assertAlmostEqual(items1[i][1], ritems1[i][1], 4)
            self.assertEqual(items1[i][1].flags, ritems1[i][1].flags)
            self.assertEqual(items2[i][0], ritems2[i][0])
            self.assertAlmostEqual(items2[i][1], ritems2[i][1], 4)
            self.assertEqual(items2[i][1].flags, ritems2[i][1].flags)
        d['filename'] = self.file2
        df = self.class_being_tested(self.base_url, self.opener, d)
        df.update_database()
        self._read_timeseries(self.ts1)
        self._read_timeseries(self.ts2)
        self.assertEqual(len(self.ts1), 100)
        self.assertEqual(len(self.ts2), 100)
        (items1, items2, ritems1, ritems2) = [ x.items() for x in (self.ts1,
                                       self.ts2, self.ref_ts1, self.ref_ts2)]
        for i in range(0, 100):
            self.assertEqual(items1[i][0], ritems1[i][0])
            self.assertAlmostEqual(items1[i][1], ritems1[i][1], 4)
            self.assertEqual(items1[i][1].flags, ritems1[i][1].flags)
            self.assertEqual(items2[i][0], ritems2[i][0])
            self.assertAlmostEqual(items2[i][1], ritems2[i][1], 4)
            self.assertEqual(items2[i][1].flags, ritems2[i][1].flags)


class _Test_deltacom(_Test_logger):
    testdata = get_data('deltacom_data.txt')
    class_being_tested = Datafile_deltacom


class _Test_simple1(_Test_logger):
    testdata = get_data('simple_data1.txt')
    class_being_tested = Datafile_simple
    datafiledict = { 'date_format': '%y/%m/%d %H:%M:%S', }


class _Test_simple2(_Test_logger):
    testdata = get_data('simple_data2.txt')
    class_being_tested = Datafile_simple
    datafiledict = { 'date_format': '%d/%m/%Y %H:%M:%S', }


class _Test_simple3(_Test_logger):
    testdata = get_data('simple_data3.txt')
    class_being_tested = Datafile_simple
    datafiledict = { 'date_format': '%d/%m/%Y %H:%M',
                     'nfields_to_ignore': 1,
                     'delimiter': ',' }


class _Test_dst(unittest.TestCase):

    def test_parse_dst_spec(self):
        self.assertEqual(_parse_dst_spec('first Monday January 03:00'), 
                    { 'nth': 1, 'dow': 1, 'month': 1, 'time': time(3, 0) })
        self.assertEqual(_parse_dst_spec('second Tuesday February 03:00'), 
                    { 'nth': 2, 'dow': 2, 'month': 2, 'time': time(3, 0) })
        self.assertEqual(_parse_dst_spec('third Thursday May 03:00'), 
                    { 'nth': 3, 'dow': 4, 'month': 5, 'time': time(3, 0) })
        self.assertEqual(_parse_dst_spec('fourth Friday June 03:00'), 
                    { 'nth': 4, 'dow': 5, 'month': 6, 'time': time(3, 0) })
        self.assertEqual(_parse_dst_spec('last Saturday July 03:00'), 
                    { 'nth': -1, 'dow': 6, 'month': 7, 'time': time(3, 0) })
        self.assertEqual(_parse_dst_spec('03-22 03:00'),
                    { 'month': 3, 'dom': 22, 'time': time(3, 0) })
        self.assertEqual(_parse_dst_spec(''), {})
        self.assertRaises(DSTSpecificationParseError, _parse_dst_spec, 'a')
        self.assertRaises(DSTSpecificationParseError, _parse_dst_spec, 
                          'fifth Saturday July 03:00')

    def test_decode_dst_dict(self):
        dct = _parse_dst_spec('first Monday April 03:00')
        dec = _decode_dst_dict(dct, 2013)
        self.assertEqual(dec, datetime(2013, 4, 1, 3, 0))

        dct = _parse_dst_spec('first Sunday April 03:00')
        dec = _decode_dst_dict(dct, 2013)
        self.assertEqual(dec, datetime(2013, 4, 7, 3, 0))

        dct = _parse_dst_spec('second Monday April 03:00')
        dec = _decode_dst_dict(dct, 2013)
        self.assertEqual(dec, datetime(2013, 4, 8, 3, 0))

        dct = _parse_dst_spec('second Sunday April 03:00')
        dec = _decode_dst_dict(dct, 2013)
        self.assertEqual(dec, datetime(2013, 4, 14, 3, 0))

        dct = _parse_dst_spec('second Tuesday February 03:00')
        dec = _decode_dst_dict(dct, 2013)
        self.assertEqual(dec, datetime(2013, 2, 12, 3, 0))

        dct = _parse_dst_spec('third Thursday May 03:00')
        dec = _decode_dst_dict(dct, 2013)
        self.assertEqual(dec, datetime(2013, 5, 16, 3, 0))

        dct = _parse_dst_spec('fourth Friday June 03:00')
        dec = _decode_dst_dict(dct, 2013)
        self.assertEqual(dec, datetime(2013, 6, 28, 3, 0))

        dct = _parse_dst_spec('last Saturday July 03:00')
        dec = _decode_dst_dict(dct, 2013)
        self.assertEqual(dec, datetime(2013, 7, 27, 3, 0))

        dct = _parse_dst_spec('last Sunday March 03:00')
        dec = _decode_dst_dict(dct, 2013)
        self.assertEqual(dec, datetime(2013, 3, 31, 3, 0))

        dct = _parse_dst_spec('last Monday March 03:00')
        dec = _decode_dst_dict(dct, 2013)
        self.assertEqual(dec, datetime(2013, 3, 25, 3, 0))

        dct = _parse_dst_spec('last Monday December 03:00')
        dec = _decode_dst_dict(dct, 2012)
        self.assertEqual(dec, datetime(2012, 12, 31, 3, 0))

        dct = _parse_dst_spec('last Sunday December 03:00')
        dec = _decode_dst_dict(dct, 2012)
        self.assertEqual(dec, datetime(2012, 12, 30, 3, 0))

    def test_nearest_dst_switch(self):
        datafile = Datafile('http://irrelevant', None, 
                            { 'dst_starts': 'last Sunday April 03:00',
                              'dst_ends':   'last Sunday November 03:00',
                              'filename':   'irrelevant',
                              'datafile_fields': '0',
                            })
        d, to_dst = datafile._nearest_dst_switch(datetime(2013, 1, 1))
        self.assertEqual(d, datetime(2012, 11, 25, 3, 0))
        self.assertFalse(to_dst)
        d, to_dst = datafile._nearest_dst_switch(datetime(2013, 3, 1))
        self.assertEqual(d, datetime(2013, 4, 28, 3, 0))
        self.assertTrue(to_dst)

        datafile = Datafile('http://irrelevant', None, 
                            { 'dst_starts': 'last Sunday February 03:00',
                              'dst_ends':   'last Sunday September 03:00',
                              'filename':   'irrelevant',
                              'datafile_fields': '0',
                            })
        d, to_dst = datafile._nearest_dst_switch(datetime(2013, 1, 1))
        self.assertEqual(d, datetime(2013, 2, 24, 3, 0))
        self.assertTrue(to_dst)
        d, to_dst = datafile._nearest_dst_switch(datetime(2012, 12, 1))
        self.assertEqual(d, datetime(2013, 2, 24, 3, 0))
        self.assertTrue(to_dst)

        datafile = Datafile('http://irrelevant', None, 
                            { 'dst_starts': 'last Sunday September 03:00',
                              'dst_ends':   'last Sunday February 03:00',
                              'filename':   'irrelevant',
                              'datafile_fields': '0',
                            })
        d, to_dst = datafile._nearest_dst_switch(datetime(2012, 11, 1))
        self.assertEqual(d, datetime(2012, 9, 30, 3, 0))
        self.assertTrue(to_dst)
        d, to_dst = datafile._nearest_dst_switch(datetime(2012, 12, 1))
        self.assertEqual(d, datetime(2013, 2, 24, 3, 0))
        self.assertFalse(to_dst)
