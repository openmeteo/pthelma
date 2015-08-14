from datetime import datetime
from glob import glob
import math
import os
import shutil
import six
from six import StringIO
from six.moves import configparser
import sys
import tempfile
import textwrap
from time import sleep
from unittest import TestCase, skipIf

import iso8601
from osgeo import gdal

gdal.UseExceptions()

if sys.platform != 'win32':
    import numpy as np
    from osgeo import ogr, osr, gdal
    from pthelma.spatial import create_ogr_layer_from_timeseries, \
        extract_point_from_raster, extract_point_timeseries_from_rasters, \
        h_integrate, idw, integrate, SpatializeApp, WrongValueError
    skip_osgeo = False
    skip_osgeo_message = ''
else:
    skip_osgeo = True
    skip_osgeo_message = 'Not available on Windows'


def add_point_to_layer(layer, x, y, value):
    p = ogr.Geometry(ogr.wkbPoint)
    p.AddPoint(x, y)
    f = ogr.Feature(layer.GetLayerDefn())
    f.SetGeometry(p)
    f.SetField('value', value)
    layer.CreateFeature(f)


@skipIf(skip_osgeo, skip_osgeo_message)
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
                               64.090, places=3)
        self.assertAlmostEqual(idw(self.point, self.data_layer, alpha=2.0),
                               64.188, places=3)

    def test_idw_point_with_nan(self):
        add_point_to_layer(self.data_layer, 6.4, 7.8, 33.0)
        add_point_to_layer(self.data_layer, 9.5, 7.4, 94.0)
        add_point_to_layer(self.data_layer, 7.1, 4.9, 67.7)
        add_point_to_layer(self.data_layer, 7.2, 5.4, float('nan'))
        self.assertAlmostEqual(idw(self.point, self.data_layer),
                               64.090, places=3)
        self.assertAlmostEqual(idw(self.point, self.data_layer, alpha=2.0),
                               64.188, places=3)


@skipIf(skip_osgeo, skip_osgeo_message)
class IntegrateTestCase(TestCase):

    # The calculations for this test have been made manually in
    # data/spatial_calculations.ods, tab test_integrate_idw.

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
        self.dataset.AddBand(gdal.GDT_Float32)
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

    def test_integrate_idw(self):
        integrate(self.dataset, self.data_layer, self.target_band, idw)
        result = self.target_band.ReadAsArray()
        nodatavalue = self.target_band.GetNoDataValue()

        # All masked points and only those must be no data
        # (^ is bitwise xor in Python)
        self.assertTrue(((result == nodatavalue) ^ (self.mask != 0)).all())

        self.assertAlmostEqual(result[3, 3],  62.971, places=3)
        self.assertAlmostEqual(result[6, 14], 34.838, places=3)
        self.assertAlmostEqual(result[4, 13], 30.737, places=3)


@skipIf(skip_osgeo, skip_osgeo_message)
class CreateOgrLayerFromTimeseriesTestCase(TestCase):

    def setUp(self):
        self.tempdir = tempfile.mkdtemp()

        # Create two time series
        with open(os.path.join(self.tempdir, 'ts1'), 'w') as f:
            f.write(textwrap.dedent("""\
                                    Location=23.78743 37.97385 4326

                                    """))
        with open(os.path.join(self.tempdir, 'ts2'), 'w') as f:
            f.write(textwrap.dedent("""\
                                    Location=24.56789 38.76543 4326

                                    """))

    def tearDown(self):
        shutil.rmtree(self.tempdir)

    def test_create_ogr_layer_from_timeseries(self):
        data_source = ogr.GetDriverByName('memory').CreateDataSource('tmp')
        filenames = [os.path.join(self.tempdir, x) for x in ('ts1', 'ts2')]
        layer = create_ogr_layer_from_timeseries(filenames, 2100, data_source)
        self.assertTrue(layer.GetFeatureCount(), 2)
        # The co-ordinates below are converted from WGS84 to Greek Grid/GGRS87
        ref = [{'x': 481180.63, 'y': 4202647.01,  # 23.78743, 37.97385
                'filename': filenames[0]},
               {'x': 549187.44, 'y': 4290612.25,  # 24.56789, 38.76543
                'filename': filenames[1]},
               ]
        for feature, r in zip(layer, ref):
            self.assertEqual(feature.GetField('filename'), r['filename'])
            self.assertAlmostEqual(feature.GetGeometryRef().GetX(), r['x'], 2)
            self.assertAlmostEqual(feature.GetGeometryRef().GetY(), r['y'], 2)


