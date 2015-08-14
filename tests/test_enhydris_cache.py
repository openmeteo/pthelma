# -*- coding: utf8 -*-
import json
import os
import shutil
import sys
import tempfile
import textwrap
from unittest import TestCase, skipUnless

from six import StringIO
from six.moves import configparser

from pthelma import enhydris_api
from pthelma.enhydris_cache import EnhydrisCacheApp, TimeseriesCache
from pthelma.timeseries import Timeseries


@skipUnless(os.getenv('PTHELMA_TEST_ENHYDRIS_API'),
            'set PTHELMA_TEST_ENHYDRIS_API')
class TimeseriesCacheTestCase(TestCase):
    test_timeseries1 = textwrap.dedent("""\
                                   2014-01-01 08:00,11,
                                   2014-01-02 08:00,12,
                                   2014-01-03 08:00,13,
                                   2014-01-04 08:00,14,
                                   2014-01-05 08:00,15,
                                   """)
    test_timeseries2 = textwrap.dedent("""\
                                   2014-07-01 08:00,9.11,
                                   2014-07-02 08:00,9.12,
                                   2014-07-03 08:00,9.13,
                                   2014-07-04 08:00,9.14,
                                   2014-07-05 08:00,9.15,
                                   """)
    timeseries1_top = ''.join(test_timeseries1.splitlines(True)[:-1])
    timeseries2_top = ''.join(test_timeseries2.splitlines(True)[:-1])
    timeseries1_bottom = test_timeseries1.splitlines(True)[-1]
    timeseries2_bottom = test_timeseries2.splitlines(True)[-1]

    def setUp(self):
        self.parms = json.loads(os.getenv('PTHELMA_TEST_ENHYDRIS_API'))
        self.cookies = enhydris_api.login(self.parms['base_url'],
                                          self.parms['user'],
                                          self.parms['password'])

        # Create two time series
        j = {
            'gentity': self.parms['station_id'],
            'variable': self.parms['variable_id'],
            'unit_of_measurement': self.parms['unit_of_measurement_id'],
            'time_zone': self.parms['time_zone_id'],
            'time_step': 3,
            'timestamp_offset_minutes': 0,
            'timestamp_offset_months': 0,
            'remarks': 'Très importante',
        }
        self.ts1_id = enhydris_api.post_model(
            self.parms['base_url'], self.cookies, 'Timeseries', j)
        self.ts2_id = enhydris_api.post_model(
            self.parms['base_url'], self.cookies, 'Timeseries', j)
        assert self.ts1_id != self.ts2_id

        # Add some data (all but the last record) to the database
        ts = Timeseries(self.ts1_id)
        ts.read(StringIO(self.timeseries1_top))
        enhydris_api.post_tsdata(self.parms['base_url'], self.cookies, ts)
        ts = Timeseries(self.ts2_id)
        ts.read(StringIO(self.timeseries2_top))
        enhydris_api.post_tsdata(self.parms['base_url'], self.cookies, ts)

        # Temporary directory for cache files
        self.tempdir = tempfile.mkdtemp()
        self.savedcwd = os.getcwd()
        os.chdir(self.tempdir)

    def tearDown(self):
        os.chdir(self.savedcwd)
        shutil.rmtree(self.tempdir)

    def test_update(self):
        self.parms = json.loads(os.getenv('PTHELMA_TEST_ENHYDRIS_API'))
        timeseries_group = [{'base_url': self.parms['base_url'],
                             'id': self.ts1_id,
                             'user': self.parms['user'],
                             'password': self.parms['password'],
                             'file': 'file1',
                             },
                            {'base_url': self.parms['base_url'],
                             'id': self.ts2_id,
                             'user': self.parms['user'],
                             'password': self.parms['password'],
                             'file': 'file2',
                             },
                            ]
        # Cache the two timeseries
        cache = TimeseriesCache(timeseries_group)
        cache.update()

        # Check that the cached stuff is what it should be
        with open('file1') as f:
            ts1_before = Timeseries()
            ts1_before.read_file(f)
            self.assertEqual(ts1_before.time_step.length_minutes, 1440)
            self.assertEqual(ts1_before.time_step.length_months, 0)
            c = StringIO()
            ts1_before.write(c)
            self.assertEqual(c.getvalue().replace('\r', ''),
                             self.timeseries1_top)
        with open('file2') as f:
            ts2_before = Timeseries()
            ts2_before.read_file(f)
            self.assertEqual(ts2_before.time_step.length_minutes, 1440)
            self.assertEqual(ts2_before.time_step.length_months, 0)
            c = StringIO()
            ts2_before.write(c)
            self.assertEqual(c.getvalue().replace('\r', ''),
                             self.timeseries2_top)

        # Append a record to the database for each timeseries
        ts = Timeseries(self.ts1_id)
        ts.read(StringIO(self.timeseries1_bottom))
        enhydris_api.post_tsdata(self.parms['base_url'], self.cookies, ts)
        ts = Timeseries(self.ts2_id)
        ts.read(StringIO(self.timeseries2_bottom))
        enhydris_api.post_tsdata(self.parms['base_url'], self.cookies, ts)

        # Update the cache
        cache.update()

        # Check that the cached stuff is what it should be
        with open('file1') as f:
            ts1_after = Timeseries()
            ts1_after.read_file(f)
            self.assertEqual(ts1_after.time_step.length_minutes, 1440)
            self.assertEqual(ts1_after.time_step.length_months, 0)
            c = StringIO()
            ts1_after.write(c)
            self.assertEqual(c.getvalue().replace('\r', ''),
                             self.test_timeseries1)
        with open('file2') as f:
            ts2_after = Timeseries()
            ts2_after.read_file(f)
            self.assertEqual(ts2_after.time_step.length_minutes, 1440)
            self.assertEqual(ts2_after.time_step.length_months, 0)
            c = StringIO()
            ts2_after.write(c)
            self.assertEqual(c.getvalue().replace('\r', ''),
                             self.test_timeseries2)

        # Check that the time series comments are the same before and after
        self.assertEqual(ts1_before.comment, ts1_after.comment)
        self.assertEqual(ts2_before.comment, ts2_after.comment)


