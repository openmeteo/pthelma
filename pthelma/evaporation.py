from datetime import timedelta
from glob import glob
import math
from math import cos, pi, sin, tan
import os
import warnings

import iso8601
import numpy as np
from osgeo import gdal, ogr, osr

from pthelma.cliapp import CliApp, WrongValueError
from pthelma.spatial import NODATAVALUE
from pthelma.timeseries import Timeseries, TimeStep

gdal.UseExceptions()

# Note about RuntimeWarning
#
# When numpy makes calculations with masked arrays, it sometimes emits spurious
# RuntimeWarnings. This is because it occasionally does use the masked part of
# the array during the calculations (but masks the result). This is a known
# numpy bug (e.g. https://github.com/numpy/numpy/issues/4269). The numpy
# documentation, section "Operations on masked arrays", also has a related
# warning there.
#
# In order to avoid these spurious warnings, we have used, at various places in
# the code, "with warnings.catch_warnings()". We have attempted to unit test
# it, but sometimes it's hard to make the bug appear. A large array in
# production may cause the bug, but a small array in the unit test might not
# cause it, despite same python and numpy version. So the locations in which
# a fix was needed were largely located in production.


class PenmanMonteith(object):
    # Stefan-Boltzmann constant (Allen et al., 1998, p. 52)
    sigma = 4.903e-9

    def __init__(self, albedo, elevation, latitude, step_length,
                 longitude=None, nighttime_solar_radiation_ratio=None,
                 unit_converters={}):
        self.albedo = albedo
        self.nighttime_solar_radiation_ratio = nighttime_solar_radiation_ratio
        self.elevation = elevation
        self.latitude = latitude
        self.longitude = longitude
        self.step_length = step_length
        self.unit_converters = unit_converters

    def calculate(self, **kwargs):
        if self.step_length == timedelta(minutes=60):
            return self.calculate_hourly(**kwargs)
        elif self.step_length == timedelta(days=1):
            return self.calculate_daily(**kwargs)
        else:
            raise NotImplementedError(
                "Evaporation for time steps other than hourly and daily "
                "has not been implemented.")

    def calculate_daily(self, temperature_max, temperature_min, humidity_max,
                        humidity_min, wind_speed, adatetime,
                        sunshine_duration=None, pressure=None,
                        solar_radiation=None):
        if pressure is None:
            # Eq. 7 p. 31
            pressure = 101.3 * ((293 - 0.0065 * self.elevation) / 293) ** 5.26
        variables = self.convert_units(temperature_max=temperature_max,
                                       temperature_min=temperature_min,
                                       humidity_max=humidity_max,
                                       humidity_min=humidity_min,
                                       wind_speed=wind_speed,
                                       sunshine_duration=sunshine_duration,
                                       pressure=pressure)

        # Radiation
        r_a, N = self.get_extraterrestrial_radiation(adatetime)
        if solar_radiation is None:
            solar_radiation = (0.25 + 0.50 * variables['sunshine_duration'] / N
                               ) * r_a  # Eq.35 p. 50
        r_so = r_a * (0.75 + 2e-5 * self.elevation)  # Eq. 37, p. 51
        variables.update(self.convert_units(solar_radiation=solar_radiation))

        with warnings.catch_warnings():
            # See comment about RuntimeWarning on top of the file
            warnings.simplefilter('ignore', RuntimeWarning)
            temperature_mean = (variables['temperature_max']
                                + variables['temperature_min']) / 2
        variables['temperature_mean'] = temperature_mean
        gamma = self.get_psychrometric_constant(temperature_mean,
                                                pressure)
        return self.penman_monteith_daily(
            incoming_solar_radiation=variables['solar_radiation'],
            clear_sky_solar_radiation=r_so,
            psychrometric_constant=gamma,
            mean_wind_speed=variables['wind_speed'],
            temperature_max=variables['temperature_max'],
            temperature_min=variables['temperature_min'],
            temperature_mean=variables['temperature_mean'],
            humidity_max=variables['humidity_max'],
            humidity_min=variables['humidity_min'],
            adate=adatetime)

    def calculate_hourly(self, temperature, humidity, wind_speed,
                         solar_radiation, adatetime, pressure=None):
        if pressure is None:
            # Eq. 7 p. 31
            pressure = 101.3 * ((293 - 0.0065 * self.elevation) / 293) ** 5.26
        variables = self.convert_units(temperature=temperature,
                                       humidity=humidity,
                                       wind_speed=wind_speed,
                                       pressure=pressure,
                                       solar_radiation=solar_radiation)
        gamma = self.get_psychrometric_constant(variables['temperature'],
                                                variables['pressure'])
        r_so = self.get_extraterrestrial_radiation(adatetime) * (
            0.75 + 2e-5 * self.elevation)  # Eq. 37, p. 51
        return self.penman_monteith_hourly(
            incoming_solar_radiation=variables['solar_radiation'],
            clear_sky_solar_radiation=r_so,
            psychrometric_constant=gamma,
            mean_wind_speed=variables['wind_speed'],
            mean_temperature=variables['temperature'],
            mean_relative_humidity=variables['humidity'],
            adatetime=adatetime
        )

    def convert_units(self, **kwargs):
        result = {}
        for item in kwargs:
            varname = item
            if item.endswith('_max') or item.endswith('_min'):
                varname = item[:-4]
            converter = self.unit_converters.get(varname, lambda x: x)
            with warnings.catch_warnings():
                # See comment about RuntimeWarning on top of the file
                warnings.simplefilter('ignore', RuntimeWarning)
                result[item] = converter(kwargs[item])
        return result

    def get_extraterrestrial_radiation(self, adatetime):
        """
        Calculates the solar radiation we would receive if there were no
        atmosphere. This is a function of date, time and location.

        If adatetime is a datetime object, it merely returns the
        extraterrestrial radiation R_a; if it is a date object, it returns a
        tuple, (R_a, N), where N is the daylight hours.
        """
        j = adatetime.timetuple().tm_yday  # Day of year

        # Inverse relative distance Earth-Sun, eq. 23, p. 46.
        dr = 1 + 0.033 * cos(2 * pi * j / 365)

        # Solar declination, eq. 24, p. 46.
        decl = 0.409 * sin(2 * pi * j / 365 - 1.39)

        if self.step_length > timedelta(minutes=60):  # Daily?
            phi = self.latitude / 180.0 * pi
            omega_s = np.arccos(-np.tan(phi) * tan(decl))  # Eq. 25 p. 46

            r_a = 24 * 60 / pi * 0.0820 * dr * (
                omega_s * np.sin(phi) * sin(decl)
                + np.cos(phi) * cos(decl) * np.sin(omega_s))  # Eq. 21 p. 46
            n = 24 / pi * omega_s  # Eq. 34 p. 48
            return r_a, n

        # Seasonal correction for solar time, eq. 32, p. 48.
        b = 2 * pi * (j - 81) / 364
        sc = 0.1645 * sin(2 * b) - 0.1255 * cos(b) - 0.025 * sin(b)

        # Longitude at the centre of the local time zone
        utc_offset = adatetime.utcoffset()
        utc_offset_hours = utc_offset.days * 24 + utc_offset.seconds / 3600.0
        lz = -utc_offset_hours * 15

        # Solar time angle at midpoint of the time period, eq. 31, p. 48.
        tm = adatetime - self.step_length / 2
        t = tm.hour + tm.minute / 60.0
        omega = pi / 12 * ((t + 0.06667 * (lz + self.longitude) + sc) - 12)

        # Solar time angles at beginning and end of the period, eqs. 29 and 30,
        # p. 48.
        t1 = self.step_length.seconds / 3600.0
        omega1 = omega - pi * t1 / 24
        omega2 = omega + pi * t1 / 24

        # Result: eq. 28, p. 47.
        phi = self.latitude / 180.0 * pi
        return 12 * 60 / pi * 0.0820 * dr * (
            (omega2 - omega1) * np.sin(phi) * sin(decl)
            + np.cos(phi) * cos(decl) * (np.sin(omega2) - np.sin(omega1)))

    def get_psychrometric_constant(self, temperature, pressure):
        """
        Allen et al. (1998), eq. 8, p. 32.

        This is called a "constant" because, although it is a function of
        temperature and pressure, its variations are small, and therefore it
        can be assumed constant for a location assuming standard pressure at
        that elevation and 20 degrees C. However, here we actually calculate
        it, so it isn't a constant.
        """
        lambda_ = 2.501 - (2.361e-3) * temperature  # eq. 3-1, p. 223
        return 1.013e-3 * pressure / 0.622 / lambda_

    def penman_monteith_daily(
            self, incoming_solar_radiation, clear_sky_solar_radiation,
            psychrometric_constant, mean_wind_speed, temperature_max,
            temperature_min, temperature_mean, humidity_max, humidity_min,
            adate):
        """
        Calculates and returns the reference evapotranspiration according
        to Allen et al. (1998), eq. 6, p. 24 & 65.
        """

        # Saturation and actual vapour pressure
        svp_max = self.get_saturation_vapour_pressure(temperature_max)
        svp_min = self.get_saturation_vapour_pressure(temperature_min)
        avp1 = svp_max * humidity_min / 100
        avp2 = svp_min * humidity_max / 100
        svp = (svp_max + svp_min) / 2  # Eq. 12 p. 36
        avp = (avp1 + avp2) / 2  # Eq. 12 p. 36

        # Saturation vapour pressure curve slope
        delta = self.get_saturation_vapour_pressure_curve_slope(
            temperature_mean)

        # Net incoming radiation; p. 51, eq. 38
        albedo = self.albedo[adate.month - 1] \
            if self.albedo.__class__.__name__ in ('tuple', 'list') \
            else self.albedo
        rns = (1.0 - albedo) * incoming_solar_radiation

        # Net outgoing radiation
        rnl = self.get_net_outgoing_radiation(
            (temperature_min, temperature_max), incoming_solar_radiation,
            clear_sky_solar_radiation, avp)

        # Net radiation at grass surface
        rn = rns - rnl

        # Soil heat flux
        g_day = 0  # Eq. 42 p. 54

        # Apply the formula
        numerator_term1 = 0.408 * delta * (rn - g_day)
        numerator_term2 = psychrometric_constant * 900 / \
            (temperature_mean + 273.16) * mean_wind_speed * (svp - avp)
        denominator = delta + psychrometric_constant * (1 +
                                                        0.34 * mean_wind_speed)

        return (numerator_term1 + numerator_term2) / denominator

    def penman_monteith_hourly(self, incoming_solar_radiation,
                               clear_sky_solar_radiation,
                               psychrometric_constant,
                               mean_wind_speed, mean_temperature,
                               mean_relative_humidity, adatetime):
        """
        Calculates and returns the reference evapotranspiration according
        to Allen et al. (1998), eq. 53, p. 74.

        As explained in Allen et al. (1998, p. 74), the function is
        modified in relation to the original Penman-Monteith equation, so
        that it is suitable for hourly data.
        """

        # Saturation and actual vapour pressure
        svp = self.get_saturation_vapour_pressure(mean_temperature)
        with warnings.catch_warnings():
            # See comment about RuntimeWarning on top of the file
            warnings.simplefilter('ignore', RuntimeWarning)
            avp = svp * mean_relative_humidity / 100.0  # Eq. 54, p. 74

        # Net incoming radiation; p. 51, eq. 38
        albedo = self.albedo[adatetime.month - 1] \
            if self.albedo.__class__.__name__ in ('tuple', 'list') \
            else self.albedo
        rns = (1.0 - albedo) * incoming_solar_radiation

        # Net outgoing radiation
        rnl = self.get_net_outgoing_radiation(mean_temperature,
                                              incoming_solar_radiation,
                                              clear_sky_solar_radiation,
                                              avp)

        # Net radiation at grass surface
        rn = rns - rnl

        # Saturation vapour pressure curve slope
        delta = self.get_saturation_vapour_pressure_curve_slope(
            mean_temperature)

        # Soil heat flux density
        g = self.get_soil_heat_flux_density(incoming_solar_radiation, rn)

        # Apply the formula
        numerator_term1 = 0.408 * delta * (rn - g)
        with warnings.catch_warnings():
            # See comment about RuntimeWarning on top of the file
            warnings.simplefilter('ignore', RuntimeWarning)
            numerator_term2 = psychrometric_constant * 37 / \
                (mean_temperature + 273.16) * mean_wind_speed * (svp - avp)
        denominator = delta + psychrometric_constant * (1 +
                                                        0.34 * mean_wind_speed)

        return (numerator_term1 + numerator_term2) / denominator

    def get_net_outgoing_radiation(self, temperature,
                                   incoming_solar_radiation,
                                   clear_sky_solar_radiation,
                                   mean_actual_vapour_pressure):
        """
        Allen et al. (1998), p. 52, eq. 39. Temperature can be a tuple (a pair)
        of min and max, or a single value. If it is a single value, the
        equation is modified according to end of page 74.
        """
        if temperature.__class__.__name__ in ('tuple', 'list'):
            factor1 = self.sigma * ((temperature[0] + 273.16) ** 4 +
                                    (temperature[1] + 273.16) ** 4) / 2
        else:
            with warnings.catch_warnings():
                # See comment about RuntimeWarning on top of the file
                warnings.simplefilter('ignore', RuntimeWarning)
                factor1 = self.sigma / 24 * (temperature + 273.16) ** 4
        factor2 = 0.34 - 0.14 * (mean_actual_vapour_pressure ** 0.5)

        # Solar radiation ratio Rs/Rs0 (Allen et al., 1998, top of p. 75).
        with warnings.catch_warnings():
            # See comment about RuntimeWarning on top of the file
            warnings.simplefilter('ignore', RuntimeWarning)
            solar_radiation_ratio = np.where(
                clear_sky_solar_radiation > 0.05,
                incoming_solar_radiation / clear_sky_solar_radiation,
                self.nighttime_solar_radiation_ratio)
        solar_radiation_ratio = np.maximum(solar_radiation_ratio, 0.3)
        solar_radiation_ratio = np.minimum(solar_radiation_ratio, 1.0)

        factor3 = 1.35 * solar_radiation_ratio - 0.35

        return factor1 * factor2 * factor3

    def get_saturation_vapour_pressure(self, temperature):
        "Allen et al. (1998), p. 36, eq. 11."
        with warnings.catch_warnings():
            # See comment about RuntimeWarning on top of the file
            warnings.simplefilter('ignore')
            return 0.6108 * math.e ** (17.27 *
                                       temperature / (237.3 + temperature))

    def get_soil_heat_flux_density(self, incoming_solar_radiation, rn):
        "Allen et al. (1998), p. 55, eq. 45 & 46."
        coefficient = np.where(incoming_solar_radiation > 0.05, 0.1, 0.5)
        return coefficient * rn

    def get_saturation_vapour_pressure_curve_slope(self, temperature):
        "Allen et al. (1998), p. 37, eq. 13."
        numerator = 4098 * self.get_saturation_vapour_pressure(temperature)
        with warnings.catch_warnings():
            # See comment about RuntimeWarning on top of the file
            warnings.simplefilter('ignore', RuntimeWarning)
            denominator = (temperature + 237.3) ** 2
            return numerator / denominator


