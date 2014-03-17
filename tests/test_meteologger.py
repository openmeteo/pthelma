#!/usr/bin/python
"""
Tests for meteologger.

Copyright (C) 2009-2013 National Technical University of Athens
Copyright (C) 2013 TEI of Epirus

This program is free software; you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation; either version 2 of the License, or
(at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

In order to run the meteologger tests, you must specify the
PTHELMA_TEST_METEOLOGGER variable to contain a json-formatted string of
parameters, like this:

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

import cookielib
import json
from math import isnan
import os
import tempfile
from unittest import TestCase, skipUnless
from urllib2 import build_opener, HTTPCookieProcessor, Request, HTTPError

from pthelma.meteologger import Datafile_deltacom, Datafile_simple, \
    Datafile_wdat5, ConfigurationError
from pthelma.timeseries import Timeseries


def full_testdata_filename(filename):
    current_directory = os.path.dirname(os.path.abspath(__file__))
    full_pathname = os.path.join(current_directory, 'data', filename)
    return full_pathname


class RequestWithMethod(Request):
    """
    See http://benjamin.smedbergs.us/blog/2008-10-21/putting-and-deleteing
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
    opener.addheaders = [('X-CSRFToken', cookie.value)
                         for cookie in cookiejar if cookie.name == 'csrftoken']
    return opener


def create_timeseries(opener, adict):
    # Create a timeseries on the server and return its id
    j = {'gentity': adict['station_id'],
         'variable': adict['variable_id'],
         'unit_of_measurement': adict['unit_of_measurement_id'],
         'time_zone': adict['time_zone_id'], }
    r = Request(adict['base_url'] + 'api/Timeseries/', data=json.dumps(j),
                headers={'Content-type': 'application/json'})
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


def get_server_from_env(adict):
    conn = os.getenv("PTHELMA_TEST_METEOLOGGER")
    v = json.loads(conn)
    for item in 'base_url username password station_id variable_id ' \
                'unit_of_measurement_id time_zone_id'.split():
        adict[item] = v[item]


@skipUnless(os.getenv('PTHELMA_TEST_METEOLOGGER'),
            "set PTHELMA_TEST_METEOLOGGER")
class _Test_logger(TestCase):
    class_being_tested = None
    datafilename = ''
    datafiledict = {}
    ref_ts1 = Timeseries(0)
    ref_ts1.read(open(full_testdata_filename('timeseries1.txt')))
    ref_ts2 = Timeseries(0)
    ref_ts2.read(open(full_testdata_filename('timeseries2.txt')))

    def setUp(self):
        get_server_from_env(self.__dict__)

        if not self.class_being_tested or not self.base_url:
            return

        # First 60 nonempty lines of test go to self.file1
        (fd, self.file1) = tempfile.mkstemp(text=True)
        fp = os.fdopen(fd, 'w')
        i = 0
        for line in open(full_testdata_filename(self.datafilename)):
            if i >= 60:
                break
            if not line.strip():
                continue
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

    def check_config_test(self):
        self.assertRaises(ConfigurationError, self.class_being_tested,
                          self.base_url, self.opener, {})
        self.assertRaises(ConfigurationError, self.class_being_tested,
                          self.base_url, self.opener,
                          {'filename': 'hello', 'datafile_fields': '0',
                           'datafile_format': 'irrelevant',
                           'nonexistent_config_option': True})
        # Call it correctly and expect it doesn't raise anything
        self.class_being_tested(self.base_url, self.opener,
                                {'filename': 'hello', 'datafile_fields': '0',
                                 'datafile_format': 'irrelevant'})

    def upload_test(self):
        d = {'filename': self.file1,
             'datafile_fields': self.datafile_fields,
             'datafile_format': 'irrelevant'}
        d.update(self.datafiledict)
        df = self.class_being_tested(self.base_url, self.opener, d)
        df.update_database()
        read_timeseries(self.opener, self.base_url, self.ts1)
        read_timeseries(self.opener, self.base_url, self.ts2)
        self.assertEqual(len(self.ts1), 60)
        self.assertEqual(len(self.ts2), 60)
        (items1, items2, ritems1, ritems2) = [
            x.items() for x in (self.ts1, self.ts2,
                                self.ref_ts1, self.ref_ts2)]
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
        (items1, items2, ritems1, ritems2) = [
            x.items() for x in (self.ts1, self.ts2,
                                self.ref_ts1, self.ref_ts2)]
        for i in range(0, 100):
            self.assertEqual(items1[i][0], ritems1[i][0])
            self.assertAlmostEqual(items1[i][1], ritems1[i][1], 4)
            self.assertEqual(items1[i][1].flags, ritems1[i][1].flags)
            self.assertEqual(items2[i][0], ritems2[i][0])
            self.assertAlmostEqual(items2[i][1], ritems2[i][1], 4)
            self.assertEqual(items2[i][1].flags, ritems2[i][1].flags)

    def runTest(self):
        if not self.class_being_tested or not self.base_url:
            return
        self.check_config_test()
        self.upload_test()