@skipIf(skip_osgeo, skip_osgeo_message)
class HIntegrateTestCase(TestCase):
    """
    We will test on a 4x3 raster:

                        ABCD
                       1
                       2
                       3

    There will be three stations: two will be exactly at the center of
    gridpoints A3 and B3, and one will be slightly outside the grid (somewhere
    in E2). We assume the bottom left corner of A3 to have co-ordinates (0, 0)
    and the gridpoint to be 10 km across. We also consider C1 to be masked out.

    The calculations for the test have been made manually in
    data/spatial_calculations.ods, tab test_h_integrate.
    """

    def create_mask(self):
        mask_array = np.ones((3, 4), np.int8)
        mask_array[0, 2] = 0
        self.mask = gdal.GetDriverByName('mem').Create('mask', 4, 3, 1,
                                                       gdal.GDT_Byte)
        self.mask.SetGeoTransform((0, 10000, 0, 30000, 0, -10000))
        self.mask.GetRasterBand(1).WriteArray(mask_array)

    def setUp(self):
        self.tempdir = tempfile.mkdtemp()

        self.filenames = [os.path.join(self.tempdir, x)
                          for x in ('ts1', 'ts2', 'ts3', 'ts4')]
        with open(self.filenames[0], 'w') as f:
            f.write("Location=19.557285 0.0473312 2100\n"  # GGRS87=5000 5000
                    "\n"
                    "2014-04-22 12:50,5.03,\n"
                    "2014-04-22 13:00,0.54,\n"
                    "2014-04-22 13:10,6.93,\n")
        with open(self.filenames[1], 'w') as f:
            f.write("Location=19.64689 0.04734 2100\n"  # GGRS87=15000 5000
                    "\n"
                    "2014-04-22 12:50,2.90,\n"
                    "2014-04-22 13:00,2.40,\n"
                    "2014-04-22 13:10,9.16,\n")
        with open(self.filenames[2], 'w') as f:
            f.write("Location=19.88886 0.12857 2100\n"  # GGRS87=42000 14000
                    "\n"
                    "2014-04-22 12:50,9.70,\n"
                    "2014-04-22 13:00,1.84,\n"
                    "2014-04-22 13:10,7.63,\n")
        with open(self.filenames[3], 'w') as f:
            # This station is missing the date required,
            # so it should not be taken into account
            f.write("Location=19.66480 0.15560 2100\n"  # GGRS87=17000 17000
                    "\n"
                    "2014-04-22 12:50,9.70,\n"
                    "2014-04-22 13:10,7.63,\n")

        self.create_mask()
        self.stations = ogr.GetDriverByName('memory').CreateDataSource('tmp')
        self.stations_layer = create_ogr_layer_from_timeseries(
            self.filenames, 2100, self.stations)

    def tearDown(self):
        shutil.rmtree(self.tempdir)

    def test_h_integrate(self):
        output_filename_prefix = os.path.join(self.tempdir, 'test')
        result_filename = output_filename_prefix + '-2014-04-22-13-00.tif'
        h_integrate(mask=self.mask,
                    stations_layer=self.stations_layer,
                    date=datetime(2014, 4, 22, 13, 0),
                    output_filename_prefix=output_filename_prefix,
                    date_fmt='%Y-%m-%d %H:%M%z', funct=idw, kwargs={})
        f = gdal.Open(result_filename)
        result = f.GetRasterBand(1).ReadAsArray()
        nodatavalue = f.GetRasterBand(1).GetNoDataValue()
        expected_result = np.array([[1.5088, 1.6064, nodatavalue, 1.7237],
                                    [1.3828, 1.6671, 1.7336, 1.7662],
                                    [0.5400, 2.4000, 1.7954, 1.7504]])
        np.testing.assert_almost_equal(result, expected_result, decimal=4)
        f = None

        # Wait long enough to make sure that, if we write to a file, its
        # modification time will be distinguishable from the modification time
        # of any file that has been written to so far (how long we need to wait
        # depends on the file system, so we use a test file).
        mtime_test_file = os.path.join(self.tempdir, 'test_mtime')
        with open(mtime_test_file, 'w') as f:
            f.write('hello, world')
        reference_mtime = os.path.getmtime(mtime_test_file)
        while os.path.getmtime(mtime_test_file) - reference_mtime < 0.001:
            sleep(0.001)
            with open(mtime_test_file, 'w') as f:
                f.write('hello, world')

        # Try re-calculating the output; the output file should not be touched
        # at all.
        result_mtime = os.path.getmtime(result_filename)
        h_integrate(mask=self.mask,
                    stations_layer=self.stations_layer,
                    date=datetime(2014, 4, 22, 13, 0),
                    output_filename_prefix=output_filename_prefix,
                    date_fmt='%Y-%m-%d %H:%M%z', funct=idw, kwargs={})
        self.assertEqual(os.path.getmtime(result_filename), result_mtime)

        # Now change one of the input files so that it contains new data that
        # can be used in the same calculation, and try recalculating. This time
        # the file should be recalculated.
        with open(self.filenames[3], 'w') as f:
            f.write("Location=19.66480 0.15560 2100\n"  # GGRS87=17000 17000
                    "\n"
                    "2014-04-22 12:50,9.70,\n"
                    "2014-04-22 13:00,4.70,\n"
                    "2014-04-22 13:10,7.63,\n")
        h_integrate(mask=self.mask,
                    stations_layer=self.stations_layer,
                    date=datetime(2014, 4, 22, 13, 0),
                    output_filename_prefix=output_filename_prefix,
                    date_fmt='%Y-%m-%d %H:%M%z', funct=idw, kwargs={})
        self.assertGreater(os.path.getmtime(result_filename),
                           result_mtime + 0.0009)
        f = gdal.Open(result_filename)
        result = f.GetRasterBand(1).ReadAsArray()
        nodatavalue = f.GetRasterBand(1).GetNoDataValue()
        expected_result = np.array([[2.6736, 3.1053, nodatavalue, 2.5166],
                                    [2.3569, 3.5775, 2.9512, 2.3596],
                                    [0.5400, 2.4000, 2.5377, 2.3779]])
        np.testing.assert_almost_equal(result, expected_result, decimal=4)
        f = None


