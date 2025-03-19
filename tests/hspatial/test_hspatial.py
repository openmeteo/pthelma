import datetime as dt
import math
import os
import shutil
import tempfile
import textwrap
from stat import S_IREAD, S_IRGRP, S_IROTH
from time import sleep
from unittest import TestCase

import numpy as np
import pandas as pd
from django.contrib.gis.gdal import GDALRaster
from django.contrib.gis.geos import Point as GeoDjangoPoint
from osgeo import gdal, ogr, osr

import hspatial
from hspatial.test import setup_test_raster
from htimeseries import HTimeseries, TzinfoFromString

gdal.UseExceptions()

UTC_PLUS_2 = dt.timezone(dt.timedelta(hours=2))


def add_point_to_layer(layer, x, y, value):
    p = ogr.Geometry(ogr.wkbPoint)
    p.AddPoint(x, y)
    f = ogr.Feature(layer.GetLayerDefn())
    f.SetGeometry(p)
    f.SetField("value", value)
    layer.CreateFeature(f)


class IdwTestCase(TestCase):
    def setUp(self):
        self.point = ogr.Geometry(ogr.wkbPoint)
        self.point.AddPoint(5.1, 2.5)

        self.data_source = ogr.GetDriverByName("memory").CreateDataSource("tmp")
        self.data_layer = self.data_source.CreateLayer("test")
        self.data_layer.CreateField(ogr.FieldDefn("value", ogr.OFTReal))

    def tearDown(self):
        self.data_layer = None
        self.data_source = None
        self.point = None

    def test_idw_single_point(self):
        add_point_to_layer(self.data_layer, 5.3, 6.4, 42.8)
        self.assertAlmostEqual(hspatial.idw(self.point, self.data_layer), 42.8)

    def test_idw_three_points(self):
        add_point_to_layer(self.data_layer, 6.4, 7.8, 33.0)
        add_point_to_layer(self.data_layer, 9.5, 7.4, 94.0)
        add_point_to_layer(self.data_layer, 7.1, 4.9, 67.7)
        self.assertAlmostEqual(
            hspatial.idw(self.point, self.data_layer), 64.090, places=3
        )
        self.assertAlmostEqual(
            hspatial.idw(self.point, self.data_layer, alpha=2.0), 64.188, places=3
        )

    def test_idw_point_with_nan(self):
        add_point_to_layer(self.data_layer, 6.4, 7.8, 33.0)
        add_point_to_layer(self.data_layer, 9.5, 7.4, 94.0)
        add_point_to_layer(self.data_layer, 7.1, 4.9, 67.7)
        add_point_to_layer(self.data_layer, 7.2, 5.4, float("nan"))
        self.assertAlmostEqual(
            hspatial.idw(self.point, self.data_layer), 64.090, places=3
        )
        self.assertAlmostEqual(
            hspatial.idw(self.point, self.data_layer, alpha=2.0), 64.188, places=3
        )


class IntegrateTestCase(TestCase):
    # The calculations for this test have been made manually in
    # data/spatial_calculations.ods, tab test_integrate_idw.

    def setUp(self):
        # We will test on a 7x15 grid
        self.mask = np.zeros((7, 15), np.int8)
        self.mask[3, 3] = 1
        self.mask[6, 14] = 1
        self.mask[4, 13] = 1
        self.dataset = gdal.GetDriverByName("mem").Create(
            "test", 15, 7, 1, gdal.GDT_Byte
        )
        self.dataset.GetRasterBand(1).WriteArray(self.mask)

        # Prepare the result band
        self.dataset.AddBand(gdal.GDT_Float32)
        self.target_band = self.dataset.GetRasterBand(self.dataset.RasterCount)

        # Our grid represents a 70x150m area, lower-left co-ordinates (0, 0).
        self.dataset.SetGeoTransform((0, 10, 0, 70, 0, -10))

        # Now the data layer, with three points
        self.data_source = ogr.GetDriverByName("memory").CreateDataSource("tmp")
        self.data_layer = self.data_source.CreateLayer("test")
        self.data_layer.CreateField(ogr.FieldDefn("value", ogr.OFTReal))
        add_point_to_layer(self.data_layer, 75.2, 10.7, 37.4)
        add_point_to_layer(self.data_layer, 125.7, 19.0, 24.0)
        add_point_to_layer(self.data_layer, 9.8, 57.1, 95.4)

    def tearDown(self):
        self.data_source = None

    def test_integrate_idw(self):
        hspatial.integrate(
            self.dataset, self.data_layer, self.target_band, hspatial.idw
        )
        result = self.target_band.ReadAsArray()
        nodatavalue = self.target_band.GetNoDataValue()

        # All masked points and only those must be no data
        # (^ is bitwise xor in Python)
        self.assertTrue(((result == nodatavalue) ^ (self.mask != 0)).all())

        self.assertAlmostEqual(result[3, 3], 62.971, places=3)
        self.assertAlmostEqual(result[6, 14], 34.838, places=3)
        self.assertAlmostEqual(result[4, 13], 30.737, places=3)