class TestDeltacom(_Test_logger):
    datafilename = 'deltacom_data.txt'
    class_being_tested = Datafile_deltacom


class TestSimple1(_Test_logger):
    datafilename = 'simple_data1.txt'
    class_being_tested = Datafile_simple
    datafiledict = {'date_format': '%y/%m/%d %H:%M:%S'}


class TestSimple2(_Test_logger):
    datafilename = 'simple_data2.txt'
    class_being_tested = Datafile_simple
    datafiledict = {'date_format': '%d/%m/%Y %H:%M:%S'}


class TestSimple3(_Test_logger):
    datafilename = 'simple_data3.txt'
    class_being_tested = Datafile_simple
    datafiledict = {'date_format': '%d/%m/%Y %H:%M',
                    'nfields_to_ignore': 1,
                    'delimiter': ','}


@skipUnless(os.getenv('PTHELMA_TEST_METEOLOGGER'),
            "set PTHELMA_TEST_METEOLOGGER")
class TestDst(TestCase):
    datafiledict = {'date_format': '%Y-%m-%dT%H:%M',
                    'timezone': 'Europe/Athens'}

    def setUp(self):
        get_server_from_env(self.__dict__)
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
        d = {'filename': full_testdata_filename(self.filename),
             'datafile_fields': str(self.timeseries_id),
             'datafile_format': 'irrelevant'}
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

    @skipUnless(os.getenv('PTHELMA_TEST_METEOLOGGER'), "see above")
    def test_to_dst(self):
        self.filename = 'data_at_change_to_dst.txt'
        self.ref_ts.read(open(full_testdata_filename(
            'timeseries_at_change_to_dst.txt')))
        self.run_test()

    @skipUnless(os.getenv('PTHELMA_TEST_METEOLOGGER'), "see above")
    def test_from_dst(self):
        self.filename = 'data_at_change_from_dst.txt'
        self.ref_ts.read(open(full_testdata_filename(
            'timeseries_at_change_from_dst.txt')))
        self.run_test()


@skipUnless(os.getenv('PTHELMA_TEST_METEOLOGGER'),
            "set PTHELMA_TEST_METEOLOGGER")
