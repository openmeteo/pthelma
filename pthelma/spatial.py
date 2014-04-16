from datetime import datetime, timedelta
import os

from six import StringIO
from six.moves.urllib.parse import quote_plus

import numpy as np
from osgeo import ogr, gdal
import requests

from pthelma import enhydris_api
from pthelma.timeseries import Timeseries


def idw(point, data_layer, alpha=1):
    """
    Calculate value with inverse distance weighting method for a
    single point.

    data_layer is an ogr.Layer object containing one or more points
    with values (all data_layer features must be points and must also
    have a value property).  point is an ogr.Point object.  This
    function applies the IDW method to calculate the value of point
    given the values of the points of data_layer.

    Distances are raised to power -alpha; this means that for alpha >
    1, the so-called distance-decay effect will be more than
    proportional to an increase in distance, and vice-versa.
    """
    data_layer.ResetReading()
    features = [f for f in data_layer]
    distances = np.array([point.Distance(f.GetGeometryRef())
                          for f in features])
    values = np.array([f.GetField('value') for f in features])
    invdistances = distances ** (-alpha)
    weights = invdistances / invdistances.sum()
    return (weights * values).sum()


def interpolate_spatially(dataset, data_layer, funct, kwargs={}):
    """
    Perform interpolation on an entire surface.

    dataset is a gdal dataset whose first band is the mask; the
    gridpoints of the mask have value zero or non-zero. data_layer is
    an ogr.Layer object containing one or more points with values (all
    data_layer features must be points and must also have a value
    attribute). funct is a python function whose first two arguments
    are an ogr.Point and data_layer, and kwargs is a dictionary with
    keyword arguments to be given to funct.

    This function calls funct for each non-zero gridpoint of the mask.
    The result is added as a new band to dataset.

    NOTE: It is assumed that there is no x_rotation and y_rotation
    (i.e. that dataset.GetGeoTransform()[3] and [4] are zero).
    """

    # Get the mask and prepare the result band
    mask = dataset.GetRasterBand(1).ReadAsArray()
    dataset.AddBand(gdal.GDT_Float64)
    new_band = dataset.GetRasterBand(dataset.RasterCount)

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
    new_band.WriteArray(interpolate(xarray, yarray, mask))


def create_ogr_layer_from_stations(group, data_source, cache_dir):
    """
    Create and return an ogr.Layer with stations as its points.

    group is a list of dictionaries; each dictionary is an Enhydris time
    series; it has keys 'base_url', 'user', 'password', and 'id'.
    Each time series refers to a station.  This function retrieves the
    co-ordinates of each station from Enhydris (unless we have them cached) and
    creates a layer in the specified ogr data_source whose features are points;
    as many points as there are stations/timeseries; each point is also given a
    timeseries_id attribute.
    """
    layer = data_source.CreateLayer('stations')
    layer.CreateField(ogr.FieldDefn('timeseries_id', ogr.OFTInteger))
    for item in group:
        # Get the point from the cache, or fetch it anew on cache miss
        cache_filename = os.path.join(
            cache_dir,
            'timeseries_{}_{}_point'.format(quote_plus(item['base_url']),
                                            item['id']))
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


def update_timeseries_cache(cache_dir, groups):
    """
    Download the newer part of timeseries from Enhydris.

    We keep some time series in our cache, which we download from Enhydris
    using the Enhydris web service API. This function downloads the part that
    has not already been downloaded (or all the timeseries if nothing is in the
    cache). groups is a dictionary; each item is a list of dictionaries, each
    one representing an Enhydris time series; its keys are base_url, user,
    password, id.
    """

    def update_one_timeseries(base_url, id, user=None, password=None):
        if base_url[-1] != '/':
            base_url += '/'

        # Read timeseries from cache file
        cache_filename = os.path.join(cache_dir, '{}.hts'.format(id))
        ts1 = Timeseries()
        if os.path.exists(cache_filename):
            with open(cache_filename) as f:
                try:
                    ts1.read_file(f)
                except ValueError:
                    # File may be corrupted; continue with empty time series
                    ts1 = Timeseries()

        # Get its end date
        try:
            end_date = ts1.bounding_dates()[1]
        except TypeError:
            # Timeseries is totally empty; no start and end date
            end_date = datetime(1, 1, 1, 0, 0)
        start_date = end_date + timedelta(minutes=1)

        # Get newer timeseries and append it
        session_cookies = enhydris_api.login(base_url, user, password)
        url = base_url + 'timeseries/d/{}/download/{}/'.format(
            id, start_date.isoformat())
        r = requests.get(url, cookies=session_cookies)
        r.raise_for_status()
        ts2 = Timeseries()
        ts2.read_file(StringIO(r.text))
        ts1.append(ts2)

        # Save it
        with open(cache_filename, 'w') as f:
            ts1.write(f)

    for group in groups:
        for item in groups[group]:
            update_one_timeseries(**item)