class IntegrateWithGeoDjangoObjectsTestCase(IntegrateTestCase):
    """This is exactly the same as IntegrateTestCase, except that instead of using gdal
    objects for the mask and target_band, it uses django.contrib.gis.gdal objects."""

    def setUp(self):
        # We will test on a 7x15 grid
        self.mask = np.zeros((7, 15), np.float32)
        self.mask[3, 3] = 1
        self.mask[6, 14] = 1
        self.mask[4, 13] = 1
        self.dataset = GDALRaster(
            {
                "srid": 4326,
                "width": 15,
                "height": 7,
                "datatype": gdal.GDT_Float32,
                "bands": [{"data": self.mask}, {}],
            }
        )

        # Our grid represents a 70x150m area, lower-left co-ordinates (0, 0).
        self.dataset.geotransform = (0, 10, 0, 70, 0, -10)

        self.target_band = self.dataset.bands[1]

        # Now the data layer, with three points
        self.data_source = ogr.GetDriverByName("memory").CreateDataSource("tmp")
        self.data_layer = self.data_source.CreateLayer("test")
        self.data_layer.CreateField(ogr.FieldDefn("value", ogr.OFTReal))
        add_point_to_layer(self.data_layer, 75.2, 10.7, 37.4)
        add_point_to_layer(self.data_layer, 125.7, 19.0, 24.0)
        add_point_to_layer(self.data_layer, 9.8, 57.1, 95.4)

    def tearDown(self):
        self.data_source = None

    def test_integrate_idw(self):
        hspatial.integrate(
            self.dataset, self.data_layer, self.target_band, hspatial.idw
        )
        result = self.target_band.data()
        nodatavalue = self.target_band.nodata_value

        # All masked points and only those must be no data
        # (^ is bitwise xor in Python)
        self.assertTrue(((result == nodatavalue) ^ (self.mask != 0)).all())

        self.assertAlmostEqual(result[3, 3], 62.971, places=3)
        self.assertAlmostEqual(result[6, 14], 34.838, places=3)
        self.assertAlmostEqual(result[4, 13], 30.737, places=3)


