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
import tempfile
import cookielib
from urllib2 import build_opener, HTTPCookieProcessor, Request, HTTPError
import json
import sys
from datetime import time, datetime

from pthelma.timeseries import Timeseries
from pthelma.meteologger import Datafile, Datafile_deltacom, Datafile_simple, \
                                _parse_dst_spec, ConfigurationError, \
                                _decode_dst_dict


def full_testdata_filename(filename):
    current_directory = os.path.dirname(os.path.abspath(__file__))
    full_pathname = os.path.join(current_directory, 'data', filename)
    return full_pathname


class RequestWithMethod(Request):
    """
    See http://benjamin.smedbergs.us/blog/2008-10-21/putting-and-deleteing-in-python-urllib2/
    """
    def __init__(self, method, *args, **kwargs):
        self._method = method
        Request.__init__(self, *args, **kwargs)

    def get_method(self):
        return self._method


def connect_to_server(base_url, username, password):
    cookiejar = cookielib.CookieJar()
    opener = build_opener(HTTPCookieProcessor(cookiejar))
    opener.open(base_url + 'accounts/login/').read()
    opener.addheaders = [('X-CSRFToken', cookie.value)
                         for cookie in cookiejar if cookie.name == 'csrftoken']
    data = 'username={0}&password={1}'.format(username, password)
    opener.open(base_url + 'accounts/login/', data)
    return opener


def create_timeseries(opener, adict):
    # Create a timeseries on the server and return its id
    j = { 'gentity': adict['station_id'],
          'variable': adict['variable_id'],
          'unit_of_measurement': adict['unit_of_measurement_id'],
          'time_zone': adict['time_zone_id'],
        }
    r = Request(adict['base_url'] + 'api/Timeseries/', data=json.dumps(j),
                headers = { 'Content-type': 'application/json' })
    fp = opener.open(r)
    response_text = fp.read()
    return json.loads(response_text)['id']


def delete_timeseries(opener, base_url, ts_id):
    url = base_url + 'api/Timeseries/{0}/'.format(ts_id)
    r = RequestWithMethod('DELETE', url)
    try:
        opener.open(r)
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

def read_timeseries(opener, base_url, ts):
    r = Request(base_url + 'api/tsdata/{0}/'.format(ts.id))
    fp = opener.open(r)
    ts.read(fp)
        

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

def get_server_from_env(adict):
    try:
        v = json.loads(os.getenv("PTHELMA_TEST_METEOLOGGER"))
        for item in 'base_url username password station_id variable_id ' \
                    'unit_of_measurement_id time_zone_id'.split():
            adict[item] = v[item]
    except TypeError:
        sys.stderr.write(_connection_instructions)


class _Test_logger(unittest.TestCase):
    class_being_tested = None
    datafilename = ''
    datafiledict = {}
    ref_ts1 = Timeseries(0)
    ref_ts1.read(open(full_testdata_filename('timeseries1.txt')))
    ref_ts2 = Timeseries(0)
    ref_ts2.read(open(full_testdata_filename('timeseries2.txt')))

    def __init__(self, *args, **kwargs):
        self.base_url = None
        get_server_from_env(self.__dict__)
        return super(_Test_logger, self).__init__(*args, **kwargs)

    def setUp(self):
        if not self.class_being_tested or not self.base_url:
            return

        # First 60 nonempty lines of test go to self.file1
        (fd, self.file1) = tempfile.mkstemp(text=True)
        fp = os.fdopen(fd, 'w')
        i = 0
        for line in open(full_testdata_filename(self.datafilename)):
            if i>=60: break
            if not line.strip(): continue
            i += 1
            fp.write(line)
        fp.close()

        # Connect to server
        self.opener = connect_to_server(self.base_url, self.username,
                                        self.password)

        # Create two timeseries
        self.timeseries_id1 = create_timeseries(self.opener, self.__dict__)
        self.timeseries_id2 = create_timeseries(self.opener, self.__dict__)
        self.datafile_fields = "0,{0},{1}".format(self.timeseries_id1,
                                                  self.timeseries_id2)
        self.ts1 = Timeseries(self.timeseries_id1)
        self.ts2 = Timeseries(self.timeseries_id2)

    def tearDown(self):
        if not self.class_being_tested or not self.base_url:
            return
        delete_timeseries(self.opener, self.base_url, self.timeseries_id2)
        delete_timeseries(self.opener, self.base_url, self.timeseries_id1)

    def runTest(self):
        if not self.class_being_tested or not self.base_url:
            return
        d = { 'filename': self.file1,
              'datafile_fields': self.datafile_fields,
            }
        d.update(self.datafiledict)
        df = self.class_being_tested(self.base_url, self.opener, d)
        df.update_database()
        read_timeseries(self.opener, self.base_url, self.ts1)
        read_timeseries(self.opener, self.base_url, self.ts2)
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
        d['filename'] = full_testdata_filename(self.datafilename)
        df = self.class_being_tested(self.base_url, self.opener, d)
        df.update_database()
        read_timeseries(self.opener, self.base_url, self.ts1)
        read_timeseries(self.opener, self.base_url, self.ts2)
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


