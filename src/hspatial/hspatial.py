from __future__ import annotations

import datetime as dt
import os
import struct
from glob import glob
from math import isnan
from typing import Any, Callable, Dict, Iterable, List, Mapping, Optional, Union

import iso8601
import numpy as np
from affine import Affine
from django.contrib.gis.gdal import CoordTransform, SpatialReference
from django.contrib.gis.gdal.error import GDALException
from django.contrib.gis.geos import Point as GeoDjangoPoint
from osgeo import gdal, ogr, osr

from htimeseries import HTimeseries

gdal.UseExceptions()

NODATAVALUE = -(2.0**127)

GeometryLike = Union[GeoDjangoPoint, ogr.Geometry]
KwargsMapping = Mapping[str, Any]
InterpolationFunction = Callable[..., float]


def coordinates2point(x: float, y: float, srid: int = 4326) -> ogr.Geometry:
    point = ogr.Geometry(ogr.wkbPoint)
    sr = osr.SpatialReference()
    sr.ImportFromEPSG(srid)
    if int(gdal.__version__.split(".")[0]) > 2:
        sr.SetAxisMappingStrategy(osr.OAMS_TRADITIONAL_GIS_ORDER)
    point.AssignSpatialReference(sr)
    point.AddPoint(x, y)
    return point


def idw(point: ogr.Geometry, data_layer: ogr.Layer, alpha: float = 1) -> float:
    data_layer.ResetReading()
    features = [f for f in data_layer if not isnan(f.GetField("value"))]
    distances = np.array([point.Distance(f.GetGeometryRef()) for f in features])
    values = np.array([f.GetField("value") for f in features])
    matches_station_exactly = abs(distances) < 1e-3
    if matches_station_exactly.any():
        invdistances = np.where(matches_station_exactly, 1, 0)
    else:
        invdistances = distances ** (-alpha)
    weights = invdistances / invdistances.sum()
    return (weights * values).sum()


def integrate(
    dataset: Any,
    data_layer: ogr.Layer,
    target_band: Any,
    funct: InterpolationFunction,
    kwargs: Optional[KwargsMapping] = None,
) -> None:
    call_kwargs: Dict[str, Any] = dict(kwargs or {})
    try:
        mask = dataset.GetRasterBand(1).ReadAsArray() != 0
        x_left, x_step, d1, y_top, d2, y_step = dataset.GetGeoTransform()
    except AttributeError:
        mask = dataset.bands[0].data() != 0
        x_left, x_step, d1, y_top, d2, y_step = dataset.geotransform

    # Create an array with the x co-ordinate of each grid point, and
    # one with the y co-ordinate of each grid point
    height, width = mask.shape
    xcoords = np.arange(x_left + x_step / 2.0, x_left + x_step * width, x_step)
    ycoords = np.arange(y_top + y_step / 2.0, y_top + y_step * height, y_step)
    xarray, yarray = np.meshgrid(xcoords, ycoords)

    # Create a ufunc that makes the interpolation given the above arrays
    def interpolate_one_point(x: float, y: float, mask_value: bool) -> float:
        if not mask_value:
            return np.nan
        point = ogr.Geometry(ogr.wkbPoint)
        point.AddPoint(x, y)
        return funct(point, data_layer, **call_kwargs)

    interpolate = np.vectorize(interpolate_one_point, otypes=[np.float32])

    # Make the calculation
    result = interpolate(xarray, yarray, mask)
    result[np.isnan(result)] = NODATAVALUE
    try:
        target_band.SetNoDataValue(NODATAVALUE)
        target_band.WriteArray(result)
    except AttributeError:
        target_band.nodata_value = NODATAVALUE
        target_band.data(data=result)


def create_ogr_layer_from_timeseries(
    filenames: Iterable[str], epsg: int, data_source: ogr.DataSource  # type: ignore[type-alias]
) -> ogr.Layer:
    # Prepare the co-ordinate transformation from WGS84 to epsg
    source_sr = osr.SpatialReference()
    source_sr.ImportFromEPSG(4326)
    target_sr = osr.SpatialReference()
    target_sr.ImportFromEPSG(epsg)
    if int(gdal.__version__.split(".")[0]) > 2:
        source_sr.SetAxisMappingStrategy(osr.OAMS_TRADITIONAL_GIS_ORDER)
        target_sr.SetAxisMappingStrategy(osr.OAMS_TRADITIONAL_GIS_ORDER)
    transform = osr.CoordinateTransformation(source_sr, target_sr)

    layer = data_source.CreateLayer("stations", target_sr)
    layer.CreateField(ogr.FieldDefn("filename", ogr.OFTString))
    for filename in filenames:
        with open(filename, newline="\n") as f:
            # The default_tzinfo doesn't matter because we don't care about the data,
            # we only use the location.
            ts = HTimeseries(f, default_tzinfo=dt.timezone.utc)
        point = ogr.Geometry(ogr.wkbPoint)
        assert ts.location is not None
        point.AddPoint(ts.location["abscissa"], ts.location["ordinate"])
        point.Transform(transform)
        f = ogr.Feature(layer.GetLayerDefn())
        f.SetGeometry(point)
        f.SetField("filename", filename)
        layer.CreateFeature(f)
    return layer