class CreateOgrLayerFromTimeseriesTestCase(TestCase):
    def setUp(self):
        self.tempdir = tempfile.mkdtemp()

        # Create two time series
        with open(os.path.join(self.tempdir, "ts1"), "w") as f:
            f.write(
                textwrap.dedent(
                    """\
                                    Location=23.78743 37.97385 4326

                                    """
                )
            )
        with open(os.path.join(self.tempdir, "ts2"), "w") as f:
            f.write(
                textwrap.dedent(
                    """\
                                    Location=24.56789 38.76543 4326

                                    """
                )
            )

    def tearDown(self):
        shutil.rmtree(self.tempdir)

    def test_create_ogr_layer_from_timeseries(self):
        data_source = ogr.GetDriverByName("memory").CreateDataSource("tmp")
        filenames = [os.path.join(self.tempdir, x) for x in ("ts1", "ts2")]
        layer = hspatial.create_ogr_layer_from_timeseries(filenames, 2100, data_source)
        self.assertTrue(layer.GetFeatureCount(), 2)
        # The co-ordinates below are converted from WGS84 to Greek Grid/GGRS87
        ref = [
            {
                "x": 481180.63,
                "y": 4202647.01,  # 23.78743, 37.97385
                "filename": filenames[0],
            },
            {
                "x": 549187.44,
                "y": 4290612.25,  # 24.56789, 38.76543
                "filename": filenames[1],
            },
        ]
        for feature, r in zip(layer, ref):
            self.assertEqual(feature.GetField("filename"), r["filename"])
            self.assertAlmostEqual(feature.GetGeometryRef().GetX(), r["x"], 2)
            self.assertAlmostEqual(feature.GetGeometryRef().GetY(), r["y"], 2)


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
        self.mask = gdal.GetDriverByName("mem").Create("mask", 4, 3, 1, gdal.GDT_Byte)
        self.mask.SetGeoTransform((0, 10000, 0, 30000, 0, -10000))
        self.mask.GetRasterBand(1).WriteArray(mask_array)

    def setUp(self):
        self.tempdir = tempfile.mkdtemp()

        self.filenames = [
            os.path.join(self.tempdir, x) for x in ("ts1", "ts2", "ts3", "ts4")
        ]
        with open(self.filenames[0], "w") as f:
            f.write(
                "Unit=microchips\n"
                "Timezone=EET (UTC+0200)\n"
                "Location=19.557285 0.0473312 2100\n"  # GGRS87=5000 5000
                "\n"
                "2014-04-22 12:50,5.03,\n"
                "2014-04-22 13:00,0.54,\n"
                "2014-04-22 13:10,6.93,\n"
            )
        with open(self.filenames[1], "w") as f:
            f.write(
                "Unit=microchips\n"
                "Timezone=EET (UTC+0200)\n"
                "Location=19.64689 0.04734 2100\n"  # GGRS87=15000 5000
                "\n"
                "2014-04-22 12:50,2.90,\n"
                "2014-04-22 13:00,2.40,\n"
                "2014-04-22 13:10,9.16,\n"
            )
        with open(self.filenames[2], "w") as f:
            f.write(
                "Unit=microchips\n"
                "Timezone=EET (UTC+0200)\n"
                "Location=19.88886 0.12857 2100\n"  # GGRS87=42000 14000
                "\n"
                "2014-04-22 12:50,9.70,\n"
                "2014-04-22 13:00,1.84,\n"
                "2014-04-22 13:10,7.63,\n"
            )
        with open(self.filenames[3], "w") as f:
            # This station is missing the date required,
            # so it should not be taken into account
            f.write(
                "Unit=microchips\n"
                "Timezone=EET (UTC+0200)\n"
                "Location=19.66480 0.15560 2100\n"  # GGRS87=17000 17000
                "\n"
                "2014-04-22 12:50,9.70,\n"
                "2014-04-22 13:10,7.63,\n"
            )

        self.create_mask()
        self.stations = ogr.GetDriverByName("memory").CreateDataSource("tmp")
        self.stations_layer = hspatial.create_ogr_layer_from_timeseries(
            self.filenames, 2100, self.stations
        )

    def tearDown(self):
        shutil.rmtree(self.tempdir)

    def test_h_integrate(self):
        output_filename_prefix = os.path.join(self.tempdir, "test")
        result_filename = output_filename_prefix + "-2014-04-22-13-00+0200.tif"
        hspatial.h_integrate(
            mask=self.mask,
            stations_layer=self.stations_layer,
            date=dt.datetime(
                2014, 4, 22, 13, 0, tzinfo=TzinfoFromString("EET (+0200)")
            ),
            output_filename_prefix=output_filename_prefix,
            date_fmt="%Y-%m-%d %H:%M%z",
            funct=hspatial.idw,
            kwargs={},
        )
        f = gdal.Open(result_filename)
        result = f.GetRasterBand(1).ReadAsArray()
        nodatavalue = f.GetRasterBand(1).GetNoDataValue()
        expected_result = np.array(
            [
                [1.5088, 1.6064, nodatavalue, 1.7237],
                [1.3828, 1.6671, 1.7336, 1.7662],
                [0.5400, 2.4000, 1.7954, 1.7504],
            ]
        )
        np.testing.assert_almost_equal(result, expected_result, decimal=4)
        self.assertEqual(f.GetMetadataItem("UNIT"), "microchips")
        f = None

        # Wait long enough to make sure that, if we write to a file, its
        # modification time will be distinguishable from the modification time
        # of any file that has been written to so far (how long we need to wait
        # depends on the file system, so we use a test file).
        mtime_test_file = os.path.join(self.tempdir, "test_mtime")
        with open(mtime_test_file, "w") as f:
            f.write("hello, world")
        reference_mtime = os.path.getmtime(mtime_test_file)
        while os.path.getmtime(mtime_test_file) - reference_mtime < 0.001:
            sleep(0.001)
            with open(mtime_test_file, "w") as f:
                f.write("hello, world")

        # Try re-calculating the output; the output file should not be touched
        # at all.
        result_mtime = os.path.getmtime(result_filename)
        hspatial.h_integrate(
            mask=self.mask,
            stations_layer=self.stations_layer,
            date=dt.datetime(
                2014, 4, 22, 13, 0, tzinfo=TzinfoFromString("EET (+0200)")
            ),
            output_filename_prefix=output_filename_prefix,
            date_fmt="%Y-%m-%d %H:%M%z",
            funct=hspatial.idw,
            kwargs={},
        )
        self.assertEqual(os.path.getmtime(result_filename), result_mtime)

        # Now change one of the input files so that it contains new data that
        # can be used in the same calculation, and try recalculating. This time
        # the file should be recalculated.
        with open(self.filenames[3], "w") as f:
            f.write(
                "Timezone=EET (UTC+0200)\n"
                "Location=19.66480 0.15560 2100\n"  # GGRS87=17000 17000
                "\n"
                "2014-04-22 12:50,9.70,\n"
                "2014-04-22 13:00,4.70,\n"
                "2014-04-22 13:10,7.63,\n"
            )
        hspatial.h_integrate(
            mask=self.mask,
            stations_layer=self.stations_layer,
            date=dt.datetime(
                2014, 4, 22, 13, 0, tzinfo=TzinfoFromString("EET (+0200)")
            ),
            output_filename_prefix=output_filename_prefix,
            date_fmt="%Y-%m-%d %H:%M%z",
            funct=hspatial.idw,
            kwargs={},
        )
        self.assertGreater(os.path.getmtime(result_filename), result_mtime + 0.0009)
        f = gdal.Open(result_filename)
        result = f.GetRasterBand(1).ReadAsArray()
        nodatavalue = f.GetRasterBand(1).GetNoDataValue()
        expected_result = np.array(
            [
                [2.6736, 3.1053, nodatavalue, 2.5166],
                [2.3569, 3.5775, 2.9512, 2.3596],
                [0.5400, 2.4000, 2.5377, 2.3779],
            ]
        )
        np.testing.assert_almost_equal(result, expected_result, decimal=4)
        f = None


