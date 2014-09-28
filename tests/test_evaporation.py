from copy import copy
from datetime import datetime, timedelta, tzinfo
import os
import shutil
from six.moves import configparser
import sys
import tempfile
import textwrap
from unittest import TestCase

import numpy as np
from osgeo import gdal, osr

from pthelma.evaporation import GerardaApp, PenmanMonteith
#from pthelma.evaporation import get_number_or_grid

class SenegalTzinfo(tzinfo):
    """
    At various places we test using Example 19, p. 75, of Allen et al. (1998).
    The example calculates evaporation in Senegal.  Although Senegal has time
    Afrika/Dakar, which is the same as UTC, Example 19 apparently assumes that
    its time zone is actually UTC-01:00 (which would be more consistent with
    its longitude, which may be the reason for the error).  So we make the same
    assumption as example 19, in order to get the same result.
    """

    def utcoffset(self, dt):
        return -timedelta(hours=1)

    def dst(self, dt):
        return timedelta(0)


senegal_tzinfo = SenegalTzinfo()


class PenmanMonteithTest(TestCase):

    def test_point(self):
        # Apply Allen et al. (1998) Example 19 page 75.
        pm = PenmanMonteith(albedo=0.23,
                            nighttime_solar_radiation_ratio=0.8,
                            elevation=8,
                            latitude=16.217,
                            longitude=-16.25,
                            step_length=timedelta(hours=1)
                            )

        result = pm.calculate(temperature=38,
                              humidity=52,
                              wind_speed=3.3,
                              pressure=101.3,
                              solar_radiation=2.450,
                              adatetime=datetime(2014, 10, 1, 15, 0,
                                                 tzinfo=senegal_tzinfo))
        self.assertAlmostEqual(result, 0.63, places=2)
        result = pm.calculate(temperature=28,
                              humidity=90,
                              wind_speed=1.9,
                              pressure=101.3,
                              solar_radiation=0,
                              adatetime=datetime(2014, 10, 1, 2, 30,
                                                 tzinfo=senegal_tzinfo))
        self.assertAlmostEqual(result, 0.0, places=2)

    def test_grid(self):
        # We use a 2x1 grid, where point 1, 1 is the same as Example 19, and
        # point 1, 2 has some different values.
        pm = PenmanMonteith(albedo=0.23,
                            nighttime_solar_radiation_ratio=0.8,
                            elevation=8,
                            latitude=16.217,
                            longitude=np.array([-16.25, -15.25]),
                            step_length=timedelta(hours=1)
                            )
        result = pm.calculate(temperature=np.array([38, 28]),
                              humidity=np.array([52, 42]),
                              wind_speed=np.array([3.3, 2.3]),
                              pressure=101.3,
                              solar_radiation=np.array([2.450, 1.450]),
                              adatetime=datetime(2014, 10, 1, 15, 0,
                                                 tzinfo=senegal_tzinfo))
        np.testing.assert_almost_equal(result, np.array([0.63, 0.36]),
                                       decimal=2)

