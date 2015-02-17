from glob import glob
from math import isnan
import os
import struct

from affine import Affine
import iso8601
import numpy as np
from osgeo import ogr, osr, gdal
from simpletail import ropen

from pthelma.cliapp import CliApp, WrongValueError
from pthelma.timeseries import Timeseries, TzinfoFromString

gdal.UseExceptions()

NODATAVALUE = -2.0 ** 127

def idw(point, data_layer, alpha=1):
    data_layer.ResetReading()
    features = [f for f in data_layer if not isnan(f.GetField('value'))]
    distances = np.array([point.Distance(f.GetGeometryRef())
                          for f in features])
    values = np.array([f.GetField('value') for f in features])
    matches_station_exactly = abs(distances) < 1e-3
    if matches_station_exactly.any():
        invdistances = np.where(matches_station_exactly, 1, 0)
    else:
        invdistances = distances ** (-alpha)
    weights = invdistances / invdistances.sum()
    return (weights * values).sum()


def integrate(dataset, data_layer, target_band, funct, kwargs={}):
    mask = (dataset.GetRasterBand(1).ReadAsArray() != 0)

    # Create an array with the x co-ordinate of each grid point, and
    # one with the y co-ordinate of each grid point
    height, width = mask.shape
    x_left, x_step, d1, y_top, d2, y_step = dataset.GetGeoTransform()
    xcoords = np.arange(x_left + x_step / 2.0, x_left + x_step * width, x_step)
    ycoords = np.arange(y_top + y_step / 2.0, y_top + y_step * height, y_step)
    xarray, yarray = np.meshgrid(xcoords, ycoords)

    # Create a ufunc that makes the interpolation given the above arrays
    def interpolate_one_point(x, y, mask):
        if not mask:
            return np.nan
        point = ogr.Geometry(ogr.wkbPoint)
        point.AddPoint(x, y)
        return funct(point, data_layer, **kwargs)
    interpolate = np.vectorize(interpolate_one_point, otypes=[np.float32])

    # Make the calculation
    result = interpolate(xarray, yarray, mask)
    result[np.isnan(result)] = NODATAVALUE
    target_band.SetNoDataValue(NODATAVALUE)
    target_band.WriteArray(result)


def create_ogr_layer_from_timeseries(filenames, epsg, data_source):
    # Prepare the co-ordinate transformation from WGS84 to epsg
    source_sr = osr.SpatialReference()
    source_sr.ImportFromEPSG(4326)
    target_sr = osr.SpatialReference()
    target_sr.ImportFromEPSG(epsg)
    transform = osr.CoordinateTransformation(source_sr, target_sr)

    layer = data_source.CreateLayer('stations', target_sr)
    layer.CreateField(ogr.FieldDefn('filename', ogr.OFTString))
    for filename in filenames:
        with open(filename) as f:
            ts = Timeseries()
            ts.read_meta(f)
        point = ogr.Geometry(ogr.wkbPoint)
        point.AddPoint(ts.location['abscissa'], ts.location['ordinate'])
        point.Transform(transform)
        f = ogr.Feature(layer.GetLayerDefn())
        f.SetGeometry(point)
        f.SetField('filename', filename)
        layer.CreateFeature(f)
    return layer


def _needs_calculation(output_filename, date, stations_layer):
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
        actual_input_files = fp.GetMetadataItem('INPUT_FILES')
        if actual_input_files is None:
            raise IOError('{} does not contain the metadata item INPUT_FILES'
                          .format(output_filename))
    finally:
        fp = None  # Close file
    actual_input_files = set(actual_input_files.split('\n'))

    # Get list of files available for calculating the output file
    stations_layer.ResetReading()
    available_input_files = set(
        [station.GetField('filename') for station in stations_layer
         if os.path.exists(station.GetField('filename'))])

    # Which of these files have not been used?
    unused_files = available_input_files - actual_input_files

    # For each one of these files, check whether it has newly available data.
    # Upon finding one that does, the verdict is made: return True
    for filename in unused_files:
        t = Timeseries()
        with open(filename) as f:
            t.read_file(f)
        value = t.get(date, float('NaN'))
        if not isnan(value):
            return True

    # We were unable to find data that had not already been used
    return False