class ExtractPointFromRasterTestCase(TestCase):
    def setUp(self):
        self.tempdir = tempfile.mkdtemp()
        self._setup_test_raster()
        self.fp = gdal.Open(self.filename)

    def _setup_test_raster(self):
        self.filename = os.path.join(self.tempdir, "test_raster")
        nan = float("nan")
        setup_test_raster(
            self.filename,
            np.array([[1.1, nan, 1.3], [2.1, 2.2, nan], [3.1, 3.2, 3.3]]),
            dt.datetime(2014, 11, 21, 16, 1),
        )

    def tearDown(self):
        self.fp = None
        shutil.rmtree(self.tempdir)

    def test_top_left_point(self):
        point = hspatial.coordinates2point(22.005, 37.995)
        self.assertAlmostEqual(
            hspatial.extract_point_from_raster(point, self.fp), 1.1, places=2
        )

    def test_top_left_point_as_geodjango(self):
        point = GeoDjangoPoint(22.005, 37.995)
        self.assertAlmostEqual(
            hspatial.extract_point_from_raster(point, self.fp), 1.1, places=2
        )

    def test_top_middle_point(self):
        point = hspatial.coordinates2point(22.015, 37.995)
        self.assertTrue(math.isnan(hspatial.extract_point_from_raster(point, self.fp)))

    def test_middle_point(self):
        # We use co-ordinates almost to the common corner of the four lower left points,
        # only a little bit towards the center.
        point = hspatial.coordinates2point(22.01001, 37.98001)
        self.assertAlmostEqual(
            hspatial.extract_point_from_raster(point, self.fp), 2.2, places=2
        )

    def test_middle_point_with_GDALRaster(self):
        # Same as test_middle_point(), but uses GDALRaster object instead of a gdal
        # data source.
        point = hspatial.coordinates2point(22.01001, 37.98001)
        gdal_raster_object = GDALRaster(self.filename)
        self.assertAlmostEqual(
            hspatial.extract_point_from_raster(point, gdal_raster_object), 2.2, places=2
        )

    def test_bottom_left_point(self):
        # Use almost exactly same point as test_middle_point(), only slightly altered
        # so that we get bottom left point instead.
        point = hspatial.coordinates2point(22.00999, 37.97999)
        self.assertAlmostEqual(
            hspatial.extract_point_from_raster(point, self.fp), 3.1, places=2
        )

    def test_middle_point_with_GRS80(self):
        # Same as test_middle_point(), but with a different reference system, GRS80; the
        # result should be the same.
        point = hspatial.coordinates2point(325077, 4205177, srid=2100)
        self.assertAlmostEqual(
            hspatial.extract_point_from_raster(point, self.fp), 2.2, places=2
        )

    def test_does_not_modify_srid_of_point(self):
        point = hspatial.coordinates2point(325077, 4205177, srid=2100)
        original_spatial_reference = point.GetSpatialReference().ExportToWkt()
        hspatial.extract_point_from_raster(point, self.fp)
        self.assertEqual(
            point.GetSpatialReference().ExportToWkt(), original_spatial_reference
        )

    def test_bottom_left_point_with_GRS80(self):
        # Same as test_bottom_left_point(), but with a different reference system,
        # GRS80; the result should be the same.
        point = hspatial.coordinates2point(324076, 4205176, srid=2100)
        self.assertAlmostEqual(
            hspatial.extract_point_from_raster(point, self.fp), 3.1, places=2
        )

    def test_point_outside_raster(self):
        point = hspatial.coordinates2point(21.0, 38.0)
        with self.assertRaises(RuntimeError):
            hspatial.extract_point_from_raster(point, self.fp)


