from datetime import datetime
import os
import shutil
from six.moves import configparser
import sys
import tempfile
import textwrap
from unittest import TestCase, skipIf

if sys.platform != 'win32':
    import numpy as np
    from osgeo import ogr, gdal
    from pthelma.spatial import BitiaApp, create_ogr_layer_from_timeseries, \
        h_integrate, idw, integrate, WrongValueError
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

        # All masked points and only those must be NaN
        # (^ is bitwise xor in Python)
        self.assertTrue((np.isnan(result) ^ (self.mask != 0)).all())

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
            f.write("Location=19.55729 0.04733 2100\n"  # GGRS87=5000 5000
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
        h_integrate(mask=self.mask,
                    stations_layer=self.stations_layer,
                    date=datetime(2014, 4, 22, 13, 0),
                    output_filename=os.path.join(self.tempdir, 'test.tif'),
                    date_fmt='%Y-%m-%d %H:%M', funct=idw, kwargs={})
        f = gdal.Open(os.path.join(self.tempdir, 'test.tif'))
        result = f.GetRasterBand(1).ReadAsArray()
        expected_result = np.array([[1.5088, 1.6064, np.nan, 1.7237],
                                    [1.3828, 1.6671, 1.7336, 1.7662],
                                    [0.5400, 2.4000, 1.7954, 1.7504]])
        np.testing.assert_almost_equal(result, expected_result, decimal=4)


@skipIf(skip_osgeo, skip_osgeo_message)
class BitiaAppTestCase(TestCase):

    def __init__(self, *args, **kwargs):
        super(BitiaAppTestCase, self).__init__(*args, **kwargs)

        # Python 2.7 compatibility
        try:
            self.assertRaisesRegex
        except AttributeError:
            self.assertRaisesRegex = self.assertRaisesRegexp

    def setUp(self):
        self.tempdir = tempfile.mkdtemp()
        self.output_dir = os.path.join(self.tempdir, 'output')
        self.config_file = os.path.join(self.tempdir, 'bitia.conf')
        os.mkdir(self.output_dir)
        self.mask_file = os.path.join(self.tempdir, 'mask.tif')
        self.saved_argv = sys.argv
        sys.argv = ['bitia', '--traceback', self.config_file]

        # Create two time series
        self.filenames = [os.path.join(self.tempdir, x)
                          for x in ('ts1', 'ts2')]
        with open(self.filenames[0], 'w') as f:
            f.write("Location=23.78743 37.97385 4326\n"
                    "Time_step=60,0\n"
                    "\n")
        with open(self.filenames[1], 'w') as f:
            f.write("Location=24.56789 38.76543 4326\n"
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
                files_to_produce = 24
                method = idw
                files = {0.filenames[0]}
                        {0.filenames[1]}
                ''').format(self))

    def tearDown(self):
        shutil.rmtree(self.tempdir)
        sys.argv = self.saved_argv

    def test_correct_configuration(self):
        application = BitiaApp()
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
        application = BitiaApp()
        self.assertRaisesRegex(configparser.Error, 'files_to_produce',
                               application.run)

    def test_wrong_configuration2(self):
        with open(self.config_file, 'w') as f:
            f.write(textwrap.dedent('''\
                [General]
                mask = {0.mask_file}
                epsg = 2100
                output_dir = {0.output_dir}
                filename_prefix = rainfall
                files_to_produce = 24
                method = idw
                files = myfile
                nonexistent_option = irrelevant
                ''').format(self))
        application = BitiaApp()
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
                files_to_produce = 24
                method = idw
                files = myfile
                ''').format(self))
        application = BitiaApp()
        self.assertRaisesRegex(WrongValueError, 'epsg=81122',
                               application.run)

    def test_last_date(self):
        application = BitiaApp()
        application.read_command_line()
        application.read_configuration()
        with open(application.files[0], 'a') as f:
            f.write(textwrap.dedent('''\
                2014-04-30 11:00,18.3,
                2014-04-30 12:00,19.3,
                2014-04-30 13:00,20.4,
                2014-04-30 14:00,21.4,
                '''))
        self.assertEquals(application.last_date, datetime(2014, 4, 30, 14, 0))

    def test_date_fmt(self):
        application = BitiaApp()
        application.read_command_line()
        application.read_configuration()

        # Ten-minute
        with open(application.files[0], 'w') as f:
            f.write('Time_step=10,0\n\n')
        with open(application.files[1], 'w') as f:
            f.write('Time_step=10,0\n\n')
        self.assertEquals(application.date_fmt, '%Y-%m-%d %H:%M')

        # Hourly
        with open(application.files[0], 'w') as f:
            f.write('Time_step=60,0\n\n')
        with open(application.files[1], 'w') as f:
            f.write('Time_step=60,0\n\n')
        self.assertEquals(application.date_fmt, '%Y-%m-%d %H:%M')

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

    def get_file_timestamp(self, filename):
        fp = gdal.Open(filename)
        timestamp = fp.GetMetadata()['TIMESTAMP']
        fp = None
        return timestamp

    def create_file_with_timestamp(self, filename, timestamp):
        output = gdal.GetDriverByName('GTiff').Create(filename, 640, 480, 1,
                                                      gdal.GDT_Float32)
        if not output:
            raise IOError('Could not create ' + filename)
        output.SetMetadataItem('TIMESTAMP', timestamp)
        output = None

    def test_rename_existing_files(self):
        application = BitiaApp()
        application.read_command_line()
        application.read_configuration()

        # Annual time step
        for filename in application.files:
            with open(filename, 'w') as f:
                f.write('Time_step=0,12\n\n')

        # Create three files
        prefix = application.config['General']['filename_prefix']
        filename1 = os.path.join(self.output_dir, '{}-0000.tif'.format(prefix))
        filename2 = os.path.join(self.output_dir, '{}-0001.tif'.format(prefix))
        filename3 = os.path.join(self.output_dir, '{}-0002.tif'.format(prefix))
        self.create_file_with_timestamp(filename1, '2014')
        self.create_file_with_timestamp(filename2, '2013')
        self.create_file_with_timestamp(filename3, '2012')

        # Just to make sure we didn't screw up above, check
        self.assertTrue(os.path.exists(filename1))
        self.assertTrue(os.path.exists(filename2))
        self.assertTrue(os.path.exists(filename3))

        # Execute for files_to_produce = 3 and check
        application.config['General']['files_to_produce'] = 3
        application.rename_existing_files('2015')
        self.assertFalse(os.path.exists(filename1))
        self.assertEquals(self.get_file_timestamp(filename2), '2014')
        self.assertEquals(self.get_file_timestamp(filename3), '2013')
        self.assertEquals(len(os.listdir(self.output_dir)), 2)

        # Re-execute; nothing should have changed
        application.rename_existing_files('2015')
        self.assertFalse(os.path.exists(filename1))
        self.assertEquals(self.get_file_timestamp(filename2), '2014')
        self.assertEquals(self.get_file_timestamp(filename3), '2013')
        self.assertEquals(len(os.listdir(self.output_dir)), 2)

    def test_execute(self):
        application = BitiaApp()
        application.read_command_line()
        application.read_configuration()

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
        gdal.GetDriverByName('GTiff').Create(mask_filename, 640, 480, 1,
                                             gdal.GDT_Float32)

        # Execute
        application.config['General']['files_to_produce'] = 3
        application.execute()

        # Check that it has created three files
        full_prefix = os.path.join(
            self.output_dir,
            application.config['General']['filename_prefix'])
        self.assertTrue(os.path.exists(full_prefix + '-0000.tif'))
        self.assertTrue(os.path.exists(full_prefix + '-0001.tif'))
        self.assertTrue(os.path.exists(full_prefix + '-0002.tif'))

        # We could check a myriad other things here, but since we've
        # unit-tested lower level functions in detail, the above is reasonably
        # sufficient for us to know that it works.