class GerardaAppTestCase(TestCase):

    def __init__(self, *args, **kwargs):
        super(GerardaAppTestCase, self).__init__(*args, **kwargs)

        # Python 2.7 compatibility
        try:
            self.assertRaisesRegex
        except AttributeError:
            self.assertRaisesRegex = self.assertRaisesRegexp

    def setup_input_file(self, variable, value):
        """
        Saves value, which is an np array, to a GeoTIFF file whose name is
        based on variable.
        """
        filename = os.path.join(self.tempdir, variable + '-0001.tif')
        f = gdal.GetDriverByName('GTiff').Create(
            filename, 2, 1, 1, gdal.GDT_Float32)
        if not f:
            raise IOError('An error occured when trying to open ' + filename)
        try:
            f.SetMetadataItem('TIMESTAMP', self.timestamp)
            f.SetGeoTransform(self.geo_transform)
            f.SetProjection(self.wgs84.ExportToWkt())
            f.GetRasterBand(1).WriteArray(value)
        finally:
            # Close the dataset
            f = None

    def setUp(self):
        self.tempdir = tempfile.mkdtemp()
        self.config_file = os.path.join(self.tempdir, 'gerarda.conf')
        self.saved_argv = copy(sys.argv)
        sys.argv = ['gerarda', '--traceback', self.config_file]
        self.savedcwd = os.getcwd()

        # Prepare data common to all input files
        self.timestamp = datetime(2014, 10, 1, 15, 0, tzinfo=senegal_tzinfo
                                  ).isoformat()
        self.geo_transform = (-16.25, 1.0, 0, 16.217, 0, 1.0)
        self.wgs84 = osr.SpatialReference()
        self.wgs84.ImportFromEPSG(4326)

        # Prepare input files
        self.setup_input_file('temperature', np.array([[38, 28]]))
        self.setup_input_file('humidity', np.array([[52, 42]]))
        self.setup_input_file('wind_speed', np.array([[3.3, 2.3]]))
        self.setup_input_file('pressure', np.array([[1013, 1013]]))
        self.setup_input_file('solar_radiation', np.array([[681, 403]]))

        # Also prepare input files without time zone, to test an error
        # condition.
        self.timestamp = datetime(2014, 10, 1, 15, 0).isoformat()
        self.setup_input_file('temperature-notz', np.array([[38, 28]]))
        self.setup_input_file('humidity-notz', np.array([[52, 42]]))
        self.setup_input_file('wind_speed-notz', np.array([[3.3, 2.3]]))
        self.setup_input_file('pressure-notz', np.array([[1013, 1013]]))
        self.setup_input_file('solar_radiation-notz', np.array([[681, 403]]))

        # Prepare a configuration file (some tests override it)
        with open(self.config_file, 'w') as f:
            f.write(textwrap.dedent('''\
                [General]
                base_dir = {self.tempdir}
                albedo = 0.23
                nighttime_solar_radiation_ratio = 0.8
                elevation = 8
                step_length = 60
                unit_converter_pressure = x / 10.0
                unit_converter_solar_radiation = x * 3600 / 1e6

                [Last]
                temperature = temperature-0001.tif
                humidity = humidity-0001.tif
                wind_speed = wind_speed-0001.tif
                pressure = pressure-0001.tif
                solar_radiation = solar_radiation-0001.tif
                result = evaporation-0001.tif
                ''').format(self=self))

    def tearDown(self):
        os.chdir(self.savedcwd)
        shutil.rmtree(self.tempdir)
        sys.argv = copy(self.saved_argv)

    def test_correct_configuration(self):
        application = GerardaApp()
        application.run(dry=True)

    def test_wrong_configuration(self):
        # Missing step_length
        with open(self.config_file, 'w') as f:
            f.write(textwrap.dedent('''\
                [General]
                base_dir = {self.tempdir}
                albedo = 0.23
                nighttime_solar_radiation_ratio = 0.8
                elevation = 8
                ''').format(self=self))
        application = GerardaApp()
        self.assertRaisesRegex(configparser.Error, 'step_length',
                               application.run)

        # Missing albedo
        with open(self.config_file, 'w') as f:
            f.write(textwrap.dedent('''\
                [General]
                base_dir = {self.tempdir}
                nighttime_solar_radiation_ratio = 0.8
                elevation = 8
                step_length = 60
                ''').format(self=self))
        application = GerardaApp()
        self.assertRaisesRegex(configparser.Error, 'albedo',
                               application.run)

        # Missing elevation
        with open(self.config_file, 'w') as f:
            f.write(textwrap.dedent('''\
                [General]
                base_dir = {self.tempdir}
                albedo = 0.23
                nighttime_solar_radiation_ratio = 0.8
                step_length = 60
                ''').format(self=self))
        application = GerardaApp()
        self.assertRaisesRegex(configparser.Error, 'elevation',
                               application.run)

        # Missing nighttime_solar_radiation_ratio
        with open(self.config_file, 'w') as f:
            f.write(textwrap.dedent('''\
                [General]
                base_dir = {self.tempdir}
                albedo = 0.23
                elevation = 8
                step_length = 60
                ''').format(self=self))
        application = GerardaApp()
        self.assertRaisesRegex(configparser.Error,
                               'nighttime_solar_radiation_ratio',
                               application.run)

    def test_albedo_configuration_as_one_number(self):
        with open(self.config_file, 'w') as f:
            f.write(textwrap.dedent('''\
                [General]
                base_dir = {self.tempdir}
                step_length = 60
                albedo = 0.23
                nighttime_solar_radiation_ratio = 0.8
                elevation = 8

                [Last]
                temperature = temperature-0001.tif
                humidity = humidity-0001.tif
                wind_speed = wind_speed-0001.tif
                pressure = pressure-0001.tif
                solar_radiation = solar_radiation-0001.tif
                result = evaporation-0001.tif
                ''').format(self=self))
        application = GerardaApp()      
        application.run(dry=True)

    def test_albedo_configuration_as_one_grid(self):
        with open(self.config_file, 'w') as f:
            f.write(textwrap.dedent('''\
                [General]
                base_dir = {self.tempdir}
                step_length = 60
                albedo = a00.tiff
                nighttime_solar_radiation_ratio = 0.8
                elevation = 8

                [Last]
                temperature = temperature-0001.tif
                humidity = humidity-0001.tif
                wind_speed = wind_speed-0001.tif
                pressure = pressure-0001.tif
                solar_radiation = solar_radiation-0001.tif
                result = evaporation-0001.tif
                ''').format(self=self))
        application = GerardaApp()
        #self.assertRaises(IOError)
        self.assertRaises(IOError, application.run,self)
        #self.assertRaises(IOError)

    def test_seasonal_albedo_configuration_as_12_numbers(self):
        with open(self.config_file, 'w') as f:
            f.write(textwrap.dedent('''\
                [General]
                base_dir = {self.tempdir}
                step_length = 60
                albedo = 0.10 0.23 0.34 0.24 0.45 0.46 0.34 0.12 0.14 0.78 0.78 0.12
                nighttime_solar_radiation_ratio = 0.8
                elevation = 8

                [Last]
                temperature = temperature-0001.tif
                humidity = humidity-0001.tif
                wind_speed = wind_speed-0001.tif
                pressure = pressure-0001.tif
                solar_radiation = solar_radiation-0001.tif
                result = evaporation-0001.tif
                ''').format(self=self))
        application = GerardaApp()
        #self.assertRaises(IOError)
        application.run(dry = True)

    def test_seasonal_albedo_configuration_as_12_grids(self):
        with open(self.config_file, 'w') as f:
            f.write(textwrap.dedent('''\
                [General]
                base_dir = {self.tempdir}
                step_length = 60
                albedo = a01.tiff a02.tiff a03.tiff a04.tiff a05.tiff a06.tiff a07.tiff a08.tiff a09.tiff a10.tiff a11.tiff a12.tiff
                nighttime_solar_radiation_ratio = 0.8
                elevation = 8

                [Last]
                temperature = temperature-0001.tif
                humidity = humidity-0001.tif
                wind_speed = wind_speed-0001.tif
                pressure = pressure-0001.tif
                solar_radiation = solar_radiation-0001.tif
                result = evaporation-0001.tif
                ''').format(self=self))
        application = GerardaApp()
        #self.assertRaises(IOError)
        self.assertRaises(IOError, application.run,self)

    def test_seasonal_albedo_configuration_as_mix_numbers_and_grids(self):
        with open(self.config_file, 'w') as f:
            f.write(textwrap.dedent('''\
                [General]
                base_dir = {self.tempdir}
                step_length = 60
                albedo = 0.23 a02.tiff a03.tiff a04.tiff a05.tiff a06.tiff a07.tiff a08.tiff a09.tiff a10.tiff a11.tiff a12.tiff
                nighttime_solar_radiation_ratio = 0.8
                elevation = 8

                [Last]
                temperature = temperature-0001.tif
                humidity = humidity-0001.tif
                wind_speed = wind_speed-0001.tif
                pressure = pressure-0001.tif
                solar_radiation = solar_radiation-0001.tif
                result = evaporation-0001.tif
                ''').format(self=self))
        application = GerardaApp()
        self.assertRaises(IOError,application.run,self)

    def test_seasonal_albedo_configuration_with_missing_12_albedo_input_values(self):
        with open(self.config_file, 'w') as f:
            f.write(textwrap.dedent('''\
                [General]
                base_dir = {self.tempdir}
                step_length = 60
                albedo = a01.tiff a02.tiff a11.tiff a12.tiff
                nighttime_solar_radiation_ratio = 0.8
                elevation = 8

                [Last]
                temperature = temperature-0001.tif
                humidity = humidity-0001.tif
                wind_speed = wind_speed-0001.tif
                pressure = pressure-0001.tif
                solar_radiation = solar_radiation-0001.tif
                result = evaporation-0001.tif
                ''').format(self=self))
        application = GerardaApp()
        self.assertRaises(ValueError,application.run,self)

    def test_albedo_with_wrong_domain(self):
        with open(self.config_file, 'w') as f:
            f.write(textwrap.dedent('''\
                [General]
                base_dir = {self.tempdir}
                step_length = 60
                albedo = 2
                nighttime_solar_radiation_ratio = 0.8
                elevation = 8

                [Last]
                temperature = temperature-0001.tif
                humidity = humidity-0001.tif
                wind_speed = wind_speed-0001.tif
                pressure = pressure-0001.tif
                solar_radiation = solar_radiation-0001.tif
                result = evaporation-0001.tif
                ''').format(self=self))
        application = GerardaApp()
        self.assertRaises(ValueError,application.run,self)

    

    def test_execute_notz(self):
        # Use input files without time zone in TIMESTAMP
        with open(self.config_file) as f:
            config = f.read()
        config = config.replace('-0001', '-notz-0001')
        with open(self.config_file, 'w') as f:
            f.write(config)

        application = GerardaApp()
        application.read_command_line()
        application.read_configuration()

        # Verify the output file doesn't exist yet
        result_filename = os.path.join(self.tempdir, 'evaporation-0001.tif')
        self.assertFalse(os.path.exists(result_filename))

        # Execute
        self.assertRaisesRegex(Exception, 'time zone', application.run)

        # Verify the output file still doesn't exist
        self.assertFalse(os.path.exists(result_filename))

    def test_execute(self):
        application = GerardaApp()
        application.read_command_line()
        application.read_configuration()

        # Verify the output file doesn't exist yet
        result_filename = os.path.join(self.tempdir, 'evaporation-0001.tif')
        self.assertFalse(os.path.exists(result_filename))

        # Execute
        application.run()

        # Check that it has created a file
        self.assertTrue(os.path.exists(result_filename))

        # Check that the created file is correct
        fp = gdal.Open(result_filename)
        timestamp = fp.GetMetadata()['TIMESTAMP']
        self.assertEqual(timestamp, '2014-10-01T15:00:00-01:00')
        self.assertEqual(fp.RasterXSize, 2)
        self.assertEqual(fp.RasterYSize, 1)
        self.assertEqual(fp.GetGeoTransform(), self.geo_transform)
        # We can't just compare fp.GetProjection() to self.wgs84.ExportToWkt(),
        # because sometimes there are minor differences in the formatting or in
        # the information contained in the WKT.
        self.assertTrue(fp.GetProjection().startswith('GEOGCS["WGS 84",'))
        self.assertTrue(fp.GetProjection().endswith('AUTHORITY["EPSG","4326"]]'
                                                    ))
        np.testing.assert_almost_equal(fp.GetRasterBand(1).ReadAsArray(),
                                       np.array([[0.63, 0.36]]),
                                       decimal=2)
        fp = None