class ExtractPointFromRasterWhenOutsideCRSLimitsTestCase(TestCase):
    def setUp(self):
        self.tempdir = tempfile.mkdtemp()
        self._setup_test_raster()
        self.fp = gdal.Open(self.filename)

    def _setup_test_raster(self):
        self.filename = os.path.join(self.tempdir, "test_raster")
        nan = float("nan")
        setup_test_raster(
            self.filename,
            np.array([[1.1, nan, 1.3], [2.1, 2.2, nan], [3.1, 3.2, 3.3]]),
            dt.datetime(2014, 11, 21, 16, 1),
            srid=2100,
        )

    def tearDown(self):
        self.fp = None
        shutil.rmtree(self.tempdir)

    def test_fails_gracefully_when_osr_point_is_really_outside_crs_limits(self):
        point = hspatial.coordinates2point(125.0, 85.0)
        with self.assertRaises(RuntimeError):
            hspatial.extract_point_from_raster(point, self.fp)

    def test_fails_gracefully_when_geos_point_is_really_outside_crs_limits(self):
        point = GeoDjangoPoint(125.0, 85.0)
        with self.assertRaises(RuntimeError):
            hspatial.extract_point_from_raster(point, self.fp)


class SetupTestRastersMixin:
    include_time = True

    def setUp(self):
        self.tempdir = tempfile.mkdtemp()
        self._setup_test_rasters()

    def tearDown(self):
        shutil.rmtree(self.tempdir)

    def _setup_test_rasters(self):
        self._setup_raster(
            dt.date(2014, 11, 21),
            np.array([[1.1, 1.2, 1.3], [2.1, 2.2, 2.3], [3.1, 3.2, 3.3]]),
        )
        self._setup_raster(
            dt.date(2014, 11, 22),
            np.array([[11.1, 12.1, 13.1], [21.1, 22.1, 23.1], [31.1, 32.1, 33.1]]),
        )
        self._setup_raster(
            dt.date(2014, 11, 23),
            np.array(
                [[110.1, 120.1, 130.1], [210.1, 220.1, 230.1], [310.1, 320.1, 330.1]]
            ),
        )

    def _setup_raster(self, date, value):
        filename = self._create_filename(date)
        timestamp = self._create_timestamp(date)
        setup_test_raster(filename, value, timestamp, unit="microkernels")

    def _create_filename(self, date):
        result = date.strftime("test-%Y-%m-%d")
        if self.include_time:
            result += "-16-1"
        result += ".tif"
        return os.path.join(self.tempdir, result)

    def _create_timestamp(self, date):
        if self.include_time:
            return dt.datetime.combine(date, dt.time(16, 1, tzinfo=UTC_PLUS_2))
        else:
            return date

    def _check_against_expected(self, ts):
        expected = pd.DataFrame(
            data={"value": [2.2, 22.1, 220.1], "flags": ["", "", ""]},
            index=self.expected_index,
            columns=["value", "flags"],
        )
        expected.index.name = "date"
        self.assertEqual(
            ts.data.index.tz.utcoffset(None), expected.index.tz.utcoffset(None)
        )
        pd.testing.assert_frame_equal(ts.data, expected, check_index_type=False)

    @property
    def expected_index(self):
        hour, minute = self.include_time and (16, 1) or (23, 58)
        return [
            dt.datetime(2014, 11, 21, hour, minute, tzinfo=UTC_PLUS_2),
            dt.datetime(2014, 11, 22, hour, minute, tzinfo=UTC_PLUS_2),
            dt.datetime(2014, 11, 23, hour, minute, tzinfo=UTC_PLUS_2),
        ]