def _needs_calculation(
    output_filename: str, date: dt.datetime, stations_layer: ogr.Layer
) -> bool:
    """
    Used by h_integrate to check whether the output file needs to be calculated
    or not. It does not need to be calculated if it already exists and has been
    calculated from all available data.
    """
    # Return immediately if output file does not exist
    if not os.path.exists(output_filename):
        return True

    # Get list of files which were used to calculate the output file
    fp = gdal.Open(output_filename)
    try:
        actual_input_files = fp.GetMetadataItem("INPUT_FILES")
        if actual_input_files is None:
            raise IOError(
                "{} does not contain the metadata item INPUT_FILES".format(
                    output_filename
                )
            )
    finally:
        fp = None  # Close file
    actual_input_files = set(actual_input_files.split("\n"))

    # Get list of files available for calculating the output file
    stations_layer.ResetReading()
    available_input_files = set(
        [
            station.GetField("filename")
            for station in stations_layer
            if os.path.exists(station.GetField("filename"))
        ]
    )

    # Which of these files have not been used?
    unused_files = available_input_files - actual_input_files

    # For each one of these files, check whether it has newly available data.
    # Upon finding one that does, the verdict is made: return True
    for filename in unused_files:
        with open(filename, newline="\n") as f:
            t = HTimeseries(f)
        try:
            value = t.data.loc[date, "value"]  # type: ignore[index]
            if not isnan(value):
                return True
        except KeyError:
            continue

    # We were unable to find data that had not already been used
    return False


def h_integrate(
    mask: gdal.Dataset,
    stations_layer: ogr.Layer,
    date: dt.datetime,
    output_filename_prefix: str,
    date_fmt: str,
    funct: InterpolationFunction,
    kwargs: Optional[KwargsMapping],
) -> None:
    date_fmt_for_filename = date.strftime(date_fmt).replace(" ", "-").replace(":", "-")
    output_filename = "{}-{}.tif".format(
        output_filename_prefix, date.strftime(date_fmt_for_filename)
    )
    if not _needs_calculation(output_filename, date, stations_layer):
        return

    # Read the time series values and add the 'value' attribute to
    # stations_layer. Also determine the unit of measurement.
    stations_layer.CreateField(ogr.FieldDefn("value", ogr.OFTReal))
    input_files = []
    unit_of_measurement = None
    stations_layer.ResetReading()
    for station in stations_layer:
        filename = station.GetField("filename")
        with open(filename, newline="\n") as f:
            t = HTimeseries(f)
        if unit_of_measurement is None and hasattr(t, "unit"):
            unit_of_measurement = t.unit
        try:
            value = t.data.loc[date, "value"]  # type: ignore[index]
        except KeyError:
            value = np.nan
        station.SetField("value", value)
        if not isnan(value):
            input_files.append(filename)
        stations_layer.SetFeature(station)
    if not input_files:
        return

    # Create destination data source
    output = gdal.GetDriverByName("GTiff").Create(
        output_filename, mask.RasterXSize, mask.RasterYSize, 1, gdal.GDT_Float32
    )
    output.SetMetadataItem("TIMESTAMP", date.strftime(date_fmt))
    output.SetMetadataItem("INPUT_FILES", "\n".join(input_files))
    output.SetMetadataItem("UNIT", unit_of_measurement)

    try:
        # Set geotransform and projection in the output data source
        output.SetGeoTransform(mask.GetGeoTransform())
        output.SetProjection(mask.GetProjection())

        # Do the integration
        integrate(mask, stations_layer, output.GetRasterBand(1), funct, kwargs)
    finally:
        # Close the dataset
        output = None


