import json
import os
import shutil
from six import StringIO
import tempfile
import textwrap
from unittest import TestCase, skipUnless

import numpy as np
from osgeo import ogr, gdal

from pthelma import enhydris_api
from pthelma.spatial import idw, interpolate_spatially, \
    update_timeseries_cache, create_ogr_layer_from_stations
from pthelma.timeseries import Timeseries


def add_point_to_layer(layer, x, y, value):
    p = ogr.Geometry(ogr.wkbPoint)
    p.AddPoint(x, y)
    f = ogr.Feature(layer.GetLayerDefn())
    f.SetGeometry(p)
    f.SetField('value', value)
    layer.CreateFeature(f)


class IdwTestCase(TestCase):

    def setUp(self):
        self.point = ogr.Geometry(ogr.wkbPoint)
        self.point.AddPoint(5.1, 2.5)

        self.data_source = ogr.GetDriverByName('memory').CreateDataSource(
            'tmp')
        self.data_layer = self.data_source.CreateLayer('test')
        self.data_layer.CreateField(ogr.FieldDefn('value', ogr.OFTReal))

    def tearDown(self):
        self.data_layer = None
        self.data_source = None
        self.point = None

    def test_idw_single_point(self):
        add_point_to_layer(self.data_layer, 5.3, 6.4, 42.8)
        self.assertAlmostEqual(idw(self.point, self.data_layer), 42.8)

    def test_idw_three_points(self):
        add_point_to_layer(self.data_layer, 6.4, 7.8, 33.0)
        add_point_to_layer(self.data_layer, 9.5, 7.4, 94.0)
        add_point_to_layer(self.data_layer, 7.1, 4.9, 67.7)
        self.assertAlmostEqual(idw(self.point, self.data_layer),
                               64.0902,
                               places=4)
        self.assertAlmostEqual(idw(self.point, self.data_layer, alpha=2.0),
                               64.1876,
                               places=4)


class InterpolateSpatiallyTestCase(TestCase):

    def setUp(self):
        # We will test on a 7x15 grid
        self.mask = np.zeros((7, 15), np.int8)
        self.mask[3, 3] = 1
        self.mask[6, 14] = 1
        self.mask[4, 13] = 1
        self.dataset = gdal.GetDriverByName('mem').Create('test', 15, 7, 1,
                                                          gdal.GDT_Byte)
        self.dataset.GetRasterBand(1).WriteArray(self.mask)

        # Prepare the result band
        self.dataset.AddBand(gdal.GDT_Float64)
        self.target_band = self.dataset.GetRasterBand(self.dataset.RasterCount)

        # Our grid represents a 70x150m area, lower-left co-ordinates (0, 0).
        self.dataset.SetGeoTransform((0, 10, 0, 70, 0, -10))

        # Now the data layer, with three points
        self.data_source = ogr.GetDriverByName('memory').CreateDataSource(
            'tmp')
        self.data_layer = self.data_source.CreateLayer('test')
        self.data_layer.CreateField(ogr.FieldDefn('value', ogr.OFTReal))
        add_point_to_layer(self.data_layer,  75.2, 10.7, 37.4)
        add_point_to_layer(self.data_layer, 125.7, 19.0, 24.0)
        add_point_to_layer(self.data_layer,   9.8, 57.1, 95.4)

    def tearDown(self):
        self.data_source = None
        self.raster = None

    def test_interpolate_idw(self):
        interpolate_spatially(self.dataset, self.data_layer, self.target_band,
                              idw)
        result = self.target_band.ReadAsArray()

        # All masked points and only those must be NaN
        # (^ is bitwise xor in Python)
        self.assertTrue((np.isnan(result) ^ (self.mask != 0)).all())

        self.assertAlmostEqual(result[3, 3],  62.9711, places=4)
        self.assertAlmostEqual(result[6, 14], 34.8381, places=4)
        self.assertAlmostEqual(result[4, 13], 30.7365, places=4)


