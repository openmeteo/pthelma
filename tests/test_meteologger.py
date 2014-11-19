"""
In order to run the meteologger tests, you must specify the
PTHELMA_TEST_ENHYDRIS_API environment variable as explained in
test_enhydris_api.py.
"""

from datetime import datetime
import json
from math import isnan
import os
import shutil
import sys
import tempfile
import textwrap
from unittest import TestCase, skipIf, skipUnless

from six import StringIO
from six.moves.configparser import NoOptionError

import pytz

from pthelma import enhydris_api
from pthelma.cliapp import WrongValueError, InvalidOptionError
from pthelma.meteologger import Datafile_deltacom, Datafile_simple, \
    Datafile_wdat5, Datafile_odbc, ConfigurationError, LoggertodbApp
from pthelma.timeseries import Timeseries


def full_testdata_filename(filename):
    current_directory = os.path.dirname(os.path.abspath(__file__))
    full_pathname = os.path.join(current_directory, 'data', filename)
    return full_pathname


def create_timeseries(cookies, adict):
    # Create a timeseries on the server and return its id
    j = {'gentity': adict['station_id'],
         'variable': adict['variable_id'],
         'unit_of_measurement': adict['unit_of_measurement_id'],
         'time_zone': adict['time_zone_id'], }
    return enhydris_api.post_model(adict['base_url'], cookies, 'Timeseries', j)


def get_server_from_env(adict):
    conn = os.getenv("PTHELMA_TEST_ENHYDRIS_API")
    v = json.loads(conn)
    for item in 'base_url user password station_id variable_id ' \
                'unit_of_measurement_id time_zone_id'.split():
        adict[item] = v[item]


@skipUnless(os.getenv('PTHELMA_TEST_ENHYDRIS_API'),
            "set PTHELMA_TEST_ENHYDRIS_API")
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
        with open(full_testdata_filename(self.datafilename)) as f:
            for line in f:
                if i >= 60:
                    break
                if not line.strip():
                    continue
                i += 1
                fp.write(line)
        fp.close()

        # Login
        self.cookies = enhydris_api.login(self.base_url,
                                          self.user,
                                          self.password)

        # Create two timeseries
        self.timeseries_id1 = create_timeseries(self.cookies, self.__dict__)
        self.timeseries_id2 = create_timeseries(self.cookies, self.__dict__)
        self.datafile_fields = "0,{0},{1}".format(self.timeseries_id1,
                                                  self.timeseries_id2)
        self.ts1 = Timeseries(self.timeseries_id1)
        self.ts2 = Timeseries(self.timeseries_id2)

    def tearDown(self):
        if not self.class_being_tested or not self.base_url:
            return
        enhydris_api.delete_model(self.base_url, self.cookies,
                                  'Timeseries', self.timeseries_id2)
        enhydris_api.delete_model(self.base_url, self.cookies,
                                  'Timeseries', self.timeseries_id1)

    def check_config_test(self):
        self.assertRaises(ConfigurationError, self.class_being_tested,
                          self.base_url, self.cookies, {})
        self.assertRaises(ConfigurationError, self.class_being_tested,
                          self.base_url, self.cookies,
                          {'filename': 'hello', 'datafile_fields': '0',
                           'datafile_format': 'irrelevant',
                           'nonexistent_config_option': True})
        # Call it correctly and expect it doesn't raise anything
        self.class_being_tested(self.base_url, self.cookies,
                                {'filename': 'hello', 'datafile_fields': '0',
                                 'datafile_format': 'irrelevant'})

    def upload_test(self):
        d = {'filename': self.file1,
             'datafile_fields': self.datafile_fields,
             'datafile_format': 'irrelevant'}
        d.update(self.datafiledict)
        df = self.class_being_tested(self.base_url, self.cookies, d)
        df.update_database()
        enhydris_api.read_tsdata(self.base_url, self.cookies, self.ts1)
        enhydris_api.read_tsdata(self.base_url, self.cookies, self.ts2)
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
        df = self.class_being_tested(self.base_url, self.cookies, d)
        df.update_database()
        enhydris_api.read_tsdata(self.base_url, self.cookies, self.ts1)
        enhydris_api.read_tsdata(self.base_url, self.cookies, self.ts2)
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


@skipUnless(os.getenv('PTHELMA_TEST_ENHYDRIS_API'),
            "set PTHELMA_TEST_ENHYDRIS_API")