def h_integrate(mask, stations_layer, date, output_filename_prefix, date_fmt,
                funct, kwargs):
    date_fmt_for_filename = date.strftime(date_fmt).replace(' ', '-').replace(
        ':', '-')
    output_filename = '{}-{}.tif'.format(output_filename_prefix,
                                         date.strftime(date_fmt_for_filename))
    if not _needs_calculation(output_filename, date, stations_layer):
        return

    # Read the time series values and add the 'value' attribute to
    # stations_layer
    stations_layer.CreateField(ogr.FieldDefn('value', ogr.OFTReal))
    input_files = []
    stations_layer.ResetReading()
    for station in stations_layer:
        filename = station.GetField('filename')
        t = Timeseries()
        with open(filename) as f:
            t.read_file(f)
        value = t.get(date, float('NaN'))
        station.SetField('value', value)
        if not isnan(value):
            input_files.append(filename)
        stations_layer.SetFeature(station)
    if not input_files:
        return

    # Create destination data source
    output = gdal.GetDriverByName('GTiff').Create(
        output_filename, mask.RasterXSize, mask.RasterYSize, 1,
        gdal.GDT_Float32)
    output.SetMetadataItem('TIMESTAMP', date.strftime(date_fmt))
    output.SetMetadataItem('INPUT_FILES', '\n'.join(input_files))

    try:
        # Set geotransform and projection in the output data source
        output.SetGeoTransform(mask.GetGeoTransform())
        output.SetProjection(mask.GetProjection())

        # Do the integration
        integrate(mask, stations_layer, output.GetRasterBand(1), funct, kwargs)
    finally:
        # Close the dataset
        output = None


def extract_point_from_raster(point, data_source, band_number=1):
    """Return floating-point value that corresponds to given point."""

    # Convert point co-ordinates so that they are in same projection as raster
    point_sr = point.GetSpatialReference()
    raster_sr = osr.SpatialReference()
    raster_sr.ImportFromWkt(data_source.GetProjection())
    transform = osr.CoordinateTransformation(point_sr, raster_sr)
    point.Transform(transform)

    # Convert geographic co-ordinates to pixel co-ordinates
    x, y = point.GetX(), point.GetY()
    forward_transform = Affine.from_gdal(*data_source.GetGeoTransform())
    reverse_transform = ~forward_transform
    px, py = reverse_transform * (x, y)
    px, py = int(px + 0.5), int(py + 0.5)

    # Extract pixel value
    band = data_source.GetRasterBand(band_number)
    structval = band.ReadRaster(px, py, 1, 1, buf_type=gdal.GDT_Float32)
    result = struct.unpack('f', structval)[0]
    if result == band.GetNoDataValue():
        result = float('nan')
    return result


def extract_point_timeseries_from_rasters(files, point):
    """Return time series of point values from a set of rasters.

    Arguments:
    files: Sequence or set of rasters.
    point: An OGR point.

    The rasters must have TIMESTAMP metadata item. The function reads all
    rasters, extracts the value at specified point, and returns all extracted
    values as a Timeseries object.
    """
    result = Timeseries()
    for f in files:
        fp = gdal.Open(f)
        try:
            isostring = fp.GetMetadata()['TIMESTAMP']
            timestamp = iso8601.parse_date(isostring, default_timezone=None)
            value = extract_point_from_raster(point, fp)
            result[timestamp] = value
        finally:
            fp = None
    return result


