from copy import copy
from datetime import datetime, timedelta
from glob import glob
from math import isnan
import os

from six import StringIO
from six.moves.urllib.parse import quote_plus

import numpy as np
from osgeo import ogr, osr, gdal
import requests
from requests.exceptions import HTTPError
from simpletail import ropen

from pthelma import enhydris_api
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


def create_ogr_layer_from_stations(group, epsg, data_source, cache):
    # Prepare the co-ordinate transformation from WGS84 to epsg
    source_sr = osr.SpatialReference()
    source_sr.ImportFromEPSG(4326)
    target_sr = osr.SpatialReference()
    target_sr.ImportFromEPSG(epsg)
    transform = osr.CoordinateTransformation(source_sr, target_sr)

    layer = data_source.CreateLayer('stations', target_sr)
    layer.CreateField(ogr.FieldDefn('timeseries_id', ogr.OFTInteger))
    for item in group:
        # Get the point from the cache, or fetch it anew on cache miss
        cache_filename = cache.get_point_filename(item['base_url'], item['id'])
        try:
            with open(cache_filename) as f:
                pointwkt = f.read()
        except IOError:
            cookies = enhydris_api.login(item['base_url'],
                                         item.get('user', None),
                                         item.get('password', None))
            tsd = enhydris_api.get_model(item['base_url'], cookies,
                                         'Timeseries', item['id'])
            gpoint = enhydris_api.get_model(item['base_url'], cookies,
                                            'Gpoint', tsd['gentity'])
            pointwkt = gpoint['point']
            with open(cache_filename, 'w') as f:
                f.write(pointwkt)

        # Create feature and put it on the layer
        point = ogr.CreateGeometryFromWkt(pointwkt)
        point.Transform(transform)
        f = ogr.Feature(layer.GetLayerDefn())
        f.SetGeometry(point)
        f.SetField('timeseries_id', item['id'])
        layer.CreateFeature(f)
    return layer


class TimeseriesCache(object):

    def __init__(self, cache_dir, timeseries_group):
        self.cache_dir = cache_dir
        self.timeseries_group = timeseries_group

    def get_filename(self, base_url, id):
        return os.path.join(self.cache_dir,
                            '{}_{}.hts'.format(quote_plus(base_url), id))

    def get_point_filename(self, base_url, id):
        return os.path.join(
            self.cache_dir,
            'timeseries_{}_{}_point'.format(quote_plus(base_url),
                                            id))

    def update(self):
        for item in self.timeseries_group:
            self.base_url = item['base_url']
            if self.base_url[-1] != '/':
                self.base_url += '/'
            self.timeseries_id = item['id']
            self.user = item['user']
            self.password = item['password']
            self.update_for_one_timeseries()

    def update_for_one_timeseries(self):
        self.cache_filename = self.get_filename(self.base_url,
                                                self.timeseries_id)
        ts1 = self.read_timeseries_from_cache_file()
        end_date = self.get_timeseries_end_date(ts1)
        start_date = end_date + timedelta(minutes=1)
        self.append_newer_timeseries(start_date, ts1)
        with open(self.cache_filename, 'w') as f:
            ts1.write(f)
        self.save_timeseries_step_to_cache()

    def read_timeseries_from_cache_file(self):
        result = Timeseries()
        if os.path.exists(self.cache_filename):
            with open(self.cache_filename) as f:
                try:
                    result.read_file(f)
                except ValueError:
                    # File may be corrupted; continue with empty time series
                    result = Timeseries()
        return result

    def get_timeseries_end_date(self, timeseries):
        try:
            end_date = timeseries.bounding_dates()[1]
        except TypeError:
            # Timeseries is totally empty; no start and end date
            end_date = datetime(1, 1, 1, 0, 0)
        return end_date

    def append_newer_timeseries(self, start_date, ts1):
        self.session_cookies = enhydris_api.login(self.base_url, self.user,
                                                  self.password)
        url = self.base_url + 'timeseries/d/{}/download/{}/'.format(
            self.timeseries_id, start_date.isoformat())
        r = requests.get(url, cookies=self.session_cookies)
        if r.status_code != 200:
            raise HTTPError('Error {} while getting {}'.format(r.status_code,
                                                               url))
        ts2 = Timeseries()
        ts2.read_file(StringIO(r.text))
        ts1.append(ts2)

    def save_timeseries_step_to_cache(self):
        step_cache_filename = self.cache_filename + '_step'
        if not os.path.exists(step_cache_filename):
            step_id = enhydris_api.get_model(
                self.base_url, self.session_cookies, 'Timeseries',
                self.timeseries_id)['time_step']
            with open(step_cache_filename, 'w') as f:
                f.write(str(step_id))