class TestDst(TestCase):
    datafiledict = {'date_format': '%Y-%m-%dT%H:%M',
                    'timezone': 'Europe/Athens'}

    def setUp(self):
        get_server_from_env(self.__dict__)
        self.ref_ts = Timeseries(0)
        if not self.base_url:
            return
        self.cookies = enhydris_api.login(self.base_url, self.user,
                                          self.password)
        self.timeseries_id = create_timeseries(self.cookies, self.__dict__)
        self.ts = Timeseries(self.timeseries_id)

    def tearDown(self):
        if not self.base_url:
            return
        enhydris_api.delete_model(self.base_url, self.cookies,
                                  'Timeseries', self.timeseries_id)

    def run_test(self):
        if not self.base_url:
            return
        d = {'filename': full_testdata_filename(self.filename),
             'datafile_fields': str(self.timeseries_id),
             'datafile_format': 'irrelevant'}
        d.update(self.datafiledict)
        df = Datafile_simple(self.base_url, self.cookies, d)
        df.update_database()
        enhydris_api.read_tsdata(self.base_url, self.cookies, self.ts)
        self.assertEqual(len(self.ts), len(self.ref_ts))
        (items, ritems) = [x.items() for x in (self.ts, self.ref_ts)]
        for item, ritem in zip(items, ritems):
            self.assertEqual(item[0], ritem[0])
            self.assertAlmostEqual(item[1], ritem[1], 4)
            self.assertEqual(item[1].flags, ritem[1].flags)

    @skipUnless(os.getenv('PTHELMA_TEST_ENHYDRIS_API'), "see above")
    def test_to_dst(self):
        self.filename = 'data_at_change_to_dst.txt'
        with open(full_testdata_filename('timeseries_at_change_to_dst.txt')
                  ) as f:
            self.ref_ts.read(f)
        self.run_test()

    @skipUnless(os.getenv('PTHELMA_TEST_ENHYDRIS_API'), "see above")
    def test_from_dst(self):
        self.filename = 'data_at_change_from_dst.txt'
        with open(full_testdata_filename('timeseries_at_change_from_dst.txt')
                  ) as f:
            self.ref_ts.read(f)
        self.run_test()

    def test_fix_dst(self):
        d = {'filename': 'irrelevant',
             'datafile_fields': '0',
             'datafile_format': 'irrelevant'}
        d.update(self.datafiledict)
        df = Datafile_simple('http://irrelevant/', {}, d)
        self.assertEqual(df._fix_dst(datetime(2012, 10, 28, 2, 59)),
                         datetime(2012, 10, 28, 1, 59))
        self.assertEqual(df._fix_dst(datetime(2012, 10, 28, 3, 00)),
                         datetime(2012, 10, 28, 3, 00))
        self.assertEqual(df._fix_dst(datetime(2012, 10, 28, 4, 00)),
                         datetime(2012, 10, 28, 4, 00))

        # Now we pretend that the switch from dst hasn't occurred yet.
        # This is the only case when loggertodb should assume that
        # ambiguous times refer to before the switch.
        athens = pytz.timezone('Europe/Athens')
        now = athens.localize(datetime(2012, 10, 28, 3, 59), is_dst=True)
        self.assertEqual(df._fix_dst(datetime(2012, 10, 28, 2, 59), now=now),
                         datetime(2012, 10, 28, 1, 59))
        self.assertEqual(df._fix_dst(datetime(2012, 10, 28, 3, 00), now=now),
                         datetime(2012, 10, 28, 2, 00))
        self.assertEqual(df._fix_dst(datetime(2012, 10, 28, 4, 00), now=now),
                         datetime(2012, 10, 28, 4, 00))

        # Once more; the switch from DST has just occurred; now it
        # should be assumed that ambiguous times refer to after the
        # switch.
        now = athens.localize(datetime(2012, 10, 28, 3, 0), is_dst=False)
        self.assertEqual(df._fix_dst(datetime(2012, 10, 28, 2, 59), now=now),
                         datetime(2012, 10, 28, 1, 59))
        self.assertEqual(df._fix_dst(datetime(2012, 10, 28, 3, 00), now=now),
                         datetime(2012, 10, 28, 3, 00))
        self.assertEqual(df._fix_dst(datetime(2012, 10, 28, 4, 00), now=now),
                         datetime(2012, 10, 28, 4, 00))