class VaporizeApp(CliApp):
    name = 'vaporize'
    description = 'Calculate evapotranspiration'
    config_file_options = {'General': {
        # Option                           Default
        'base_dir':                        None,
        'step_length':                     None,
        'elevation':                       None,
        'albedo':                          None,
        'nighttime_solar_radiation_ratio': 0.6,
        'unit_converter_temperature':      'x',
        'unit_converter_humidity':         'x',
        'unit_converter_wind_speed':       'x',
        'unit_converter_pressure':         'x',
        'unit_converter_solar_radiation':  'x',
        'temperature_min_prefix':          'temperature_min',
        'temperature_max_prefix':          'temperature_max',
        'temperature_prefix':              'temperature',
        'humidity_prefix':                 'humidity',
        'humidity_min_prefix':             'humidity_min',
        'humidity_max_prefix':             'humidity_max',
        'wind_speed_prefix':               'wind_speed',
        'pressure_prefix':                 'pressure',
        'solar_radiation_prefix':          'solar_radiation',
        'sunshine_duration_prefix':        'sunshine_duration',
        'evaporation_prefix':              'evaporation',
    }}

    def read_configuration(self):
        super(VaporizeApp, self).read_configuration()

        self.read_configuration_step_length()
        self.read_configuration_unit_converters()
        self.base_dir = self.config['General']['base_dir']
        if self.base_dir:
            os.chdir(self.base_dir)
        self.read_configuration_elevation()
        self.read_configuration_albedo()
        self.read_configuration_nighttime_solar_radiation_ratio()

    def read_configuration_step_length(self):
        s = self.config['General']['step_length']
        try:
            minutes = int(s)
            if minutes not in (60, 1440):
                raise ValueError("only hourly or daily in this version")
        except ValueError:
            raise WrongValueError(
                '"{}" is not an appropriate time step; in this version of '
                'vaporize, the step must be either 60 or 1440.'.format(s))
        self.step = timedelta(minutes=minutes)

    def get_number_or_grid(self, s):
        """
        If string s holds a valid number, return it; otherwise try to open the
        geotiff file whose filename is s and read its first band into the
        returned numpy array.
        """
        try:
            return float(s)
        except ValueError:
            pass
        input_file = gdal.Open(s)
        result = input_file.GetRasterBand(1).ReadAsArray()
        nodata = input_file.GetRasterBand(1).GetNoDataValue()
        if nodata is not None:
            result = np.ma.masked_values(result, nodata, copy=False)
        return result

    def read_configuration_elevation(self):
        s = self.config['General']['elevation']
        self.elevation = self.get_number_or_grid(s)
        if np.any(self.elevation < -427) or np.any(self.elevation > 8848):
            raise WrongValueError('The elevation must be between -427 '
                                  'and 8848')

    def check_albedo_domain(self, albedo):
        value_to_test = albedo if isinstance(albedo, float) else albedo.all()
        if value_to_test < 0.0 or value_to_test > 1.0:
            raise ValueError('Albedo must be between 0.0 and 1.0')

    def read_configuration_albedo(self):
        s = self.config['General']['albedo'].split()
        if len(s) not in (1, 12):
            raise ValueError('Albedo must be either one item or 12 '
                             'space-separated items')
        self.albedo = [self.get_number_or_grid(item)
                       for item in s]
        for albedo in self.albedo:
            self.check_albedo_domain(albedo)
        if len(s) == 1:
            self.albedo = self.albedo[0]

    def read_configuration_nighttime_solar_radiation_ratio(self):
        s = self.config['General']['nighttime_solar_radiation_ratio']
        a = self.get_number_or_grid(s)
        self.nighttime_solar_radiation_ratio = a
        if a < 0.4 or a > 0.8:
            raise WrongValueError('The nighttime solar radiation ratio must '
                                  'be between 0.4 and 0.8')

    def read_configuration_unit_converters(self):
        self.unit_converters = {}
        for variable in ('temperature', 'humidity', 'wind_speed', 'pressure',
                         'solar_radiation'):
            config_item = 'unit_converter_' + variable
            config_value = self.config['General'][config_item]
            lambda_defn = 'lambda x: ' + config_value
            try:
                self.unit_converters[variable] = eval(lambda_defn)
            except Exception as e:
                raise WrongValueError(
                    '{} while parsing {} ({}): {}'.format(e.__class__.__name__,
                                                          config_item,
                                                          config_value,
                                                          str(e)))

    def get_coordinates(self):
        """
        Retrieve geographical stuff into self.latitude, self.longitude,
        self.width, self.height, self.geo_transform, self.projection. We do
        this by retrieving the data from self.geographical_reference_file,
        which our caller should have set to one arbitrary from the available
        input files.  Elsewhere other GeoTIFF files are checked for consistency
        with this data.
        """
        # Read data from GeoTIFF file
        fp = gdal.Open(self.geographical_reference_file)
        self.width, self.height = fp.RasterXSize, fp.RasterYSize
        self.geo_transform = fp.GetGeoTransform()
        self.projection = osr.SpatialReference()
        self.projection.ImportFromWkt(fp.GetProjection())

        # Find (x_left, y_top), (x_right, y_bottom)
        x_left, x_step, d1, y_top, d2, y_step = self.geo_transform
        x_right = x_left + self.width * x_step
        y_bottom = y_top + self.height * y_step

        # Transform into (long_left, lat_top), (long_right, lat_bottom)
        wgs84 = osr.SpatialReference()
        wgs84.ImportFromEPSG(4326)
        transform = osr.CoordinateTransformation(self.projection, wgs84)
        top_left = ogr.Geometry(ogr.wkbPoint)
        top_left.AddPoint(x_left, y_top)
        bottom_right = ogr.Geometry(ogr.wkbPoint)
        bottom_right.AddPoint(x_right, y_bottom)
        top_left.Transform(transform)
        bottom_right.Transform(transform)
        long_left, lat_top = top_left.GetX(), top_left.GetY()
        long_right, lat_bottom = bottom_right.GetX(), bottom_right.GetY()

        # Calculate self.latitude and self.longitude
        long_step = (long_right - long_left) / self.width
        longitudes = np.arange(long_left + long_step / 2.0,
                               long_left + long_step * self.width,
                               long_step)
        lat_step = (lat_top - lat_bottom) / self.height
        latitudes = np.arange(lat_top + lat_step / 2.0,
                              lat_top + lat_step * self.height,
                              lat_step)
        self.longitude, self.latitude = np.meshgrid(longitudes, latitudes)

    def execute(self):
        base_dir_has_tif_files = bool(glob('*.tif'))
        base_dir_has_hts_files = bool(glob('*.hts'))
        if base_dir_has_tif_files and base_dir_has_hts_files:
            raise WrongValueError(
                'Base directory {} contains both tif files and hts files; '
                'this is not allowed.'.format(self.base_dir))
        elif base_dir_has_tif_files:
            self.execute_spatial()
        elif base_dir_has_hts_files:
            self.execute_point()
        else:
            raise WrongValueError(
                'Base directory {} contains neither tif files nor hts files.'
                .format(self.base_dir))

    def execute_spatial(self):
        # List all input wind speed files
        pattern = self.config['General']['wind_speed_prefix'] + '-*.tif'
        wind_speed_files = glob(pattern)

        # Remove the prefix from the start and the .tif from the end, leaving
        # only the date.
        prefix_len = len(self.config['General']['wind_speed_prefix'])
        timestamps = [item[prefix_len + 1:-4] for item in wind_speed_files]

        # Arbitrarily use the first temperature file to extract location and
        # other geographical stuff. Elsewhere consistency of such data from all
        # other files with this file will be checked.
        self.geographical_reference_file = wind_speed_files[0]
        self.get_coordinates()

        nsrr = self.nighttime_solar_radiation_ratio
        self.penman_monteith = PenmanMonteith(
            albedo=self.albedo,
            nighttime_solar_radiation_ratio=nsrr,
            elevation=self.elevation,
            latitude=self.latitude,
            longitude=self.longitude,
            step_length=self.step,
            unit_converters=self.unit_converters)
        for timestamp in timestamps:
            self.process_timestamp(timestamp)
        self.remove_extra_evaporation_files(timestamps)

    def execute_point(self):
        # Read input time series
        input_timeseries = {}
        for name in ('temperature_min', 'temperature_max', 'temperature',
                     'humidity', 'humidity_min', 'humidity_max', 'wind_speed',
                     'pressure', 'solar_radiation', 'sunshine_duration'):
            filename = self.config['General'][name + '_prefix'] + '.hts'
            if not os.path.exists(filename):
                continue
            t = Timeseries()
            with open(filename, 'r') as f:
                t.read_file(f)
            input_timeseries[name] = t

        # Make sure all are in the same location and timezone
        first = True
        for index in input_timeseries:
            t = input_timeseries[index]
            if first:
                abscissa = t.location['abscissa']
                ordinate = t.location['ordinate']
                srid = t.location['srid']
                altitude = t.location['altitude']
                timezone = t.timezone
                first = False
                continue
            if abs(abscissa - t.location['abscissa']) > 1e-7 or \
                    abs(ordinate - t.location['ordinate']) > 1e-7 or \
                    srid != t.location['srid'] or \
                    abs(altitude - t.location['altitude']) > 1e-2 or \
                    timezone != t.timezone:
                raise ValueError('Incorrect or unspecified or inconsistent '
                                 'locations or time zones in the time series '
                                 'files.')

        # Convert location to WGS84
        source_projection = osr.SpatialReference()
        source_projection.ImportFromEPSG(srid)
        wgs84 = osr.SpatialReference()
        wgs84.ImportFromEPSG(4326)
        transform = osr.CoordinateTransformation(source_projection, wgs84)
        apoint = ogr.Geometry(ogr.wkbPoint)
        apoint.AddPoint(abscissa, ordinate)
        apoint.Transform(transform)
        latitude, longitude = apoint.GetY(), apoint.GetY()

        # Prepare the Penman Monteith method
        nsrr = self.nighttime_solar_radiation_ratio
        self.penman_monteith = PenmanMonteith(
            albedo=self.albedo,
            nighttime_solar_radiation_ratio=nsrr,
            elevation=altitude,
            latitude=latitude,
            longitude=longitude,
            step_length=self.step,
            unit_converters=self.unit_converters)

        # Create output timeseries object
        pet = Timeseries(
            time_step=TimeStep(length_minutes=self.step.total_seconds() / 60),
            unit='mm',
            timezone=timezone,
            variable='Potential Evapotranspiration',
            precision=1,
            location={'abscissa': abscissa, 'ordinate': ordinate,
                      'srid': srid, 'altitude': altitude})

        # Let's see what variables we are going to use in the calculation,
        # based mainly on the step.
        if self.step == timedelta(hours=1):
            variables = ('temperature', 'humidity', 'wind_speed',
                         'solar radiation')
        elif self.step == timedelta(days=1):
            variables = (
                'temperature_max', 'temperature_min', 'humidity_max',
                'humidity_min', 'wind_speed',
                'solar_radiation' if 'solar_radiation' in input_timeseries
                else 'sunshine_duration')
        else:
            raise Exception(
                'Internal error: step should have been checked already')

        # Calculate evaporation
        for adatetime in input_timeseries['wind_speed']:
            try:
                kwargs = {v: input_timeseries[v][adatetime]
                          for v in variables}
            except IndexError:
                continue
            kwargs['adatetime'] = adatetime
            pet[adatetime] = self.penman_monteith.calculate(**kwargs)

        # Save result
        outfilename = self.config['General']['evaporation_prefix'] + '.hts'
        with open(outfilename, 'w') as f:
            pet.write_file(f)

    def remove_extra_evaporation_files(self, timestamps):
        """
        Remove evaporation files for which no input files exist.
        """
        pattern = self.config['General']['evaporation_prefix'] + '-*.tif'
        evaporation_files = glob(pattern)
        prefix_len = len(self.config['General']['evaporation_prefix'])
        for filename in evaporation_files:
            if filename[prefix_len + 1:-4] not in timestamps:
                os.unlink(filename)

    def timestamp_from_filename(self, s):
        """
        Convert a timestamp from its filename format (e.g.
        2014-10-01-15-00-0100) to its iso format (e.g. 2014-10-01 15:00-0100).
        """
        first_hyphen = s.find('-')
        if first_hyphen < 0:
            return s
        second_hyphen = s.find('-', first_hyphen + 1)
        if second_hyphen < 0:
            return s
        third_hyphen = s.find('-', second_hyphen + 1)
        if third_hyphen < 0:
            return s
        fourth_hyphen = s.find('-', third_hyphen + 1)
        chars = list(s)
        chars[third_hyphen] = ' '
        if fourth_hyphen > 0:
            chars[fourth_hyphen] = ':'
        return ''.join(chars)

    def process_timestamp(self, timestamp):
        if self.step == timedelta(minutes=60):
            input_data = {'temperature': None, 'humidity': None,
                          'wind_speed': None, 'pressure': None,
                          'solar_radiation': None}
        else:
            input_data = {'temperature_max': None, 'temperature_min': None,
                          'humidity_max': None, 'humidity_min': None,
                          'wind_speed': None, 'solar_radiation': None,
                          'sunshine_duration': None}
        for variable in input_data:
            # Open file
            filename_prefix = self.config['General'][variable + '_prefix']
            filename = filename_prefix + '-' + timestamp + '.tif'
            if variable in ('solar_radiation', 'sunshine_duration') and \
                    not os.path.exists(filename):
                # Either solar_radiation or sunshine_duration may be absent;
                # here we allow both to be absent and after the loop we will
                # check that one was present
                continue
            try:
                fp = gdal.Open(filename)
            except RuntimeError:
                if variable == 'pressure':
                    continue
                raise

            # Verify consistency of geographical data
            consistent = all(
                (self.width == fp.RasterXSize,
                 self.height == fp.RasterYSize,
                 self.geo_transform == fp.GetGeoTransform(),
                 self.projection.ExportToWkt() == fp.GetProjection()))
            if not consistent:
                raise Exception('Not all input files have the same '
                                'width, height, geo_transform and projection '
                                '(offending items: {} and {})'
                                .format(self.geographical_reference_file,
                                        filename))

            # Read array
            array = fp.GetRasterBand(1).ReadAsArray()
            nodata = fp.GetRasterBand(1).GetNoDataValue()
            if nodata is not None:
                array = np.ma.masked_values(array, nodata, copy=False)
            input_data[variable] = array

            # Close file
            fp = None

        # Verify that one of solar_radiation and sunshine duration was present
        if input_data['solar_radiation'] is not None:
            input_data.pop('sunshine_duration', None)
        elif input_data.get('sunshine_duration', None) is not None:
            input_data.pop('solar_radiation', None)
        else:
            raise RuntimeError('Neither sunshine_duration nor solar_radiation '
                               'are available for {}.'.format(timestamp))

        input_data['adatetime'] = iso8601.parse_date(
            self.timestamp_from_filename(timestamp), default_timezone=None)
        if (self.step == timedelta(minutes=1440)):
            input_data['adatetime'] = input_data['adatetime'].date()
        if (self.step == timedelta(minutes=60)) and (
                input_data['adatetime'].tzinfo is None):
            raise Exception('The time stamp in the input files does not '
                            'have a time zone specified.')

        result = self.penman_monteith.calculate(**input_data)

        # Create destination data source
        output_filename = self.config['General']['evaporation_prefix'] \
            + '-' + timestamp + '.tif'
        output = gdal.GetDriverByName('GTiff').Create(
            output_filename, self.width, self.height, 1,
            gdal.GDT_Float32)
        try:
            output.SetMetadataItem('TIMESTAMP',
                                   input_data['adatetime'].isoformat())
            output.SetGeoTransform(self.geo_transform)
            output.SetProjection(self.projection.ExportToWkt())
            result[result.mask] = NODATAVALUE
            output.GetRasterBand(1).SetNoDataValue(NODATAVALUE)
            output.GetRasterBand(1).WriteArray(result)
        finally:
            # Close the dataset
            output = None