class PointTimeseriesGetTestCase(SetupTestRastersMixin, TestCase):
    def test_with_list_of_files(self):
        # Use co-ordinates almost to the common corner of the four lower left points,
        # and only a little bit towards the center.
        point = hspatial.coordinates2point(22.01001, 37.98001)
        filenames = [
            os.path.join(self.tempdir, "test-2014-11-22-16-1.tif"),
            os.path.join(self.tempdir, "test-2014-11-21-16-1.tif"),
            os.path.join(self.tempdir, "test-2014-11-23-16-1.tif"),
        ]
        ts = hspatial.PointTimeseries(
            point, filenames=filenames, default_time=dt.time(0, 0, tzinfo=UTC_PLUS_2)
        ).get()
        self._check_against_expected(ts)

    def test_raises_when_no_timezone(self):
        point = hspatial.coordinates2point(22.01001, 37.98001)
        filenames = [os.path.join(self.tempdir, "test-2014-11-22-16-1.tif")]
        with self.assertRaises(TypeError):
            hspatial.PointTimeseries(
                point, filenames=filenames, default_time=dt.time(0, 0)
            )

    def test_with_prefix(self):
        # Same as test_with_list_of_files(), but with prefix.
        point = hspatial.coordinates2point(22.01001, 37.98001)
        prefix = os.path.join(self.tempdir, "test")
        ts = hspatial.PointTimeseries(
            point, prefix=prefix, default_time=dt.time(0, 0, tzinfo=UTC_PLUS_2)
        ).get()
        self._check_against_expected(ts)

    def test_with_prefix_and_geodjango(self):
        point = hspatial.coordinates2point(22.01001, 37.98001)
        prefix = os.path.join(self.tempdir, "test")
        ts = hspatial.PointTimeseries(
            point, prefix=prefix, default_time=dt.time(0, 0, tzinfo=UTC_PLUS_2)
        ).get()
        self._check_against_expected(ts)

    def test_unit_of_measurement(self):
        point = hspatial.coordinates2point(22.01001, 37.98001)
        prefix = os.path.join(self.tempdir, "test")
        ts = hspatial.PointTimeseries(
            point, prefix=prefix, default_time=dt.time(0, 0, tzinfo=UTC_PLUS_2)
        ).get()
        self.assertEqual(ts.unit, "microkernels")


