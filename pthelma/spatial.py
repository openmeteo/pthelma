from argparse import ArgumentParser
from datetime import datetime, timedelta
import logging
import os
import sys

from six import StringIO
from six.moves import configparser
from six.moves.configparser import RawConfigParser, NoOptionError
from six.moves.urllib.parse import quote_plus

import numpy as np
from osgeo import ogr, gdal
import requests

from pthelma import enhydris_api
from pthelma.timeseries import Timeseries


def idw(point, data_layer, alpha=1):
    data_layer.ResetReading()
    features = [f for f in data_layer]
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
    mask = dataset.GetRasterBand(1).ReadAsArray()

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
                               otypes=[np.float64, np.float64, np.bool])

    # Make the calculation
    target_band.WriteArray(interpolate(xarray, yarray, mask))


def create_ogr_layer_from_stations(group, data_source, cache):
    layer = data_source.CreateLayer('stations')
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
        r.raise_for_status()
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


class IntegrationDateMissingError(Exception):
    pass


def h_integrate(group, mask, stations_layer, cache, date, output_dir,
                filename_prefix, date_fmt, funct, kwargs):

    # Read the time series values and add the 'value' attribute to
    # stations_layer
    stations_layer.CreateField(ogr.FieldDefn('value', ogr.OFTReal))
    for station in stations_layer:
        ts_id = station.GetField('timeseries_id')
        base_url = [t['base_url'] for t in group if t['id'] == ts_id][0]
        cache_filename = cache.get_filename(base_url, ts_id)
        t = Timeseries()
        with open(cache_filename) as f:
            t.read(f)
        try:
            station.SetField('value', t[date])
            stations_layer.SetFeature(station)
        except KeyError:
            raise IntegrationDateMissingError(
                'Timeseries from {} with id={} does not have date {}'
                .format(base_url, ts_id, date))

    # Create destination data source
    output_filename = os.path.join(
        output_dir, '{}-{}.tif'.format(filename_prefix,
                                       date.strftime(date_fmt)))
    output = gdal.GetDriverByName('GTiff').Create(
        output_filename, mask.RasterXSize, mask.RasterYSize, 1,
        gdal.GDT_Float64)

    try:
        # Set geotransform and projection in the output data source
        output.SetGeoTransform(mask.GetGeoTransform())
        output.SetProjection(mask.GetProjection())

        # Do the integration
        integrate(mask, stations_layer, output.GetRasterBand(1), funct, kwargs)
    finally:
        # Close the dataset
        output = None