def setup_input_file(filename, value, timestamp):
    """Save value, which is an np array, to a GeoTIFF file."""
    nodata = 1e8
    value[np.isnan(value)] = nodata
    f = gdal.GetDriverByName('GTiff').Create(
        filename, 3, 3, 1, gdal.GDT_Float32)
    try:
        f.SetMetadataItem('TIMESTAMP', timestamp.isoformat())
        f.SetGeoTransform((22.0, 0.01, 0, 38.0, 0, -0.01))
        wgs84 = osr.SpatialReference()
        wgs84.ImportFromEPSG(4326)
        f.SetProjection(wgs84.ExportToWkt())
        f.GetRasterBand(1).SetNoDataValue(nodata)
        f.GetRasterBand(1).WriteArray(value)
    finally:
        f = None


@skipIf(skip_osgeo, skip_osgeo_message)
class ExtractPointFromRasterTestCase(TestCase):

    def setUp(self):
        self.tempdir = tempfile.mkdtemp()

    def tearDown(self):
        shutil.rmtree(self.tempdir)

    def test_extract_point_from_raster(self):
        filename = os.path.join(self.tempdir, 'test_raster')
        nan = float('nan')
        setup_input_file(
            filename,
            np.array([[1.1, nan, 1.3],
                      [2.1, 2.2, nan],
                      [3.1, 3.2, 3.3]]),
            datetime(2014, 11, 21, 16, 1))

        fp = gdal.Open(filename)

        # Get the top left point, coordinates 22.00, 38.00
        point = ogr.Geometry(ogr.wkbPoint)
        sr = osr.SpatialReference()
        sr.ImportFromEPSG(4326)
        point.AssignSpatialReference(sr)
        point.AddPoint(22.0, 38.0)
        self.assertAlmostEqual(extract_point_from_raster(point, fp), 1.1,
                               places=2)

        # Get the top middle point, co-ordinates 22.01, 38.00
        point = ogr.Geometry(ogr.wkbPoint)
        sr = osr.SpatialReference()
        sr.ImportFromEPSG(4326)
        point.AssignSpatialReference(sr)
        point.AddPoint(22.01, 38.0)
        self.assertTrue(math.isnan(extract_point_from_raster(point, fp)))

        # Get the middle point, using co-ordinates almost to the center of
        # the four lower left points, and only a little bit towards the center.
        point = ogr.Geometry(ogr.wkbPoint)
        sr = osr.SpatialReference()
        sr.ImportFromEPSG(4326)
        point.AssignSpatialReference(sr)
        point.AddPoint(22.00501, 37.98501)
        self.assertAlmostEqual(extract_point_from_raster(point, fp), 2.2,
                               places=2)

        # Use almost exactly same point as before, only slightly altered
        # so that we get bottom left point instead.
        point = ogr.Geometry(ogr.wkbPoint)
        sr = osr.SpatialReference()
        sr.ImportFromEPSG(4326)
        point.AssignSpatialReference(sr)
        point.AddPoint(22.00499, 37.98499)
        self.assertAlmostEqual(extract_point_from_raster(point, fp), 3.1,
                               places=2)

        # Now try same two things as above, but with a different reference
        # system, GRS80; the result should be the same.
        point = ogr.Geometry(ogr.wkbPoint)
        sr = osr.SpatialReference()
        sr.ImportFromEPSG(2100)
        point.AssignSpatialReference(sr)
        point.AddPoint(324651, 4205742)
        self.assertAlmostEqual(extract_point_from_raster(point, fp), 2.2,
                               places=2)
        point = ogr.Geometry(ogr.wkbPoint)
        sr = osr.SpatialReference()
        sr.ImportFromEPSG(2100)
        point.AssignSpatialReference(sr)
        point.AddPoint(324648, 4205739)
        self.assertAlmostEqual(extract_point_from_raster(point, fp), 3.1,
                               places=2)

        # Try to get a point that is outside the raster; should raise an
        # exception.
        point = ogr.Geometry(ogr.wkbPoint)
        sr = osr.SpatialReference()
        sr.ImportFromEPSG(4326)
        point.AssignSpatialReference(sr)
        point.AddPoint(21.0, 38.0)
        self.assertRaises(RuntimeError, extract_point_from_raster,
                          *(point, fp))

        fp = None

    def test_extract_point_timeseries_from_rasters(self):
        # Create three rasters
        filename = os.path.join(self.tempdir, 'test1.tif')
        setup_input_file(
            filename,
            np.array([[1.1, 1.2, 1.3],
                      [2.1, 2.2, 2.3],
                      [3.1, 3.2, 3.3]]),
            datetime(2014, 11, 21, 16, 1))
        filename = os.path.join(self.tempdir, 'test2.tif')
        setup_input_file(
            filename,
            np.array([[11.1, 12.1, 13.1],
                      [21.1, 22.1, 23.1],
                      [31.1, 32.1, 33.1]]),
            datetime(2014, 11, 22, 16, 1))
        filename = os.path.join(self.tempdir, 'test0.tif')
        setup_input_file(
            filename,
            np.array([[110.1, 120.1, 130.1],
                      [210.1, 220.1, 230.1],
                      [310.1, 320.1, 330.1]]),
            datetime(2014, 11, 23, 16, 1))

        # Get the middle point, using co-ordinates almost to the center of
        # the four lower left points, and only a little bit towards the center.
        point = ogr.Geometry(ogr.wkbPoint)
        sr = osr.SpatialReference()
        sr.ImportFromEPSG(4326)
        point.AssignSpatialReference(sr)
        point.AddPoint(22.00501, 37.98501)
        files = glob(os.path.join(self.tempdir, '*.tif'))
        ts = extract_point_timeseries_from_rasters(files, point)
        outstring = StringIO()
        ts.write(outstring)
        self.assertEqual(outstring.getvalue(),
                         textwrap.dedent("""\
                                         2014-11-21 16:01,2.2,\r
                                         2014-11-22 16:01,22.1,\r
                                         2014-11-23 16:01,220.1,\r
                                         """))