@skipUnless(os.getenv('PTHELMA_TEST_ENHYDRIS_API'),
            'set PTHELMA_TEST_ENHYDRIS_API')
class EnhydrisCacheAppTestCase(TestCase):

    def __init__(self, *args, **kwargs):
        super(EnhydrisCacheAppTestCase, self).__init__(*args, **kwargs)

        # Python 2.7 compatibility
        try:
            self.assertRaisesRegex
        except AttributeError:
            self.assertRaisesRegex = self.assertRaisesRegexp

    def setUp(self):
        self.tempdir = tempfile.mkdtemp()
        self.config_file = os.path.join(self.tempdir, 'enhydris_cache.conf')
        self.saved_argv = sys.argv
        sys.argv = ['enhydris_cache', '--traceback', self.config_file]
        self.savedcwd = os.getcwd()

        # Create two stations, each one with a time series
        self.parms = json.loads(os.getenv('PTHELMA_TEST_ENHYDRIS_API'))
        self.cookies = enhydris_api.login(self.parms['base_url'],
                                          self.parms['user'],
                                          self.parms['password'])
        self.station1_id = enhydris_api.post_model(
            self.parms['base_url'], self.cookies, 'Station',
            {'name': 'station1',
             'srid': 4326,
             'point': 'POINT (23.78743 37.97385)',
             'copyright_holder': 'Joe User',
             'copyright_years': '2014',
             'stype': 1,
             'owner': self.parms['owner_id'],
             })
        self.timeseries1_id = enhydris_api.post_model(
            self.parms['base_url'], self.cookies, 'Timeseries',
            {'gentity': self.station1_id,
             'variable': self.parms['variable_id'],
             'unit_of_measurement': self.parms['unit_of_measurement_id'],
             'time_zone': self.parms['time_zone_id']})
        self.station2_id = enhydris_api.post_model(
            self.parms['base_url'], self.cookies, 'Station',
            {'name': 'station1',
             'srid': 4326,
             'point': 'POINT (24.56789 38.76543)',
             'copyright_holder': 'Joe User',
             'copyright_years': '2014',
             'stype': 1,
             'owner': self.parms['owner_id'],
             })
        self.timeseries2_id = enhydris_api.post_model(
            self.parms['base_url'], self.cookies, 'Timeseries',
            {'gentity': self.station2_id,
             'variable': self.parms['variable_id'],
             'unit_of_measurement': self.parms['unit_of_measurement_id'],
             'time_zone': self.parms['time_zone_id']})

        # Prepare a configuration file (some tests override it)
        with open(self.config_file, 'w') as f:
            f.write(textwrap.dedent('''\
                [General]
                cache_dir = {self.tempdir}

                [timeseries1]
                base_url = {base_url}
                id = {self.timeseries1_id}
                file = file1
                user = {self.parms[user]}
                password = {self.parms[password]}

                [timeseries2]
                base_url = {base_url}
                id = {self.timeseries2_id}
                file = file2
                user = {self.parms[user]}
                password = {self.parms[password]}
                ''').format(self=self, base_url=self.parms['base_url']))

    def tearDown(self):
        os.chdir(self.savedcwd)
        shutil.rmtree(self.tempdir)
        sys.argv = self.saved_argv

    def test_correct_configuration(self):
        application = EnhydrisCacheApp()
        application.run(dry=True)

    def test_wrong_configuration1(self):
        with open(self.config_file, 'w') as f:
            f.write(textwrap.dedent('''\
                [General]
                cache_dir = {self.tempdir}
                nonexistent_option = irrelevant
                ''').format(self=self))
        application = EnhydrisCacheApp()
        self.assertRaisesRegex(configparser.Error, 'nonexistent_option',
                               application.run)

    def test_wrong_configuration2(self):
        with open(self.config_file, 'w') as f:
            f.write(textwrap.dedent('''\
                [General]
                cache_dir = {self.tempdir}

                [timeseries1]
                id = 5432
                file = file1
                ''').format(self=self))
        application = EnhydrisCacheApp()
        self.assertRaisesRegex(configparser.Error, 'base_url',
                               application.run)

    def test_wrong_configuration3(self):
        with open(self.config_file, 'w') as f:
            f.write(textwrap.dedent('''\
                [General]
                cache_dir = {self.tempdir}

                [timeseries1]
                base_url = wrongproto://irrelevant.com/
                id = non-numeric
                file = file1
                ''').format(self=self))
        application = EnhydrisCacheApp()
        self.assertRaisesRegex(configparser.Error, 'id',
                               application.run)

    def test_execute(self):
        application = EnhydrisCacheApp()
        application.read_command_line()
        application.read_configuration()
        application.setup_logger()

        # Check that the two files don't exist yet
        self.assertFalse(os.path.exists(os.path.join(self.tempdir, 'file1')))
        self.assertFalse(os.path.exists(os.path.join(self.tempdir, 'file2')))

        application.execute()

        # Check that it has created two files
        self.assertTrue(os.path.exists(os.path.join(self.tempdir, 'file1')))
        self.assertTrue(os.path.exists(os.path.join(self.tempdir, 'file2')))

        # The above is reasonably sufficient to know that it works, given
        # that lower-level functionality has been tested in other unit tests.