class TestDeltacom(_Test_logger):
    datafilename = 'deltacom_data.txt'
    class_being_tested = Datafile_deltacom


class TestSimple1(_Test_logger):
    datafilename = 'simple_data1.txt'
    class_being_tested = Datafile_simple
    datafiledict = { 'date_format': '%y/%m/%d %H:%M:%S', }


class TestSimple2(_Test_logger):
    datafilename = 'simple_data2.txt'
    class_being_tested = Datafile_simple
    datafiledict = { 'date_format': '%d/%m/%Y %H:%M:%S', }


class TestSimple3(_Test_logger):
    datafilename = 'simple_data3.txt'
    class_being_tested = Datafile_simple
    datafiledict = { 'date_format': '%d/%m/%Y %H:%M',
                     'nfields_to_ignore': 1,
                     'delimiter': ',' }


class TestDstUtils(unittest.TestCase):

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
        self.assertRaises(ConfigurationError, _parse_dst_spec, 'a')
        self.assertRaises(ConfigurationError, _parse_dst_spec, 
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
                              'utcoffset':  '0',
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
                              'utcoffset':  '0',
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
                              'utcoffset':  '0',
                              'filename':   'irrelevant',
                              'datafile_fields': '0',
                            })
        d, to_dst = datafile._nearest_dst_switch(datetime(2012, 11, 1))
        self.assertEqual(d, datetime(2012, 9, 30, 3, 0))
        self.assertTrue(to_dst)
        d, to_dst = datafile._nearest_dst_switch(datetime(2012, 12, 1))
        self.assertEqual(d, datetime(2013, 2, 24, 3, 0))
        self.assertFalse(to_dst)


class TestDst(unittest.TestCase):
    datafiledict = { 'date_format': '%Y-%m-%dT%H:%M',
                     'dst_starts': 'last Sunday March 03:00',
                     'dst_ends': 'last Sunday October 03:00',
                     'utcoffset': 120,
                   }

    def __init__(self, *args, **kwargs):
        self.base_url = None
        get_server_from_env(self.__dict__)
        return super(TestDst, self).__init__(*args, **kwargs)

    def setUp(self):
        self.ref_ts = Timeseries(0)
        if not self.base_url:
            return
        self.opener = connect_to_server(self.base_url, self.username,
                                        self.password)
        self.timeseries_id = create_timeseries(self.opener, self.__dict__)
        self.ts = Timeseries(self.timeseries_id)

    def tearDown(self):
        if not self.base_url:
            return
        delete_timeseries(self.opener, self.base_url, self.timeseries_id)

    def run_test(self):
        if not self.base_url:
            return
        d = { 'filename': full_testdata_filename(self.filename),
              'datafile_fields': str(self.timeseries_id),
            }
        d.update(self.datafiledict)
        df = Datafile_simple(self.base_url, self.opener, d)
        df.update_database()
        read_timeseries(self.opener, self.base_url, self.ts)
        self.assertEqual(len(self.ts), len(self.ref_ts))
        (items, ritems) = [x.items() for x in (self.ts, self.ref_ts)]
        for item, ritem in zip(items, ritems):
            self.assertEqual(item[0], ritem[0])
            self.assertAlmostEqual(item[1], ritem[1], 4)
            self.assertEqual(item[1].flags, ritem[1].flags)

    def test_to_dst(self):
        self.filename = 'data_at_change_to_dst.txt'
        self.ref_ts.read(open(full_testdata_filename(
            'timeseries_at_change_to_dst.txt')))
        self.run_test()

    def test_from_dst(self):
        self.filename = 'data_at_change_from_dst.txt'
        self.ref_ts.read(open(full_testdata_filename(
            'timeseries_at_change_from_dst.txt')))
        self.run_test()