class PassepartoutPoint:
    """Uniform interface for GeoDjango Point and OGR Point."""

    def __init__(self, point: GeometryLike) -> None:
        self.point: GeometryLike = point

    def transform_to(self, target_srs_wkt: str) -> "PassepartoutPoint":
        point = self.clone(self.point)
        if isinstance(self.point, GeoDjangoPoint):
            source_srs = getattr(point, "srs") or SpatialReference("4326")
            if hasattr(source_srs, "SetAxisMappingStrategy"):
                source_srs.SetAxisMappingStrategy(osr.OAMS_TRADITIONAL_GIS_ORDER)  # type: ignore[attr-defined]
            ct = CoordTransform(source_srs, SpatialReference(target_srs_wkt))
            point.transform(ct)  # type: ignore[attr-defined]
            return PassepartoutPoint(point)
        else:
            point_sr = point.GetSpatialReference()  # type: ignore[attr-defined]
            raster_sr = osr.SpatialReference()
            raster_sr.ImportFromWkt(target_srs_wkt)
            if int(gdal.__version__.split(".")[0]) > 2:
                point_sr.SetAxisMappingStrategy(osr.OAMS_TRADITIONAL_GIS_ORDER)
                raster_sr.SetAxisMappingStrategy(osr.OAMS_TRADITIONAL_GIS_ORDER)
            transform = osr.CoordinateTransformation(point_sr, raster_sr)
            point.Transform(transform)  # type: ignore[attr-defined]
            return PassepartoutPoint(point)

    def clone(self, original_point: GeometryLike) -> GeometryLike:
        if isinstance(original_point, GeoDjangoPoint):
            return GeoDjangoPoint(
                original_point.x, original_point.y, original_point.srid
            )
        else:
            point = ogr.Geometry(ogr.wkbPoint)
            point.AddPoint(original_point.GetX(), original_point.GetY())
            point.AssignSpatialReference(original_point.GetSpatialReference())
            return point

    @property
    def x(self) -> float:
        if isinstance(self.point, GeoDjangoPoint):
            return self.point.x
        else:
            return self.point.GetX()

    @property
    def y(self) -> float:
        if isinstance(self.point, GeoDjangoPoint):
            return self.point.y
        else:
            return self.point.GetY()


def extract_point_from_raster(
    point: GeometryLike, data_source: Any, band_number: int = 1
) -> float:
    """Return floating-point value that corresponds to given point."""
    pppoint = PassepartoutPoint(point)

    # Convert point co-ordinates so that they are in same projection as raster
    try:
        target_srs_wkt = data_source.GetProjection()
    except AttributeError:
        target_srs_wkt = data_source.srs.wkt
    try:
        pppoint = pppoint.transform_to(target_srs_wkt)
    except GDALException:
        raise RuntimeError("Couldn't convert point to raster's CRS")
    infinities = (float("inf"), float("-inf"))
    if pppoint.x in infinities or pppoint.y in infinities:
        raise RuntimeError("Couldn't convert point to raster's CRS")

    # Convert geographic co-ordinates to pixel co-ordinates
    try:
        forward_transform = Affine.from_gdal(*data_source.GetGeoTransform())
    except AttributeError:
        forward_transform = Affine.from_gdal(*data_source.geotransform)
    reverse_transform = ~forward_transform
    px, py = reverse_transform * (pppoint.x, pppoint.y)  # type: ignore[operator]
    px, py = int(px), int(py)

    # Extract pixel value
    try:
        band = data_source.GetRasterBand(band_number)
    except AttributeError:
        band = data_source.bands[band_number - 1]
    try:
        structval = band.ReadRaster(px, py, 1, 1, buf_type=gdal.GDT_Float32)
    except AttributeError:
        structval = band.data(offset=(px, py), size=(1, 1))
    result = struct.unpack("f", structval)[0]
    try:
        nodata_value = band.GetNoDataValue()
    except AttributeError:
        nodata_value = band.nodata_value
    if result == nodata_value:
        result = float("nan")
    return result