@skipUnless(os.getenv('PTHELMA_TEST_ENHYDRIS_API'),
            "set PTHELMA_TEST_ENHYDRIS_API")
class TestWdat5(TestCase):
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
        self.cookies = enhydris_api.login(self.base_url, self.user,
                                          self.password)

        # Create as many timeseries as there are not-to-ignore parameters
        for parm in self.parameters:
            parm['ts_id'] = create_timeseries(self.cookies, self.__dict__
                                              ) if parm['expname'] else 0

    def tearDown(self):
        for parm in self.parameters:
            if parm['ts_id']:
                enhydris_api.delete_model(self.base_url, self.cookies,
                                          'Timeseries', parm['ts_id'])

    def test_check_config(self):
        self.assertRaises(ConfigurationError, Datafile_wdat5,
                          self.base_url, self.cookies, {})
        self.assertRaises(ConfigurationError, Datafile_wdat5,
                          self.base_url, self.cookies,
                          {'filename': 'hello', 'outsidetemp': '0',
                           'datafile_format': 'irrelevant',
                           'nonexistent_config_option': True})
        # Call it correctly and expect it doesn't raise anything
        Datafile_wdat5(self.base_url, self.cookies,
                       {'filename': 'hello', 'outsidetemp': '0',
                        'datafile_format': 'irrelevant'})

    def test_upload(self):
        # Initial upload of the stuff in the "1" directory
        d = {'filename': full_testdata_filename(os.path.join('wdat5', '1')),
             'datafile_format': 'irrelevant'}
        for parm in self.parameters:
            if parm['ts_id']:
                d[parm['name'].lower()] = parm['ts_id']
        df = Datafile_wdat5(self.base_url, self.cookies, d)
        df.update_database()
        self.check(d['filename'])

        # We now move to the "2" directory and re-run; "2" contains all the
        # data of "1" plus newer, so it should append the newer.
        d['filename'] = full_testdata_filename(os.path.join('wdat5', '2'))
        df = Datafile_wdat5(self.base_url, self.cookies, d)
        df.update_database()
        self.check(d['filename'])

    def test_dst(self):
        # Upload and check the "3" directory, which contains a DST switch
        d = {'filename': full_testdata_filename(os.path.join('wdat5', '3')),
             'datafile_format': 'irrelevant',
             'timezone': 'Europe/Athens'}
        for parm in self.parameters:
            if parm['ts_id']:
                d[parm['name'].lower()] = parm['ts_id']
        df = Datafile_wdat5(self.base_url, self.cookies, d)
        df.update_database()
        self.check(d['filename'])

    def check(self, datadir):
        for parm in self.parameters:
            if not parm['ts_id']:
                continue
            actual_ts = Timeseries(parm['ts_id'])
            enhydris_api.read_tsdata(self.base_url, self.cookies, actual_ts)
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
        considered equal to both 0.5 and 0.6. Actually 0.548 is also considered
        equal to 0.6 (we round 0.548 to 0.55, then we consider it equal to 0.6
        [and 0.5]). This is because WeatherLink sucks when exporting values.
        """
        a = round(a, places + 1)
        b = round(b, places + 1)
        tolerance = 10 ** (-places - 3)
        if abs(a - b) <= 0.5 * 10 ** (-places) + tolerance:
            return
        super(TestWdat5, self).assertAlmostEqual(a, b, places=places, msg=msg)


skip_test_odbc = True
skip_test_odbc_message = ''
if sys.platform != 'win32':
    skip_test_odbc_message = 'Windows only'
elif not os.getenv('PTHELMA_TEST_ENHYDRIS_API'):
    skip_test_odbc_message = 'set PTHELMA_TEST_ENHYDRIS_API'
else:
    try:
        import pyodbc
        if 'Microsoft Access Driver (*.mdb)' not in pyodbc.drivers():
            skip_test_odbc_message = \
                'Install ODBC "Microsoft Access Driver (*.mdb)"'
        else:
            skip_test_odbc = False
    except ImportError:
        skip_test_odbc_message = 'Install pyodbc'


@skipIf(skip_test_odbc, skip_test_odbc_message)
class TestOdbc(TestCase):
    class_being_tested = Datafile_odbc
    ref_ts1 = Timeseries(0)
    ref_ts1.read(StringIO(textwrap.dedent('''\
                                          2014-03-30 10:55,12.8,
                                          2014-03-30 10:56,12.8,
                                          2014-03-30 10:57,12.9,
                                          2014-03-30 23:12,12.9,
                                          2014-03-30 23:42,12.9,
                                          2014-03-31 00:12,11.9,
                                          2014-03-31 00:27,11.7,
                                          2014-03-31 00:42,11.7,
                                          2014-03-31 01:27,10.9,
                                          2014-03-31 15:11,21,
                                          2014-03-31 19:26,16.4,
                                          2014-03-31 20:11,14.6,
                                          2014-03-31 20:26,14.3,
                                          2014-03-31 20:41,13.9,
                                          2014-04-01 14:41,20.8,
                                          2014-04-01 15:41,21,
                                          2014-04-01 15:56,21.3,
                                          ''')))
    ref_ts2 = Timeseries(0)
    ref_ts2.read(StringIO(textwrap.dedent('''\
                                          2014-03-30 10:55,99.9,
                                          2014-03-30 10:56,99.8,
                                          2014-03-30 10:57,99.9,
                                          2014-03-30 23:12,99.9,
                                          2014-03-30 23:42,99.9,
                                          2014-03-31 00:12,99.8,
                                          2014-03-31 00:27,99.8,
                                          2014-03-31 00:42,99.9,
                                          2014-03-31 01:27,99.8,
                                          2014-03-31 15:11,52.3,
                                          2014-03-31 19:26,80.8,
                                          2014-03-31 20:11,87.7,
                                          2014-03-31 20:26,91,
                                          2014-03-31 20:41,93.6,
                                          2014-04-01 14:41,78,
                                          2014-04-01 15:41,73.8,
                                          2014-04-01 15:56,66.1,
                                          ''')))
    file1 = 'DRIVER=Microsoft Access Driver (*.mdb);DBQ={}'.format(
        full_testdata_filename('msaccess1.mdb'))
    file2 = 'DRIVER=Microsoft Access Driver (*.mdb);DBQ={}'.format(
        full_testdata_filename('msaccess2.mdb'))
    datafiledict = {'table': 'Clima',
                    'date_sql': "Date + ' ' + Time",
                    'data_columns': 'T out,H out',
                    'date_format': '%d/%m/%Y %H:%M:%S',
                    'decimal_separator': ',',
                    }

    def setUp(self):
        get_server_from_env(self.__dict__)

        if not self.class_being_tested or not self.base_url:
            return

        # Login
        self.cookies = enhydris_api.login(self.base_url,
                                          self.user,
                                          self.password)

        # Create two timeseries
        self.timeseries_id1 = create_timeseries(self.cookies, self.__dict__)
        self.timeseries_id2 = create_timeseries(self.cookies, self.__dict__)
        self.datafile_fields = "{0},{1}".format(self.timeseries_id1,
                                                self.timeseries_id2)
        self.ts1 = Timeseries(self.timeseries_id1)
        self.ts2 = Timeseries(self.timeseries_id2)

    def tearDown(self):
        if not self.class_being_tested or not self.base_url:
            return
        enhydris_api.delete_model(self.base_url, self.cookies,
                                  'Timeseries', self.timeseries_id2)
        enhydris_api.delete_model(self.base_url, self.cookies,
                                  'Timeseries', self.timeseries_id1)

    def check_config_test(self):
        self.assertRaises(ConfigurationError, self.class_being_tested,
                          self.base_url, self.cookies, {})
        self.assertRaises(ConfigurationError, self.class_being_tested,
                          self.base_url, self.cookies,
                          {'filename': 'hello', 'datafile_fields': '0',
                           'datafile_format': 'msaccess',
                           'table': 'atable',
                           'date_sql': 'somecolumn',
                           'data_columns': 'acolumn1,acolumn2',
                           'nonexistent_config_option': True})
        # Call it correctly and expect it doesn't raise anything
        self.class_being_tested(self.base_url, self.cookies,
                                {'filename': 'hello', 'datafile_fields': '0',
                                 'datafile_format': 'msaccess',
                                 'table': 'atable',
                                 'date_sql': 'somecolumn',
                                 'data_columns': 'acolumn1,acolumn2',
                                 })

    def upload_test(self):
        d = {'filename': self.file1,
             'datafile_fields': self.datafile_fields,
             'datafile_format': 'msaccess',
             'table': 'Clima'}
        d.update(self.datafiledict)
        df = self.class_being_tested(self.base_url, self.cookies, d)
        df.update_database()
        enhydris_api.read_tsdata(self.base_url, self.cookies, self.ts1)
        enhydris_api.read_tsdata(self.base_url, self.cookies, self.ts2)
        self.assertEqual(len(self.ts1), 10)
        self.assertEqual(len(self.ts2), 10)
        (items1, items2, ritems1, ritems2) = [
            x.items() for x in (self.ts1, self.ts2,
                                self.ref_ts1, self.ref_ts2)]
        for i in range(0, 10):
            self.assertEqual(items1[i][0], ritems1[i][0])
            self.assertAlmostEqual(items1[i][1], ritems1[i][1], 4)
            self.assertEqual(items1[i][1].flags, ritems1[i][1].flags)
            self.assertEqual(items2[i][0], ritems2[i][0])
            self.assertAlmostEqual(items2[i][1], ritems2[i][1], 4)
            self.assertEqual(items2[i][1].flags, ritems2[i][1].flags)
        d['filename'] = self.file2
        df = self.class_being_tested(self.base_url, self.cookies, d)
        df.update_database()
        enhydris_api.read_tsdata(self.base_url, self.cookies, self.ts1)
        enhydris_api.read_tsdata(self.base_url, self.cookies, self.ts2)
        self.assertEqual(len(self.ts1), 17)
        self.assertEqual(len(self.ts2), 17)
        (items1, items2, ritems1, ritems2) = [
            x.items() for x in (self.ts1, self.ts2,
                                self.ref_ts1, self.ref_ts2)]
        for i in range(0, 17):
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


class LoggertodbAppTestCase(TestCase):

    def setUp(self):
        self.tempdir = tempfile.mkdtemp()
        self.config_file = os.path.join(self.tempdir, 'loggertodb.conf')
        self.saved_argv = sys.argv
        sys.argv = ['loggertodb', '--traceback', self.config_file]

    def tearDown(self):
        sys.argv = self.saved_argv
        shutil.rmtree(self.tempdir)

    def test_nonexistent_config_file(self):
        app = LoggertodbApp()
        sys.argv = ['loggertodb',
                    os.path.join(self.tempdir, 'nonexistent.conf')]
        stderr = StringIO()
        orig_stderr = sys.stderr
        sys.stderr = stderr
        try:
            app.run()
            self.assertTrue(False)
        except SystemExit:
            self.assertTrue('nonexistent.conf' in stderr.getvalue())
        finally:
            sys.stderr = orig_stderr

    def test_wrong_configuration1(self):
        app = LoggertodbApp()
        with open(self.config_file, 'w') as f:
            f.write(textwrap.dedent('''\
                [General]
                user = a_user
                password = a_password
                '''))
        self.assertRaises(NoOptionError, app.run, dry=True)

    def test_wrong_configuration2(self):
        app = LoggertodbApp()
        with open(self.config_file, 'w') as f:
            f.write(textwrap.dedent('''\
                [General]
                base_url = a_base_url
                user = a_user
                password = a_password
                nonexistent_option = an_option
                '''))
        self.assertRaises(InvalidOptionError, app.run, dry=True)

    def test_wrong_configuration3(self):
        app = LoggertodbApp()
        with open(self.config_file, 'w') as f:
            f.write(textwrap.dedent('''\
                [General]
                base_url = a_base_url
                user = a_user
                password = a_password
                loglevel = NONEXISTENT_LOG_LEVEL
                '''))
        self.assertRaises(WrongValueError, app.run, dry=True)

    def test_correct_configuration1(self):
        app = LoggertodbApp()
        with open(self.config_file, 'w') as f:
            f.write(textwrap.dedent('''\
                [General]
                base_url = a_base_url
                user = a_user
                password = a_password
                '''))
        app.run(dry=True)

    def test_correct_configuration2(self):
        app = LoggertodbApp()
        with open(self.config_file, 'w') as f:
            f.write(textwrap.dedent('''\
                [General]
                base_url = a_base_url
                user = a_user
                password = a_password
                loglevel = ERROR
                '''))
        app.run(dry=True)