class PointTimeseriesGetDailyTestCase(SetupTestRastersMixin, TestCase):
    include_time = False

    def test_with_list_of_files(self):
        # Use co-ordinates almost to the center of the four lower left points, and only
        # a little bit towards the center.
        point = hspatial.coordinates2point(22.01001, 37.98001)
        filenames = [
            os.path.join(self.tempdir, "test-2014-11-22.tif"),
            os.path.join(self.tempdir, "test-2014-11-21.tif"),
            os.path.join(self.tempdir, "test-2014-11-23.tif"),
        ]
        ts = hspatial.PointTimeseries(
            point, filenames=filenames, default_time=dt.time(23, 58, tzinfo=UTC_PLUS_2)
        ).get()
        self._check_against_expected(ts)

    def test_with_prefix(self):
        # Same as test_with_list_of_files(), but with prefix.
        point = hspatial.coordinates2point(22.01001, 37.98001)
        prefix = os.path.join(self.tempdir, "test")
        ts = hspatial.PointTimeseries(
            point, prefix=prefix, default_time=dt.time(23, 58, tzinfo=UTC_PLUS_2)
        ).get()
        self._check_against_expected(ts)

    def test_with_prefix_and_geodjango(self):
        point = GeoDjangoPoint(22.01001, 37.98001)
        prefix = os.path.join(self.tempdir, "test")
        ts = hspatial.PointTimeseries(
            point, prefix=prefix, default_time=dt.time(23, 58, tzinfo=UTC_PLUS_2)
        ).get()
        self._check_against_expected(ts)


class PointTimeseriesGetCachedTestCase(SetupTestRastersMixin, TestCase):
    def setUp(self):
        super().setUp()
        self.point = hspatial.coordinates2point(22.01001, 37.98001)
        self.prefix = os.path.join(self.tempdir, "test")
        self.dest = os.path.join(self.tempdir, "dest.hts")

    def test_result(self):
        result = hspatial.PointTimeseries(
            self.point,
            prefix=self.prefix,
            default_time=dt.time(0, 0, tzinfo=UTC_PLUS_2),
        ).get_cached(self.dest)
        self._check_against_expected(result)

    def test_file(self):
        hspatial.PointTimeseries(
            self.point,
            prefix=self.prefix,
            default_time=dt.time(0, 0, tzinfo=UTC_PLUS_2),
        ).get_cached(self.dest)
        with open(self.dest, "r", newline="\n") as f:
            self._check_against_expected(HTimeseries(f, default_tzinfo=UTC_PLUS_2))

    def test_version(self):
        hspatial.PointTimeseries(
            self.point,
            prefix=self.prefix,
            default_time=dt.time(0, 0, tzinfo=UTC_PLUS_2),
        ).get_cached(self.dest, version=2)
        with open(self.dest, "r") as f:
            first_line = f.readline()
        self.assertEqual(first_line, "Version=2\n")

    def test_file_is_not_recreated(self):
        hspatial.PointTimeseries(
            self.point,
            prefix=self.prefix,
            default_time=dt.time(0, 0, tzinfo=UTC_PLUS_2),
        ).get_cached(self.dest)

        # Make existing file read-only
        os.chmod(self.dest, S_IREAD | S_IRGRP | S_IROTH)

        # Try again—it shouldn't try to write, therefore it shouldn't raise exception
        hspatial.PointTimeseries(
            self.point,
            prefix=self.prefix,
            default_time=dt.time(0, 0, tzinfo=UTC_PLUS_2),
        ).get_cached(self.dest)
        with open(self.dest, "r", newline="\n") as f:
            self._check_against_expected(HTimeseries(f, default_tzinfo=UTC_PLUS_2))

    def test_file_is_recreated_when_out_of_date(self):
        hspatial.PointTimeseries(
            self.point,
            prefix=self.prefix,
            default_time=dt.time(0, 0, tzinfo=UTC_PLUS_2),
        ).get_cached(self.dest)
        self._setup_additional_raster()

        # Make existing file read-only
        os.chmod(self.dest, S_IREAD | S_IRGRP | S_IROTH)

        # Try again—it should raise exception
        with self.assertRaises(PermissionError):
            hspatial.PointTimeseries(
                self.point,
                prefix=self.prefix,
                default_time=dt.time(0, 0, tzinfo=UTC_PLUS_2),
            ).get_cached(self.dest)

    def _setup_additional_raster(self):
        filename = os.path.join(self.tempdir, "test-2014-11-24-16-1.tif")
        setup_test_raster(
            filename,
            np.array(
                [[110.1, 120.1, 130.1], [210.1, 220.1, 230.1], [310.1, 320.1, 330.1]]
            ),
            dt.datetime(2014, 11, 24, 16, 1),
        )

    def test_start_date(self):
        start_date = dt.datetime(2014, 11, 22, 16, 1)
        result = hspatial.PointTimeseries(
            self.point,
            prefix=self.prefix,
            start_date=start_date,
            default_time=dt.time(0, 0, tzinfo=UTC_PLUS_2),
        ).get_cached(self.dest)
        self.assertEqual(result.data.index[0], start_date.replace(tzinfo=UTC_PLUS_2))

    def test_end_date(self):
        end_date = dt.datetime(2014, 11, 22, 16, 1)
        result = hspatial.PointTimeseries(
            self.point,
            prefix=self.prefix,
            end_date=end_date,
            default_time=dt.time(0, 0, tzinfo=UTC_PLUS_2),
        ).get_cached(self.dest)
        self.assertEqual(result.data.index[-1], end_date.replace(tzinfo=UTC_PLUS_2))


