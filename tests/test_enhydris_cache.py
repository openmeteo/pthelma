import json
import os
import shutil
import tempfile
import textwrap
from unittest import TestCase, skipUnless

from six import StringIO

from pthelma import enhydris_api
from pthelma.enhydris_cache import TimeseriesCache
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
            'actual_offset_minutes': 0,
            'actual_offset_months': 0,
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

    def tearDown(self):
        shutil.rmtree(self.tempdir)

    def test_update(self):
        self.parms = json.loads(os.getenv('PTHELMA_TEST_ENHYDRIS_API'))
        timeseries_group = [{'base_url': self.parms['base_url'],
                             'id': self.ts1_id,
                             'user': self.parms['user'],
                             'password': self.parms['password'],
                             },
                            {'base_url': self.parms['base_url'],
                             'id': self.ts2_id,
                             'user': self.parms['user'],
                             'password': self.parms['password'],
                             },
                            ]
        # Cache the two timeseries
        cache = TimeseriesCache(self.tempdir, timeseries_group)
        cache.update()

        # Check that the cached stuff is what it should be
        file1, file2 = [cache.get_filename(self.parms['base_url'], x)
                        for x in (self.ts1_id, self.ts2_id)]
        with open(file1) as f:
            ts = Timeseries()
            ts.read_file(f)
            self.assertEqual(ts.time_step.length_minutes, 1440)
            self.assertEqual(ts.time_step.length_months, 0)
            c = StringIO()
            ts.write(c)
            self.assertEqual(c.getvalue().replace('\r', ''),
                             self.timeseries1_top)
        with open(file2) as f:
            ts = Timeseries()
            ts.read_file(f)
            self.assertEqual(ts.time_step.length_minutes, 1440)
            self.assertEqual(ts.time_step.length_months, 0)
            c = StringIO()
            ts.write(c)
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
        file1, file2 = [cache.get_filename(self.parms['base_url'], x)
                        for x in (self.ts1_id, self.ts2_id)]
        with open(file1) as f:
            ts = Timeseries()
            ts.read_file(f)
            self.assertEqual(ts.time_step.length_minutes, 1440)
            self.assertEqual(ts.time_step.length_months, 0)
            c = StringIO()
            ts.write(c)
            self.assertEqual(c.getvalue().replace('\r', ''),
                             self.test_timeseries1)
        with open(file2) as f:
            ts = Timeseries()
            ts.read_file(f)
            self.assertEqual(ts.time_step.length_minutes, 1440)
            self.assertEqual(ts.time_step.length_months, 0)
            c = StringIO()
            ts.write(c)
            self.assertEqual(c.getvalue().replace('\r', ''),
                             self.test_timeseries2)