class PointTimeseries:
    def __init__(
        self,
        point: GeometryLike,
        *,
        filenames: Optional[Iterable[str]] = None,
        prefix: Optional[str] = None,
        date_fmt: Optional[str] = None,
        start_date: Optional[dt.datetime] = None,
        end_date: Optional[dt.datetime] = None,
        default_time: dt.time = dt.time(0, 0, tzinfo=dt.timezone.utc),
    ) -> None:
        self.point: GeometryLike = point
        self.prefix = prefix
        self.filename_format: Optional[FilenameWithDateFormat] = None
        assert filenames is None or self.prefix is None
        assert filenames is not None or self.prefix is not None
        self.date_fmt = date_fmt
        self.start_date = start_date
        self.end_date = end_date
        self.default_time = default_time
        if self.default_time.tzinfo is None:
            raise TypeError("default_time must be aware")
        if self.start_date and self.start_date.tzinfo is None:
            self.start_date = self.start_date.replace(tzinfo=self.default_time.tzinfo)
        if self.end_date and self.end_date.tzinfo is None:
            self.end_date = self.end_date.replace(tzinfo=self.default_time.tzinfo)
        self.filenames: List[str] = self._get_filenames(filenames)

    def _get_filenames(self, filenames: Optional[Iterable[str]]) -> List[str]:
        if self.prefix is None:
            assert filenames is not None
            return list(filenames)
        filenames_list = glob(self.prefix + "-*.tif")
        assert self.default_time.tzinfo is not None
        self.filename_format = FilenameWithDateFormat(
            self.prefix, date_fmt=self.date_fmt, tzinfo=self.default_time.tzinfo
        )
        result: List[str] = []
        for filename in filenames_list:
            date = self.filename_format.get_date(filename)
            is_after_start_date = (self.start_date is None) or (date >= self.start_date)
            is_before_end_date = (self.end_date is None) or (date <= self.end_date)
            if is_after_start_date and is_before_end_date:
                result.append(filename)
        return result

    def get(self) -> HTimeseries:
        result = HTimeseries(default_tzinfo=self.default_time.tzinfo)
        for filename in self.filenames:
            f = gdal.Open(filename)
            try:
                timestamp = self._get_timestamp(f)
                self._get_unit_of_measurement(f, result)
                value = extract_point_from_raster(self.point, f)
                result.data.loc[timestamp, "value"] = value
                result.data.loc[timestamp, "flags"] = ""
            finally:
                f = None
        result.data = result.data.sort_index()
        return result

    def _get_timestamp(self, f: Any) -> dt.datetime:
        isostring = f.GetMetadata()["TIMESTAMP"]
        assert self.default_time.tzinfo is not None
        assert isinstance(self.default_time.tzinfo, dt.timezone)
        timestamp = iso8601.parse_date(
            isostring, default_timezone=self.default_time.tzinfo
        )
        if len(isostring) <= 10:
            timestamp = dt.datetime.combine(timestamp.date(), self.default_time)
        return timestamp

    def _get_unit_of_measurement(self, f: Any, ahtimeseries: HTimeseries) -> None:
        if hasattr(ahtimeseries, "unit"):
            return
        unit = f.GetMetadataItem("UNIT")
        if unit is not None:
            ahtimeseries.unit = unit

    def get_cached(
        self, dest: str, force: bool = False, version: int = 4
    ) -> HTimeseries:
        assert self.prefix
        ts = self._get_saved_timeseries_if_updated_else_none(dest, force)
        if ts is None:
            ts = self.get()
            with open(dest, "w", newline="") as f:
                ts.write(f, format=HTimeseries.FILE, version=version)
        return ts

    def _get_saved_timeseries_if_updated_else_none(
        self, dest: str, force: bool
    ) -> Optional[HTimeseries]:
        if force or not os.path.exists(dest):
            return None
        else:
            return self._get_timeseries_if_file_is_up_to_date_else_none(dest)

    def _get_timeseries_if_file_is_up_to_date_else_none(
        self, dest: str
    ) -> Optional[HTimeseries]:
        with open(dest, "r", newline="") as f:
            ts = HTimeseries(f, default_tzinfo=self.default_time.tzinfo)
        for filename in self.filenames:
            assert self.filename_format is not None
            if not self.filename_format.get_date(filename) in ts.data.index:
                return None
        return ts


class FilenameWithDateFormat:
    def __init__(
        self,
        prefix: str,
        *,
        date_fmt: Optional[str] = None,
        tzinfo: dt.tzinfo,
    ) -> None:
        self.prefix = prefix
        self.date_fmt = date_fmt
        self.tzinfo = tzinfo

    def get_date(self, filename: str) -> dt.datetime:
        datestr = self._extract_datestr(filename)
        self._ensure_we_have_date_fmt(datestr)
        assert self.date_fmt is not None
        return dt.datetime.strptime(datestr, self.date_fmt).replace(tzinfo=self.tzinfo)

    def _ensure_we_have_date_fmt(self, datestr: str) -> None:
        if self.date_fmt is not None:
            pass
        elif datestr.count("-") == 4:
            self.date_fmt = "%Y-%m-%d-%H-%M"
        elif datestr.count("-") == 2:
            self.date_fmt = "%Y-%m-%d"
        else:
            raise ValueError("Invalid date " + datestr)

    def _extract_datestr(self, filename: str) -> str:
        assert filename.startswith(self.prefix + "-")
        assert filename.endswith(".tif")
        startpos = len(self.prefix) + 1
        return filename[startpos:-4]