class FilenameWithDateFormatTestCase(TestCase):
    def test_with_given_datetime_format(self):
        format = hspatial.FilenameWithDateFormat(
            "myprefix", date_fmt="%d-%m-%Y-%H-%M", tzinfo=UTC_PLUS_2
        )
        self.assertEqual(
            format.get_date("myprefix-4-8-2019-10-41.tif"),
            dt.datetime(2019, 8, 4, 10, 41, tzinfo=UTC_PLUS_2),
        )

    def test_with_given_date_format(self):
        format = hspatial.FilenameWithDateFormat(
            "myprefix", date_fmt="%d-%m-%Y", tzinfo=UTC_PLUS_2
        )
        self.assertEqual(
            format.get_date("myprefix-4-8-2019.tif"),
            dt.datetime(2019, 8, 4, tzinfo=UTC_PLUS_2),
        )

    def test_datetime_with_auto_format(self):
        format = hspatial.FilenameWithDateFormat("myprefix", tzinfo=UTC_PLUS_2)
        self.assertEqual(
            format.get_date("myprefix-2019-8-4-10-41.tif"),
            dt.datetime(2019, 8, 4, 10, 41, tzinfo=UTC_PLUS_2),
        )

    def test_date_with_auto_format(self):
        format = hspatial.FilenameWithDateFormat("myprefix", tzinfo=UTC_PLUS_2)
        self.assertEqual(
            format.get_date("myprefix-2019-8-4.tif"),
            dt.datetime(2019, 8, 4, tzinfo=UTC_PLUS_2),
        )


class PassepartoutPointTestCase(TestCase):
    def test_transform_does_not_modify_srid_of_gdal_point(self):
        pppoint = hspatial.PassepartoutPoint(
            hspatial.coordinates2point(324651, 4205742, srid=2100)
        )
        original_spatial_reference = pppoint.point.GetSpatialReference().ExportToWkt()
        sr = osr.SpatialReference()
        sr.ImportFromEPSG(4326)
        pppoint.transform_to(sr.ExportToWkt())
        self.assertEqual(
            pppoint.point.GetSpatialReference().ExportToWkt(),
            original_spatial_reference,
        )

    def test_transform_does_not_modify_srid_of_geodjango_point(self):
        pppoint = hspatial.PassepartoutPoint(GeoDjangoPoint(324651, 4205742, srid=2100))
        pppoint.transform_to(4326)
        self.assertEqual(pppoint.point.srid, 2100)