@skipIf(skip_osgeo, skip_osgeo_message)
class SpatializeAppTestCase(TestCase):

    def __init__(self, *args, **kwargs):
        super(SpatializeAppTestCase, self).__init__(*args, **kwargs)

        # Python 2.7 compatibility
        try:
            self.assertRaisesRegex
        except AttributeError:
            self.assertRaisesRegex = self.assertRaisesRegexp

    def setUp(self):
        self.tempdir = tempfile.mkdtemp()
        self.output_dir = os.path.join(self.tempdir, 'output')
        self.config_file = os.path.join(self.tempdir, 'spatialize.conf')
        os.mkdir(self.output_dir)
        self.mask_file = os.path.join(self.tempdir, 'mask.tif')
        self.saved_argv = sys.argv
        sys.argv = ['spatialize', '--traceback', self.config_file]

        # Create two time series
        self.filenames = [os.path.join(self.tempdir, x)
                          for x in ('ts1', 'ts2')]
        with open(self.filenames[0], 'w') as f:
            f.write("Location=23.78743 37.97385 4326\n"
                    "Timezone=+0200\n"
                    "Time_step=60,0\n"
                    "\n")
        with open(self.filenames[1], 'w') as f:
            f.write("Location=24.56789 38.76543 4326\n"
                    "Timezone=EET (+0200)\n"
                    "Time_step=60,0\n"
                    "\n")

        # Prepare a configuration file (some tests override it)
        with open(self.config_file, 'w') as f:
            f.write(textwrap.dedent('''\
                [General]
                mask = {0.mask_file}
                epsg = 2100
                output_dir = {0.output_dir}
                filename_prefix = rainfall
                number_of_output_files = 24
                method = idw
                files = {0.filenames[0]}
                        {0.filenames[1]}
                ''').format(self))

    def tearDown(self):
        shutil.rmtree(self.tempdir)
        sys.argv = self.saved_argv

    def test_correct_configuration(self):
        application = SpatializeApp()
        application.run(dry=True)

    def test_wrong_configuration1(self):
        with open(self.config_file, 'w') as f:
            f.write(textwrap.dedent('''\
                [General]
                mask = {0.mask_file}
                epsg = 2100
                output_dir = {0.output_dir}
                filename_prefix = rainfall
                method = idw
                files = myfile
                ''').format(self))
        application = SpatializeApp()
        self.assertRaisesRegex(configparser.Error, 'number_of_output_files',
                               application.run)

    def test_wrong_configuration2(self):
        with open(self.config_file, 'w') as f:
            f.write(textwrap.dedent('''\
                [General]
                mask = {0.mask_file}
                epsg = 2100
                output_dir = {0.output_dir}
                filename_prefix = rainfall
                number_of_output_files = 24
                method = idw
                files = myfile
                nonexistent_option = irrelevant
                ''').format(self))
        application = SpatializeApp()
        self.assertRaisesRegex(configparser.Error, 'nonexistent_option',
                               application.run)

    def test_wrong_configuration_epsg(self):
        with open(self.config_file, 'w') as f:
            f.write(textwrap.dedent('''\
                [General]
                mask = {0.mask_file}
                epsg = 81122
                output_dir = {0.output_dir}
                filename_prefix = rainfall
                number_of_output_files = 24
                method = idw
                files = myfile
                ''').format(self))
        application = SpatializeApp()
        self.assertRaisesRegex(WrongValueError, 'epsg=81122',
                               application.run)

    def test_get_last_dates(self):
        filename = os.path.join(self.tempdir, 'timeseries.hts')
        with open(filename, 'w') as f:
            f.write(textwrap.dedent('''\
                2014-04-30 11:00,18.3,
                2014-04-30 12:00,19.3,
                2014-04-30 13:00,20.4,
                2014-04-30 14:00,21.4,
                '''))
        application = SpatializeApp()
        with open(filename) as f:
            self.assertEquals(application.get_last_dates(filename, 2),
                              [datetime(2014, 4, 30, 13, 0),
                               datetime(2014, 4, 30, 14, 0)])
            f.seek(0)
            self.assertEquals(application.get_last_dates(filename, 20),
                              [datetime(2014, 4, 30, 11, 0),
                               datetime(2014, 4, 30, 12, 0),
                               datetime(2014, 4, 30, 13, 0),
                               datetime(2014, 4, 30, 14, 0)])

    def test_dates_to_calculate(self):
        application = SpatializeApp()
        application.read_command_line()
        application.read_configuration()
        with open(self.filenames[0], 'w') as f:
            f.write(textwrap.dedent('''\
                2014-04-30 11:00,18.3,
                2014-04-30 13:00,20.4,
                2014-04-30 14:00,21.4,
                2014-04-30 15:00,22.4,
                '''))
        with open(self.filenames[1], 'w') as f:
            f.write(textwrap.dedent('''\
                Time_step=60,0
                Timestamp_rounding=0,0
                Timestamp_offset=0,0

                2014-04-30 11:00,18.3,
                2014-04-30 12:00,19.3,
                2014-04-30 13:00,20.4,
                2014-04-30 14:00,21.4,
                '''))

        # Check for number_of_output_files=24
        dates = []
        for d in application.dates_to_calculate:
            dates.append(d)
        self.assertEquals(dates, [datetime(2014, 4, 30, 11, 0),
                                  datetime(2014, 4, 30, 12, 0),
                                  datetime(2014, 4, 30, 13, 0),
                                  datetime(2014, 4, 30, 14, 0),
                                  datetime(2014, 4, 30, 15, 0)])

        # Check for number_of_output_files=2
        application.config['General']['number_of_output_files'] = 2
        dates = []
        for d in application.dates_to_calculate:
            dates.append(d)
        self.assertEquals(dates, [datetime(2014, 4, 30, 14, 0),
                                  datetime(2014, 4, 30, 15, 0)])

        # Check for number_of_output_files=4
        application.config['General']['number_of_output_files'] = 4
        dates = []
        for d in application.dates_to_calculate:
            dates.append(d)
        self.assertEquals(dates, [datetime(2014, 4, 30, 12, 0),
                                  datetime(2014, 4, 30, 13, 0),
                                  datetime(2014, 4, 30, 14, 0),
                                  datetime(2014, 4, 30, 15, 0)])

    def test_dates_to_calculate_error1(self):
        application = SpatializeApp()
        application.read_command_line()
        application.read_configuration()
        with open(self.filenames[0], 'w') as f:
            f.write(textwrap.dedent('''\
                2014-04-30 11:00,18.3,
                malformed date,20.4,
                2014-04-30 14:00,21.4,
                2014-04-30 15:00,22.4,
                '''))
        with open(self.filenames[1], 'w') as f:
            f.write(textwrap.dedent('''\
                2014-04-30 11:00,18.3,
                2014-04-30 12:00,19.3,
                2014-04-30 13:00,20.4,
                2014-04-30 14:00,21.4,
                '''))
        error_message = r"^Unable to parse date string u?'malformed date' " \
            r"\(file " + self.filenames[0] + ", 3 lines from the end\)$"
        six.assertRaisesRegex(self, iso8601.ParseError, error_message,
                              six.next, application.dates_to_calculate)

    def test_dates_to_calculate_error2(self):
        application = SpatializeApp()
        application.read_command_line()
        application.read_configuration()
        with open(self.filenames[0], 'w') as f:
            f.write(textwrap.dedent('''\
                2014-04-30 11:00,18.3,
                2014-04-30 13:00,20.4,
                2014-04-30 14:00,21.4,
                2014-04-30 15:00,22.4,
                '''))
        with open(self.filenames[1], 'w') as f:
            f.write(textwrap.dedent('''\
                Time_step=60,0
                Timestamp_rounding=0,0
                Timestamp_offset=0,0
                2014-04-30 11:00,18.3,
                2014-04-30 12:00,19.3,
                2014-04-30 13:00,20.4,
                2014-04-30 14:00,21.4,
                '''))
        error_message = r"^Unable to parse date string " \
            r"u?'Timestamp_offset=0' " \
            r"\(file " + self.filenames[1] + ", 5 lines from the end\)$"
        six.assertRaisesRegex(self, iso8601.ParseError, error_message,
                              six.next, application.dates_to_calculate)

    def test_date_fmt(self):
        application = SpatializeApp()
        application.read_command_line()
        application.read_configuration()

        # Ten-minute
        with open(application.files[0], 'w') as f:
            f.write('Time_step=10,0\n\n')
        with open(application.files[1], 'w') as f:
            f.write('Time_step=10,0\n\n')
        self.assertEquals(application.date_fmt, '%Y-%m-%d %H:%M%z')

        # Hourly
        with open(application.files[0], 'w') as f:
            f.write('Time_step=60,0\n\n')
        with open(application.files[1], 'w') as f:
            f.write('Time_step=60,0\n\n')
        self.assertEquals(application.date_fmt, '%Y-%m-%d %H:%M%z')

        # Daily
        with open(application.files[0], 'w') as f:
            f.write('Time_step=1440,0\n\n')
        with open(application.files[1], 'w') as f:
            f.write('Time_step=1440,0\n\n')
        self.assertEquals(application.date_fmt, '%Y-%m-%d')

        # Monthly
        with open(application.files[0], 'w') as f:
            f.write('Time_step=0,1\n\n')
        with open(application.files[1], 'w') as f:
            f.write('Time_step=0,1\n\n')
        self.assertEquals(application.date_fmt, '%Y-%m')

        # Annual
        with open(application.files[0], 'w') as f:
            f.write('Time_step=0,12\n\n')
        with open(application.files[1], 'w') as f:
            f.write('Time_step=0,12\n\n')
        self.assertEquals(application.date_fmt, '%Y')

        # Inconsistent
        with open(application.files[0], 'w') as f:
            f.write('Time_step=10,0\n\n')
        with open(application.files[1], 'w') as f:
            f.write('Time_step=60,0\n\n')
        self.assertRaises(WrongValueError, lambda: application.date_fmt)

    def test_delete_obsolete_files(self):
        application = SpatializeApp()
        application.read_command_line()
        application.read_configuration()

        # Create three files
        prefix = application.config['General']['filename_prefix']
        filename1 = os.path.join(self.output_dir, '{}-1.tif'.format(prefix))
        filename2 = os.path.join(self.output_dir, '{}-2.tif'.format(prefix))
        filename3 = os.path.join(self.output_dir, '{}-3.tif'.format(prefix))
        with open(filename1, 'w'):
            pass
        with open(filename2, 'w'):
            pass
        with open(filename3, 'w'):
            pass

        # Just to make sure we didn't screw up above, check
        self.assertTrue(os.path.exists(filename1))
        self.assertTrue(os.path.exists(filename2))
        self.assertTrue(os.path.exists(filename3))

        # Execute for number_of_output_files = 2 and check
        application.config['General']['number_of_output_files'] = 2
        application.delete_obsolete_files()
        self.assertFalse(os.path.exists(filename1))
        self.assertTrue(os.path.exists(filename2))
        self.assertTrue(os.path.exists(filename3))

        # Re-execute; nothing should have changed
        application.delete_obsolete_files()
        self.assertFalse(os.path.exists(filename1))
        self.assertTrue(os.path.exists(filename2))
        self.assertTrue(os.path.exists(filename3))

    def test_execute(self):
        application = SpatializeApp()
        application.read_command_line()
        application.read_configuration()
        application.setup_logger()

        # Create some time series data
        with open(application.files[0], 'a') as f:
            f.write(textwrap.dedent('''\
                2014-04-30 11:00,18.3,
                2014-04-30 13:00,20.4,
                2014-04-30 14:00,21.4,
                2014-04-30 15:00,22.4,
                '''))
        with open(application.files[1], 'a') as f:
            f.write(textwrap.dedent('''\
                2014-04-30 11:00,18.3,
                2014-04-30 12:00,19.3,
                2014-04-30 13:00,20.4,
                2014-04-30 14:00,21.4,
                '''))

        # Create a mask
        mask_filename = os.path.join(self.tempdir, 'mask.tif')
        mask = gdal.GetDriverByName('GTiff').Create(mask_filename, 640, 480, 1,
                                                    gdal.GDT_Float32)
        mask.SetGeoTransform((23, 0.01, 0, 39, 0, -0.01))
        mask.SetProjection(
            'GEOGCS["WGS 84",DATUM["WGS_1984",SPHEROID["WGS 84",6378137,'
            '298.257223563,AUTHORITY["EPSG","7030"]],AUTHORITY["EPSG","6326"'
            ']],PRIMEM["Greenwich",0,AUTHORITY["EPSG","8901"]],UNIT["degree",'
            '0.01745329251994328,AUTHORITY["EPSG","9122"]],AUTHORITY["EPSG",'
            '"4326"]]')
        mask = None

        # Execute
        application.config['General']['number_of_output_files'] = 3
        application.execute()

        # Check that it has created three files
        full_prefix = os.path.join(
            self.output_dir,
            application.config['General']['filename_prefix'])
        self.assertTrue(os.path.exists(
            full_prefix + '-2014-04-30-15-00+0200.tif'))
        self.assertTrue(os.path.exists(
            full_prefix + '-2014-04-30-14-00+0200.tif'))
        self.assertTrue(os.path.exists(
            full_prefix + '-2014-04-30-13-00+0200.tif'))

        # Check the timestamp in the last file
        fp = gdal.Open(full_prefix + '-2014-04-30-15-00+0200.tif')
        timestamp = fp.GetMetadata()['TIMESTAMP']
        fp = None
        self.assertEqual(timestamp, '2014-04-30 15:00+0200')

        # We could check a myriad other things here, but since we've
        # unit-tested lower level functions in detail, the above is reasonably
        # sufficient for us to know that it works.