@skipUnless(os.getenv('PTHELMA_TEST_ENHYDRIS_API'),
            'set PTHELMA_TEST_ENHYDRIS_API')
class CreateOgrLayerFromStationsTestCase(TestCase):

    def setUp(self):
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

        # Temporary directory for cache files
        self.tempdir = tempfile.mkdtemp()

    def tearDown(self):
        shutil.rmtree(self.tempdir)
        enhydris_api.delete_model(self.parms['base_url'], self.cookies,
                                  'Station', self.station1_id)
        enhydris_api.delete_model(self.parms['base_url'], self.cookies,
                                  'Station', self.station2_id)

    def test_create_ogr_layer_from_stations(self):
        data_source = ogr.GetDriverByName('memory').CreateDataSource('tmp')
        group = [{'base_url': self.parms['base_url'],
                  'user': self.parms['user'],
                  'id': self.timeseries1_id},
                 {'base_url': self.parms['base_url'],
                  'user': self.parms['user'],
                  'id': self.timeseries2_id}]
        layer = create_ogr_layer_from_stations(group, data_source,
                                               self.tempdir)
        self.assertTrue(layer.GetFeatureCount(), 2)
        ref = [{'x': 23.78743, 'y': 37.97385,
                'timeseries_id': self.timeseries1_id},
               {'x': 24.56789, 'y': 38.76543,
                'timeseries_id': self.timeseries2_id},
               ]
        for feature, r in zip(layer, ref):
            self.assertEqual(feature.GetField('timeseries_id'),
                             r['timeseries_id'])
            self.assertAlmostEqual(feature.GetGeometryRef().GetX(), r['x'], 5)
            self.assertAlmostEqual(feature.GetGeometryRef().GetY(), r['y'], 5)


@skipUnless(os.getenv('PTHELMA_TEST_ENHYDRIS_API'),
            'set PTHELMA_TEST_ENHYDRIS_API')
class UpdateTimeseriesTestCase(TestCase):
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

    def test_update_timeseries_cache(self):
        self.parms = json.loads(os.getenv('PTHELMA_TEST_ENHYDRIS_API'))
        timeseries_groups = {
            'one': [{'base_url': self.parms['base_url'],
                     'id': self.ts1_id,
                     'user': self.parms['user'],
                     'password': self.parms['password'],
                     },
                    {'base_url': self.parms['base_url'],
                     'id': self.ts2_id,
                     'user': self.parms['user'],
                     'password': self.parms['password'],
                     },
                    ],
        }
        # Cache the two timeseries
        update_timeseries_cache(self.tempdir, timeseries_groups)

        # Check that the cached stuff is what it should be
        file1, file2 = [os.path.join(self.tempdir, '{}.hts'.format(x))
                        for x in (self.ts1_id, self.ts2_id)]
        with open(file1) as f:
            self.assertEqual(f.read().replace('\r', ''), self.timeseries1_top)
        with open(file2) as f:
            self.assertEqual(f.read().replace('\r', ''), self.timeseries2_top)

        # Append a record to the database for each timeseries
        ts = Timeseries(self.ts1_id)
        ts.read(StringIO(self.timeseries1_bottom))
        enhydris_api.post_tsdata(self.parms['base_url'], self.cookies, ts)
        ts = Timeseries(self.ts2_id)
        ts.read(StringIO(self.timeseries2_bottom))
        enhydris_api.post_tsdata(self.parms['base_url'], self.cookies, ts)

        # Update the cache
        update_timeseries_cache(self.tempdir, timeseries_groups)

        # Check that the cached stuff is what it should be
        file1, file2 = [os.path.join(self.tempdir, '{}.hts'.format(x))
                        for x in (self.ts1_id, self.ts2_id)]
        with open(file1) as f:
            self.assertEqual(f.read().replace('\r', ''), self.test_timeseries1)
        with open(file2) as f:
            self.assertEqual(f.read().replace('\r', ''), self.test_timeseries2)