class TestWdat5(_Test_logger):
    class_being_tested = Datafile_wdat5
    longMessage = True
    # The dicts below hold the parameter name as it is in the WeatherLink
    # README file, and the corresponding heading in the WeatherLink export file
    # (lowercase, after changing spaces to hyphens and removing dots), empty
    # string for those that aren't going to be tested.
    parameters = [
        {'name': 'outsideTemp', 'expname': 'temp-out'},
        {'name': 'hiOutsideTemp', 'expname': 'hi-temp'},
        {'name': 'lowOutsideTemp', 'expname': 'low-temp'},
        {'name': 'insideTemp', 'expname': 'in-temp'},
        {'name': 'barometer', 'expname': 'bar'},
        {'name': 'outsideHum', 'expname': 'out-hum'},
        {'name': 'insideHum', 'expname': 'in-hum'},
        {'name': 'rain', 'expname': 'rain'},
        {'name': 'hiRainRate', 'expname': 'rain-rate'},
        {'name': 'windSpeed', 'expname': 'wind-speed'},
        {'name': 'hiWindSpeed', 'expname': 'hi-speed'},
        {'name': 'windDirection', 'expname': 'wind-dir'},
        {'name': 'hiWindDirection', 'expname': 'hi-dir'},
        {'name': 'numWindSamples', 'expname': 'wind-samp'},
        {'name': 'solarRad', 'expname': 'solar-rad'},
        {'name': 'hiSolarRad', 'expname': 'hi-solar-rad'},
        {'name': 'UV', 'expname': 'uv-index'},
        {'name': 'hiUV', 'expname': 'hi-uv'},
        {'name': 'leafTemp1', 'expname': ''},
        {'name': 'leafTemp2', 'expname': ''},
        {'name': 'leafTemp3', 'expname': ''},
        {'name': 'leafTemp4', 'expname': ''},
        {'name': 'extraRad', 'expname': ''},
        {'name': 'newSensors1', 'expname': ''},
        {'name': 'newSensors2', 'expname': ''},
        {'name': 'newSensors3', 'expname': ''},
        {'name': 'newSensors4', 'expname': ''},
        {'name': 'newSensors5', 'expname': ''},
        {'name': 'newSensors6', 'expname': ''},
        {'name': 'forecast', 'expname': ''},
        {'name': 'ET', 'expname': 'et'},
        {'name': 'soilTemp1', 'expname': ''},
        {'name': 'soilTemp2', 'expname': ''},
        {'name': 'soilTemp3', 'expname': ''},
        {'name': 'soilTemp4', 'expname': ''},
        {'name': 'soilTemp5', 'expname': ''},
        {'name': 'soilTemp6', 'expname': ''},
        {'name': 'soilMoisture1', 'expname': ''},
        {'name': 'soilMoisture2', 'expname': ''},
        {'name': 'soilMoisture3', 'expname': ''},
        {'name': 'soilMoisture4', 'expname': ''},
        {'name': 'soilMoisture5', 'expname': ''},
        {'name': 'soilMoisture6', 'expname': ''},
        {'name': 'leafWetness1', 'expname': ''},
        {'name': 'leafWetness2', 'expname': ''},
        {'name': 'leafWetness3', 'expname': ''},
        {'name': 'leafWetness4', 'expname': ''},
        {'name': 'extraTemp1', 'expname': ''},
        {'name': 'extraTemp2', 'expname': ''},
        {'name': 'extraTemp3', 'expname': ''},
        {'name': 'extraTemp4', 'expname': ''},
        {'name': 'extraTemp5', 'expname': ''},
        {'name': 'extraTemp6', 'expname': ''},
        {'name': 'extraTemp7', 'expname': ''},
        {'name': 'extraHum1', 'expname': ''},
        {'name': 'extraHum2', 'expname': ''},
        {'name': 'extraHum3', 'expname': ''},
        {'name': 'extraHum4', 'expname': ''},
        {'name': 'extraHum5', 'expname': ''},
        {'name': 'extraHum6', 'expname': ''},
        {'name': 'extraHum7', 'expname': ''},
    ]

    def setUp(self):
        get_server_from_env(self.__dict__)

        # Connect to server
        self.opener = connect_to_server(self.base_url, self.username,
                                        self.password)

        # Create as many timeseries as there are not-to-ignore parameters
        for parm in self.parameters:
            parm['ts_id'] = create_timeseries(self.opener, self.__dict__
                                              ) if parm['expname'] else 0

    def tearDown(self):
        for parm in self.parameters:
            if parm['ts_id']:
                delete_timeseries(self.opener, self.base_url, parm['ts_id'])

    def check_config_test(self):
        self.assertRaises(ConfigurationError, self.class_being_tested,
                          self.base_url, self.opener, {})
        self.assertRaises(ConfigurationError, self.class_being_tested,
                          self.base_url, self.opener,
                          {'filename': 'hello', 'outsidetemp': '0',
                           'datafile_format': 'irrelevant',
                           'nonexistent_config_option': True})
        # Call it correctly and expect it doesn't raise anything
        self.class_being_tested(self.base_url, self.opener,
                                {'filename': 'hello', 'outsidetemp': '0',
                                 'datafile_format': 'irrelevant'})

    def upload_test(self):
        d = {'filename': full_testdata_filename('wdat5/1'),
             'datafile_format': 'irrelevant'}
        for parm in self.parameters:
            if parm['ts_id']:
                d[parm['name'].lower()] = parm['ts_id']
        df = Datafile_wdat5(self.base_url, self.opener, d)
        df.update_database()
        self.check(d['filename'])
        d['filename'] = full_testdata_filename('wdat5/2')
        df = Datafile_wdat5(self.base_url, self.opener, d)
        df.update_database()
        self.check(d['filename'])

    def check(self, datadir):
        for parm in self.parameters:
            if not parm['ts_id']:
                continue
            actual_ts = Timeseries(parm['ts_id'])
            read_timeseries(self.opener, self.base_url, actual_ts)
            reference_ts = Timeseries()
            with open(os.path.join(
                    datadir, 'generated', parm['expname'] + '.txt')) as f:
                reference_ts.read(f)
                precision = self.guess_precision(f)
            self.assertTimeseriesEqual(actual_ts, reference_ts, precision,
                                       parm['expname'] + '.txt')

    def guess_precision(self, f):
        result = 0
        f.seek(0)
        # Take a sample of 200 rows
        for i, line in enumerate(f):
            if i >= 200:
                break
            value = line.split(',')[1].strip()
            integral, sep, decimal = value.partition('.')
            result = len(decimal) if len(decimal) > result else result
        return result

    def assertTimeseriesEqual(self, ts1, ts2, precision, filename):
        self.assertEqual(len(ts1), len(ts2))
        items1 = ts1.items()
        items2 = ts2.items()
        for i, (item1, item2) in enumerate(zip(items1, items2)):
            self.assertEqual(item1[0], item2[0])
            if isnan(item1[1]):
                self.assertTrue(isnan(item2[1]),
                                msg='{1}, row {0}'.format(i + 1, filename))
            else:
                self.assertAlmostEqual(
                    item1[1], item2[1], places=precision,
                    msg='{1}, row {0}'.format(i + 1, filename))
            self.assertEqual(item1[1].flags, item2[1].flags)

    def assertAlmostEqual(self, a, b, places=7, msg=None):
        """We redefine assertAlmostEqual so that, e.g. with places=1, 0.55 is
        considered equal to both 0.5 and 0.6
        """
        tolerance = 10 ** (-places - 3)
        if abs(a - b) <= 0.5 * 10 ** (-places) + tolerance:
            return
        super(TestWdat5, self).assertAlmostEqual(a, b, places=places, msg=msg)
