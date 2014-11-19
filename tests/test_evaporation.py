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

from pthelma.evaporation import VaporizeApp, PenmanMonteith


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


class PenmanMonteithTestCase(TestCase):

    def test_2_dates_scalar_with_single_albedo(self):
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

    def test_1_date_array_with_single_albedo(self):
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

    def test_1_date_scalar_with_albedo_scalar_array(self):
        # Apply Allen et al. (1998) Example 19 page 75.
        pm = PenmanMonteith(albedo=np.array([0.23]),
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
        # The following two lines could be written more simply like this:
        #     self.assertAlmostEqual(result, 0.63, places=2)
        # However, it does not work properly on Python 3 because of a numpy
        # issue.
        self.assertEqual(result.size, 1)
        self.assertAlmostEqual(result[0], 0.63, places=2)

    def test_1_date_array_with_seasonal_albedo_array(self):
        # We use a 2x1 grid, where point 1, 1 is the same as Example 19, and
        # point 1, 2 has some different values.
        pm = PenmanMonteith(albedo=[np.array([0.23, 0.23])
                                    for item in range(1, 13)],
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

    def test_3_dates_to_confirm_month_selection_in_seasonal_albedo(self):
        # Apply Allen et al. (1998) Example 19 page 75.

        pm = PenmanMonteith(albedo=[0.13, 0.01, 0.01, 0.01, 0.01, 0.01,
                                    0.01, 0.01, 0.01, 0.23, 0.01, 0.33],
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
                              adatetime=datetime(2014, 1, 1, 15, 0,
                                                 tzinfo=senegal_tzinfo))
        self.assertAlmostEqual(result, 0.69, places=2)

        result = pm.calculate(temperature=38,
                              humidity=52,
                              wind_speed=3.3,
                              pressure=101.3,
                              solar_radiation=2.450,
                              adatetime=datetime(2014, 12, 1, 15, 0,
                                                 tzinfo=senegal_tzinfo))
        self.assertAlmostEqual(result, 0.56, places=2)

        result = pm.calculate(temperature=38,
                              humidity=52,
                              wind_speed=3.3,
                              pressure=101.3,
                              solar_radiation=2.450,
                              adatetime=datetime(2014, 10, 1, 15, 0,
                                                 tzinfo=senegal_tzinfo))
        self.assertAlmostEqual(result, 0.63, places=2)


class VaporizeAppTestCase(TestCase):

    def __init__(self, *args, **kwargs):
        super(VaporizeAppTestCase, self).__init__(*args, **kwargs)

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
        filename = os.path.join(self.tempdir, variable + '-' +
                                self.timestamp.strftime('%Y-%m-%d-%H-%M%z') +
                                '.tif')
        f = gdal.GetDriverByName('GTiff').Create(
            filename, 2, 1, 1, gdal.GDT_Float32)
        if not f:
            raise IOError('An error occured when trying to open ' + filename)
        try:
            f.SetMetadataItem('TIMESTAMP', self.timestamp.isoformat())
            f.SetGeoTransform(self.geo_transform)
            f.SetProjection(self.wgs84.ExportToWkt())
            f.GetRasterBand(1).WriteArray(value)
        finally:
            # Close the dataset
            f = None

    def setup_sample_albedo_grid(self, value):
        """
        Saves a albedo geotif, which is an np array, to a GeoTIFF file
        whose name is a00.tiff.
        """
        filename = os.path.join(self.tempdir, 'a00.tif')
        f = gdal.GetDriverByName('GTiff').Create(
            filename, 2, 1, 1, gdal.GDT_Float32)
        if not f:
            raise IOError('An error occured when trying to open ' + filename)
        try:
            f.SetGeoTransform(self.geo_transform)
            f.SetProjection(self.wgs84.ExportToWkt())
            f.GetRasterBand(1).WriteArray(value)
        finally:
            # Close the dataset
            f = None

    def setUp(self):
        self.tempdir = tempfile.mkdtemp()
        self.config_file = os.path.join(self.tempdir, 'vaporize.conf')
        self.saved_argv = copy(sys.argv)
        sys.argv = ['vaporize', '--traceback', self.config_file]
        self.savedcwd = os.getcwd()

        # Prepare data common to all input files
        self.geo_transform = (-16.25, 1.0, 0, 16.217, 0, 1.0)
        self.wgs84 = osr.SpatialReference()
        self.wgs84.ImportFromEPSG(4326)

        # Prepare sample albedo grid
        self.setup_sample_albedo_grid(np.array([[0.23, 0.44]]))

    def tearDown(self):
        os.chdir(self.savedcwd)
        shutil.rmtree(self.tempdir)
        sys.argv = copy(self.saved_argv)

    def test_correct_configuration(self):
        with open(self.config_file, 'w') as f:
            f.write(textwrap.dedent('''\
                base_dir = {self.tempdir}
                albedo = 0.23
                nighttime_solar_radiation_ratio = 0.8
                elevation = 8
                step_length = 60
                unit_converter_pressure = x / 10.0
                unit_converter_solar_radiation = x * 3600 / 1e6
                ''').format(self=self))
        application = VaporizeApp()
        application.run(dry=True)

    def test_wrong_configuration(self):
        # Missing step_length
        with open(self.config_file, 'w') as f:
            f.write(textwrap.dedent('''\
                base_dir = {self.tempdir}
                albedo = 0.23
                nighttime_solar_radiation_ratio = 0.8
                elevation = 8
                ''').format(self=self))
        application = VaporizeApp()
        self.assertRaisesRegex(configparser.Error, 'step_length',
                               application.run)

        # Missing albedo
        with open(self.config_file, 'w') as f:
            f.write(textwrap.dedent('''\
                base_dir = {self.tempdir}
                nighttime_solar_radiation_ratio = 0.8
                elevation = 8
                step_length = 60
                ''').format(self=self))
        application = VaporizeApp()
        self.assertRaisesRegex(configparser.Error, 'albedo',
                               application.run)

        # Missing elevation
        with open(self.config_file, 'w') as f:
            f.write(textwrap.dedent('''\
                base_dir = {self.tempdir}
                albedo = 0.23
                nighttime_solar_radiation_ratio = 0.8
                step_length = 60
                ''').format(self=self))
        application = VaporizeApp()
        self.assertRaisesRegex(configparser.Error, 'elevation',
                               application.run)

        # Missing nighttime_solar_radiation_ratio
        with open(self.config_file, 'w') as f:
            f.write(textwrap.dedent('''\
                base_dir = {self.tempdir}
                albedo = 0.23
                elevation = 8
                step_length = 60
                ''').format(self=self))
        application = VaporizeApp()
        self.assertRaisesRegex(configparser.Error,
                               'nighttime_solar_radiation_ratio',
                               application.run)

    def test_execute_notz(self):
        # Prepare input files without time zone
        self.timestamp = datetime(2014, 10, 1, 15, 0)
        self.setup_input_file('temperature-notz', np.array([[38, 28]]))
        self.setup_input_file('humidity-notz', np.array([[52, 42]]))
        self.setup_input_file('wind_speed-notz', np.array([[3.3, 2.3]]))
        self.setup_input_file('pressure-notz', np.array([[1013, 1013]]))
        self.setup_input_file('solar_radiation-notz', np.array([[681, 403]]))

        with open(self.config_file, 'w') as f:
            f.write(textwrap.dedent('''\
                base_dir = {self.tempdir}
                albedo = 0.23
                nighttime_solar_radiation_ratio = 0.8
                elevation = 8
                step_length = 60
                unit_converter_pressure = x / 10.0
                unit_converter_solar_radiation = x * 3600 / 1e6
                temperature_prefix = temperature-notz
                humidity_prefix = humidity-notz
                wind_speed_prefix = wind_speed-notz
                solar_radiation_prefix = solar_radiation-notz
                pressure_prefix = pressure-notz
                ''').format(self=self))

        application = VaporizeApp()
        application.read_command_line()
        application.read_configuration()

        # Verify the output file doesn't exist yet
        result_filename = os.path.join(
            self.tempdir, 'evaporation-{}.tif'.format(
                self.timestamp.strftime('%Y-%m-%d-%H-%M%z')))
        self.assertFalse(os.path.exists(result_filename))

        # Execute
        self.assertRaisesRegex(Exception, 'time zone', application.run)

        # Verify the output file still doesn't exist
        self.assertFalse(os.path.exists(result_filename))

    def test_execute(self):
        # Prepare input files
        self.timestamp = datetime(2014, 10, 1, 15, 0, tzinfo=senegal_tzinfo)
        self.setup_input_file('temperature', np.array([[38, 28]]))
        self.setup_input_file('humidity', np.array([[52, 42]]))
        self.setup_input_file('wind_speed', np.array([[3.3, 2.3]]))
        self.setup_input_file('pressure', np.array([[1013, 1013]]))
        self.setup_input_file('solar_radiation', np.array([[681, 403]]))

        # Also setup an output file that has no corresponding input files
        rogue_output_file = os.path.join(
            self.tempdir, 'evaporation-2013-01-01-15-00-0100.tif')
        with open(rogue_output_file, 'w') as f:
            f.write('irrelevant contents')

        with open(self.config_file, 'w') as f:
            f.write(textwrap.dedent('''\
                base_dir = {self.tempdir}
                albedo = 0.23
                nighttime_solar_radiation_ratio = 0.8
                elevation = 8
                step_length = 60
                unit_converter_pressure = x / 10.0
                unit_converter_solar_radiation = x * 3600 / 1e6
                ''').format(self=self))
        application = VaporizeApp()
        application.read_command_line()
        application.read_configuration()

        # Verify the output file doesn't exist yet
        result_filename = os.path.join(
            self.tempdir, 'evaporation-{}.tif'.format(
                self.timestamp.strftime('%Y-%m-%d-%H-%M%z')))
        self.assertFalse(os.path.exists(result_filename))

        # Verify the rogue output file is still here
        self.assertTrue(os.path.exists(rogue_output_file))

        # Execute
        application.run()

        # Check that it has created a file
        self.assertTrue(os.path.exists(result_filename))

        # Check that the rogue output file is gone
        self.assertFalse(os.path.exists(rogue_output_file))

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

    def test_albedo_configuration_as_one_number(self):
        with open(self.config_file, 'w') as f:
            f.write(textwrap.dedent('''\
                base_dir = {self.tempdir}
                step_length = 60
                albedo = 0.23
                nighttime_solar_radiation_ratio = 0.8
                elevation = 8
                ''').format(self=self))
        application = VaporizeApp()
        application.run(dry=True)

    def test_albedo_configuration_as_one_grid(self):
        with open(self.config_file, 'w') as f:
            f.write(textwrap.dedent('''\
                base_dir = {self.tempdir}
                step_length = 60
                albedo = a0.tif
                nighttime_solar_radiation_ratio = 0.8
                elevation = 8
                ''').format(self=self))
        application = VaporizeApp()
        self.assertRaises(IOError, application.run, self)

    def test_single_albedo_with_wrong_domain_float_inputs(self):
        with open(self.config_file, 'w') as f:
            f.write(textwrap.dedent('''\
                base_dir = {self.tempdir}
                step_length = 60
                albedo = 2
                nighttime_solar_radiation_ratio = 0.8
                elevation = 8
                ''').format(self=self))
        application = VaporizeApp()
        self.assertRaises(ValueError, application.run, self)

    def test_seasonal_albedo_configuration_as_12_numbers(self):
        with open(self.config_file, 'w') as f:
            f.write(textwrap.dedent('''\
                base_dir = {self.tempdir}
                step_length = 60
                albedo = 0.10 0.23 0.34 0.24 0.45 0.46
                         0.34 0.12 0.14 0.78 0.78 0.12
                nighttime_solar_radiation_ratio = 0.8
                elevation = 8
                ''').format(self=self))
        application = VaporizeApp()
        application.run(dry=True)

    def test_seasonal_albedo_configuration_as_12_grids(self):
        with open(self.config_file, 'w') as f:
            f.write(textwrap.dedent('''\
                base_dir = {self.tempdir}
                step_length = 60
                albedo = a01.tif a02.tif a03.tif a04.tif a05.tif a06.tif
                         a07.tif a08.tif a09.tif a10.tif a11.tif a12.tif
                nighttime_solar_radiation_ratio = 0.8
                elevation = 8
                ''').format(self=self))
        application = VaporizeApp()
        self.assertRaises(IOError, application.run, self)

    def test_seasonal_albedo_configuration_as_mix_numbers_and_grids(self):
        with open(self.config_file, 'w') as f:
            f.write(textwrap.dedent('''\
                base_dir = {self.tempdir}
                step_length = 60
                albedo = 0.23 a02.tif a03.tif a04.tif a05.tif a06.tif
                         a07.tif a08.tif a09.tiff a10.tif a11.tif a12.tif
                nighttime_solar_radiation_ratio = 0.8
                elevation = 8
                ''').format(self=self))
        application = VaporizeApp()
        self.assertRaises(IOError, application.run, self)

    def test_seasonal_albedo_configuration_with_not_enough_arguments(self):
        with open(self.config_file, 'w') as f:
            f.write(textwrap.dedent('''\
                base_dir = {self.tempdir}
                step_length = 60
                albedo = a01.tiff a02.tiff a11.tiff a12.tiff
                nighttime_solar_radiation_ratio = 0.8
                elevation = 8
                ''').format(self=self))
        application = VaporizeApp()
        self.assertRaises(ValueError, application.run, self)

    def test_seasonal_albedo_with_wrong_domain_mixin_inputs(self):
        with open(self.config_file, 'w') as f:
            f.write(textwrap.dedent('''\
                base_dir = {self.tempdir}
                step_length = 60
                albedo = 1 2 0.34 0.24 0.45 0.4
                        0.34 0.12 a00.tif 0.78 0.78 2
                nighttime_solar_radiation_ratio = 0.8
                elevation = 8
                ''').format(self=self))
        application = VaporizeApp()
        self.assertRaises(ValueError, application.run, self)

    def test_run_app_seasonal_albedo_with_float_sample_inputs(self):
        with open(self.config_file, 'w') as f:
            f.write(textwrap.dedent('''\
                base_dir = {self.tempdir}
                step_length = 60
                albedo = 0.10 0.23 0.34 0.24 0.45 0.46
                         0.34 0.12 0.14 0.78 0.78 0.12
                nighttime_solar_radiation_ratio = 0.8
                elevation = 8
                ''').format(self=self))

        application = VaporizeApp()
        application.run(dry=True)

    def test_run_app_with_seasonal_albedo_with_grid_sample_inputs(self):
        with open(self.config_file, 'w') as f:
            f.write(textwrap.dedent('''\
                base_dir = {self.tempdir}
                step_length = 60
                albedo = a00.tif a00.tif a00.tif a00.tif a00.tif a00.tif
                         a00.tif a00.tif a00.tif a00.tif a00.tif a00.tif
                nighttime_solar_radiation_ratio = 0.8
                elevation = 8
                ''').format(self=self))

        application = VaporizeApp()
        application.run(dry=True)

    def test_run_app_with_seasonal_albedo_with_mix_sample_inputs(self):
        with open(self.config_file, 'w') as f:
            f.write(textwrap.dedent('''\
                base_dir = {self.tempdir}
                step_length = 60
                albedo = a00.tif 0.23 a00.tif a00.tif a00.tif a00.tif
                         a00.tif a00.tif 0.23 a00.tif 0.23 a00.tif
                nighttime_solar_radiation_ratio = 0.8
                elevation = 8
                ''').format(self=self))

        application = VaporizeApp()
        application.run(dry=True)
