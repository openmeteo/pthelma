from datetime import timedelta
from glob import glob
from math import isnan
import os

import numpy as np
from osgeo import ogr, osr, gdal
from simpletail import ropen

from pthelma.cliapp import CliApp, WrongValueError
from pthelma.timeseries import Timeseries, datetime_from_iso, datestr_diff, \
    add_months_to_datetime


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
    interpolate = np.vectorize(interpolate_one_point,
                               otypes=[np.float32, np.float32, np.bool])

    # Make the calculation
    target_band.WriteArray(interpolate(xarray, yarray, mask))


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


def h_integrate(mask, stations_layer, date, output_filename, date_fmt,
                funct, kwargs):
    # Return immediately if output file already exists
    if os.path.exists(output_filename):
        return

    # Read the time series values and add the 'value' attribute to
    # stations_layer
    stations_layer.CreateField(ogr.FieldDefn('value', ogr.OFTReal))
    found_value = False
    stations_layer.ResetReading()
    for station in stations_layer:
        filename = station.GetField('filename')
        t = Timeseries()
        with open(filename) as f:
            t.read_file(f)
        value = t.get(date, float('NaN'))
        station.SetField('value', value)
        found_value = found_value or (not isnan(value))
        stations_layer.SetFeature(station)
    if not found_value:
        return

    # Create destination data source
    output = gdal.GetDriverByName('GTiff').Create(
        output_filename, mask.RasterXSize, mask.RasterYSize, 1,
        gdal.GDT_Float32)
    if not output:
        raise IOError('An error occured when trying to open {}'.format(
            output_filename))
    output.SetMetadataItem('TIMESTAMP', date.strftime(date_fmt))

    try:
        # Set geotransform and projection in the output data source
        output.SetGeoTransform(mask.GetGeoTransform())
        output.SetProjection(mask.GetProjection())

        # Do the integration
        integrate(mask, stations_layer, output.GetRasterBand(1), funct, kwargs)
    finally:
        # Close the dataset
        output = None


class BitiaApp(CliApp):
    name = 'bitia'
    description = 'Perform spatial integration'
                        # Section          Option            Default
    config_file_options = {'General': {'mask':             None,
                                       'epsg':             None,
                                       'output_dir':       None,
                                       'filename_prefix':  None,
                                       'files_to_produce': None,
                                       'method':           None,
                                       'alpha':            '1',
                                       'files':            None,
                                       },
                           }

    def read_configuration(self):
        super(BitiaApp, self).read_configuration()
        self.files = self.config['General']['files'].split('\n')

    def check_configuration(self):
        super(BitiaApp, self).check_configuration()
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

    @property
    def last_date(self):
        """
        Return the last date for which any time series has data, or None if
        all time series are empty.
        """
        result = None
        for filename in self.files:
            last_date = None
            if not os.path.exists(filename):
                continue
            with ropen(filename) as fp:
                for line in fp:
                    if not line.strip():
                        break  # Time series has no data
                    datestring = line.split(',')[0]
                    try:
                        last_date = datetime_from_iso(datestring)
                    except ValueError as e:
                        raise ValueError(e.message + ' (file {}, last line)'
                                         .format(filename))
                    break  # We only want to do this for the last line
            if last_date and ((not result) or (last_date > result)):
                result = last_date
        return result

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
            return '%Y-%m-%d %H:%M'
        if minutes and (minutes >= 1440):
            return '%Y-%m-%d'
        if months and (months < 12):
            return '%Y-%m'
        if months and (months >= 12):
            return '%Y'
        raise ValueError("Can't use time step " + str(self.time_step))

    def rename_existing_files(self, last_date):
        """
        Assume filename_prefix-XXXX files exist, where XXXX goes from 0 to N-1,
        where N is the 'files_to_produce' configuration option. This method
        renames (by increasing XXXX) so that if a new file with XXXX=000 is
        created for the specified last_date, the existing ones will be properly
        numbered (usually XXXX is increased by one, but it can be more if the
        system failed to run for some time steps).  It also removes files with
        resulting XXXX >= N.
        """
        output_dir = self.config['General']['output_dir']
        filename_prefix = self.config['General']['filename_prefix']
        pattern = os.path.join(output_dir, '{}-*.tif'.format(filename_prefix))
        files = glob(pattern)
        files.sort(reverse=True)
        for filename in files:
            self.do_rename_file(filename, last_date)

    def do_rename_file(self, filename, last_date):
        # Get the file's timestamp
        fp = gdal.Open(filename)
        timestamp = fp.GetMetadata()['TIMESTAMP']
        fp = None

        # What should the file's number be?
        number = self.get_file_number(last_date, timestamp)

        # Is the file too old? Delete it.
        if number >= int(self.config['General']['files_to_produce']):
            os.unlink(filename)
            return

        # Get the file's current number and rename the file
        cur_number = int(filename.rpartition('-')[2].split('.')[0])
        if number != cur_number:
            new_filename = os.path.join(
                self.config['General']['output_dir'],
                '{}-{:04d}.tif'.format(
                    self.config['General']['filename_prefix'], number))
            os.rename(filename, new_filename)

    def get_file_number(self, last_date, timestamp, filename=''):
        """
        Return the number a file should have for the given last_date and
        timestamp. If the two days are equal, the result is 0; otherwise
        it is the number of time steps between them, or 10000 if the
        difference is too large. The filename is used for error messages.
        """
        diff_months, diff_minutes = datestr_diff(last_date, timestamp)
        step_minutes, step_months = self.time_step
        if step_months:  # Monthly or annual
            number = int(diff_months / step_months)
            if diff_minutes or (number * step_months != diff_months):
                raise ValueError("Something's wrong in the timestamp in {}"
                                 .format(filename))
        else:
            number = int(diff_minutes / step_minutes)
            if number * step_minutes != diff_minutes:
                raise ValueError("Something's wrong in the timestamp in {}"
                                 .format(filename))
            if diff_months:
                number = 10000
        return number

    def execute(self):
        # Create stations layer
        stations = ogr.GetDriverByName('memory').CreateDataSource('stations')
        epsg = int(self.config['General']['epsg'])
        stations_layer = create_ogr_layer_from_timeseries(self.files, epsg,
                                                          stations)

        # Get mask
        mask = gdal.Open(self.config['General']['mask'])
        if mask is None:
            raise IOError('An error occured when trying to open {}'.format(
                self.config['General']['mask']))

        # Setup integration method
        if self.config['General']['method'] == 'idw':
            funct = idw
            kwargs = {'alpha': float(self.config['General']['alpha']), }
        else:
            assert False

        # Rename existing files and remove old files
        last_date_str = self.last_date.strftime(self.date_fmt)
        self.rename_existing_files(last_date_str)

        # Make calculation for each missing file
        output_dir = self.config['General']['output_dir']
        filename_prefix = self.config['General']['filename_prefix']
        date_to_calculate = self.last_date
        while True:
            dtc_str = date_to_calculate.strftime(self.date_fmt)
            number = self.get_file_number(last_date_str, dtc_str)
            if number >= int(self.config['General']['files_to_produce']):
                break
            filename = os.path.join(
                output_dir, '{}-{:04d}.tif'.format(filename_prefix, number))
            h_integrate(mask, stations_layer, date_to_calculate, filename,
                        self.date_fmt, funct, kwargs)
            step_minutes, step_months = self.time_step
            if step_months:
                date_to_calculate = add_months_to_datetime(date_to_calculate,
                                                           -step_months)
            else:
                date_to_calculate = date_to_calculate - timedelta(
                    minutes=step_minutes)