def h_integrate(group, mask, stations_layer, cache, date, filename, date_fmt,
                funct, kwargs):
    # Return immediately if output file already exists
    if os.path.exists(filename):
        return

    # Read the time series values and add the 'value' attribute to
    # stations_layer
    stations_layer.CreateField(ogr.FieldDefn('value', ogr.OFTReal))
    found_value = False
    stations_layer.ResetReading()
    for station in stations_layer:
        ts_id = station.GetField('timeseries_id')
        base_url = [x['base_url'] for x in group if x['id'] == ts_id][0]
        cache_filename = cache.get_filename(base_url, ts_id)
        t = Timeseries()
        with open(cache_filename) as f:
            t.read(f)
        value = t.get(date, float('NaN'))
        station.SetField('value', value)
        found_value = found_value or (not isnan(value))
        stations_layer.SetFeature(station)
    if not found_value:
        return

    # Create destination data source
    output = gdal.GetDriverByName('GTiff').Create(
        filename, mask.RasterXSize, mask.RasterYSize, 1, gdal.GDT_Float32)
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
                                       'cache_dir':        None,
                                       'output_dir':       None,
                                       'filename_prefix':  None,
                                       'files_to_produce': None,
                                       'method':           None,
                                       'alpha':            '1',
                                       },
                           'other':   {'base_url':         None,
                                       'id':               None,
                                       'user':             '',
                                       'password':         '',
                                       },
                           }

    def read_configuration(self):
        super(BitiaApp, self).read_configuration()

        # Convert all sections but 'General' into a list of time series
        self.timeseries_group = []
        for section in self.config:
            if section == 'General':
                continue
            item = copy(self.config[section])
            item['name'] = section
            item['id'] = int(item['id'])
            self.timeseries_group.append(item)

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
        for item in self.timeseries_group:
            filename = self.cache.get_filename(item['base_url'], item['id'])
            if not os.path.exists(filename):
                continue
            with ropen(filename) as fp:
                for line in fp:
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
        for all time series, raises exception. Must be run after updating
        cache.
        """
        time_step = None
        for item in self.timeseries_group:
            timestep_filename = self.cache.get_filename(
                item['base_url'], item['id']) + '_step'
            with open(timestep_filename) as f:
                item_time_step = int(f.read())
            if time_step and (item_time_step != time_step):
                raise WrongValueError(
                    'Not all time series have the same step')
            time_step = item_time_step
        return time_step

    @property
    def date_fmt(self):
        """
        Determine date_fmt based on time series time step.
        Call after updating self.cache.
        """
        return {1: '%Y-%m-%d %H:%M',
                2: '%Y-%m-%d %H:%M',
                3: '%Y-%m-%d',
                4: '%Y-%m',
                5: '%Y',
                6: '%Y-%m-%d %H:%M',
                7: '%Y-%m-%d %H:%M'}[self.time_step]

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
        divider = [10, 60, 1440, 1, 12, 5, 15][self.time_step - 1]
        if self.time_step in (4, 5):  # Monthly or annual
            number = diff_months / divider
            if diff_minutes or (number * divider != diff_months):
                raise ValueError("Something's wrong in the timestamp in {}"
                                 .format(filename))
        else:
            number = diff_minutes / divider
            if number * divider != diff_minutes:
                raise ValueError("Something's wrong in the timestamp in {}"
                                 .format(filename))
            if diff_months:
                number = 10000
        return number

    def execute(self, update_cache=True):
        # Setup cache
        cache_dir = self.config['General']['cache_dir']
        self.cache = TimeseriesCache(cache_dir, self.timeseries_group)
        if update_cache:
            # update_cache may be False only during unit tests
            self.cache.update()

        # Create stations layer
        stations = ogr.GetDriverByName('memory').CreateDataSource('stations')
        epsg = int(self.config['General']['epsg'])
        stations_layer = create_ogr_layer_from_stations(
            self.timeseries_group, epsg, stations, self.cache)

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
        self.rename_existing_files(self.last_date)

        # Make calculation for each missing file
        output_dir = self.config['General']['output_dir']
        filename_prefix = self.config['General']['filename_prefix']
        date_to_calculate = self.last_date
        last_date_str = self.last_date.strftime(self.date_fmt)
        while True:
            dtc_str = date_to_calculate.strftime(self.date_fmt)
            number = self.get_file_number(last_date_str, dtc_str)
            if number >= int(self.config['General']['files_to_produce']):
                break
            filename = os.path.join(
                output_dir, '{}-{:04d}.tif'.format(filename_prefix, number))
            h_integrate(self.timeseries_group, mask, stations_layer,
                        self.cache, date_to_calculate, filename, self.date_fmt,
                        funct, kwargs)
            step = [10, 60, 1440, 1, 12, 5, 15][self.time_step - 1]
            if self.time_step in (4, 5):
                date_to_calculate = add_months_to_datetime(date_to_calculate,
                                                           -step)
            else:
                date_to_calculate = date_to_calculate - timedelta(minutes=step)