class SpatializeApp(CliApp):
    name = 'spatialize'
    description = 'Perform spatial integration'
    #                     Section          Option            Default
    config_file_options = {'General': {'mask':             None,
                                       'epsg':             None,
                                       'output_dir':       None,
                                       'filename_prefix':  None,
                                       'number_of_output_files':  None,
                                       'method':           None,
                                       'alpha':            '1',
                                       'files':            None,
                                       },
                           }

    def read_configuration(self):
        super(SpatializeApp, self).read_configuration()
        self.files = self.config['General']['files'].split('\n')
        self.check_configuration_method()
        self.check_configuration_epsg()

    def check_configuration_method(self):
        # Check method
        if self.config['General']['method'] != 'idw':
            raise WrongValueError('Option "method" can currently only be idw')
        # Check alpha
        try:
            float(self.config['General']['alpha'])
        except ValueError:
            raise WrongValueError('Option "alpha" must be a number')

    def check_configuration_epsg(self):
        try:
            epsg = int(self.config['General']['epsg'])
        except ValueError:
            raise WrongValueError('Option "epsg" must be an integer')
        srs = osr.SpatialReference()
        result = srs.ImportFromEPSG(epsg)
        if result:
            raise WrongValueError(
                'An error occurred when trying to use epsg={}'.format(epsg))

    def get_last_dates(self, filename, n):
        """
        Assuming specified file contains a time series, scan it from the bottom
        and return the list of the n last dates (may be less than n if the time
        series is too small). 'filename' is used in error messages.
        """
        # Get the time zone
        with open(filename) as fp:
            for line in fp:
                if line.startswith('Timezone') or (
                        line and line[0] in '0123456789'):
                    break
        zonestr = line.partition('=')[2].strip() \
            if line.startswith('Timezone') else ''
        timezone = TzinfoFromString(zonestr)

        result = []
        previous_line_was_empty = False
        with ropen(filename) as fp:
            for i, line in enumerate(fp):
                if i >= n:
                    break
                line = line.strip()

                # Ignore empty lines
                if not line:
                    previous_line_was_empty = True
                    continue

                # Is the line in the form of an ini file configuration line?
                items = line.split('=')
                if len(items) and (',' not in items[0]) \
                        and previous_line_was_empty:
                    break  # Yes; we reached the start of the file

                previous_line_was_empty = False

                datestring = line.split(',')[0]
                try:
                    result.insert(0, iso8601.parse_date(
                        datestring, default_timezone=timezone))
                except iso8601.ParseError as e:
                    raise iso8601.ParseError(
                        str(e) + ' (file {}, {} lines from the end)'
                        .format(filename, i + 1))
        return result

    @property
    def dates_to_calculate(self):
        """
        Generator that yields the dates for which h_integrate should be run;
        this is the latest list of dates such that:
        * At least one of the time series has data
        * The length of the list is the 'number_of_output_files' configuration
          option (maybe less if the time series don't have enough data yet).
        """
        n = int(self.config['General']['number_of_output_files'])
        dates = set()
        for filename in self.files:
            dates |= set(self.get_last_dates(filename, n))
        dates = list(dates)
        dates.sort()
        dates = dates[-n:]
        for d in dates:
            yield d

    @property
    def time_step(self):
        """
        Return time step of all time series. If time step is not the same
        for all time series, raises exception.
        """
        time_step = None
        for filename in self.files:
            with open(filename) as f:
                t = Timeseries()
                t.read_meta(f)
            item_time_step = (t.time_step.length_minutes,
                              t.time_step.length_months)
            if time_step and (item_time_step != time_step):
                raise WrongValueError(
                    'Not all time series have the same step')
            time_step = item_time_step
        return time_step

    @property
    def date_fmt(self):
        """
        Determine date_fmt based on time series time step.
        """
        minutes, months = self.time_step
        if minutes and (minutes < 1440):
            return '%Y-%m-%d %H:%M%z'
        if minutes and (minutes >= 1440):
            return '%Y-%m-%d'
        if months and (months < 12):
            return '%Y-%m'
        if months and (months >= 12):
            return '%Y'
        raise ValueError("Can't use time step " + str(self.time_step))

    def delete_obsolete_files(self):
        """
        Delete all tif files produced in the past except the last N,
        where N is the 'number_of_output_files' configuration option.
        """
        n = int(self.config['General']['number_of_output_files'])
        output_dir = self.config['General']['output_dir']
        filename_prefix = self.config['General']['filename_prefix']
        pattern = os.path.join(output_dir, '{}-*.tif'.format(filename_prefix))
        files = glob(pattern)
        files.sort()
        for filename in files[:-n]:
            os.remove(filename)

    def execute(self):
        # Create stations layer
        stations = ogr.GetDriverByName('memory').CreateDataSource('stations')
        epsg = int(self.config['General']['epsg'])
        stations_layer = create_ogr_layer_from_timeseries(self.files, epsg,
                                                          stations)

        # Get mask
        mask = gdal.Open(self.config['General']['mask'])

        # Setup integration method
        if self.config['General']['method'] == 'idw':
            funct = idw
            kwargs = {'alpha': float(self.config['General']['alpha']), }
        else:
            assert False

        output_dir = self.config['General']['output_dir']
        filename_prefix = self.config['General']['filename_prefix']
        for date in self.dates_to_calculate:
            self.logger.info('Processing date ' + date.isoformat())
            h_integrate(mask, stations_layer, date,
                        os.path.join(output_dir, filename_prefix),
                        self.date_fmt, funct, kwargs)
        self.delete_obsolete_files()
