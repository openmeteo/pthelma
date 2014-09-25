from datetime import timedelta
import math
from math import cos, pi, sin
import os

import iso8601
import numpy as np
from osgeo import gdal, ogr, osr

from pthelma.cliapp import CliApp, WrongValueError


class PenmanMonteith(object):
    sigma = 2.043e-10  # Modified Stefan-Boltzmann constant (Allen et al.,
                       # 1998, end of p. 74)

    def __init__(self, albedo, nighttime_solar_radiation_ratio, elevation,
                 latitude, longitude, step_length, unit_converters={}):
        self.albedo = albedo
        self.nighttime_solar_radiation_ratio = nighttime_solar_radiation_ratio
        self.elevation = elevation
        self.latitude = latitude
        self.longitude = longitude
        self.step_length = step_length
        self.unit_converters = unit_converters

    def calculate(self, temperature, humidity, wind_speed, pressure,
                  solar_radiation, adatetime):
        if self.step_length > timedelta(minutes=60):
            raise NotImplementedError("Evaporation for time steps "
                                      "larger than hourly has not been "
                                      "implemented.")
        variables = self.convert_units(temperature=temperature,
                                       humidity=humidity,
                                       wind_speed=wind_speed,
                                       pressure=pressure,
                                       solar_radiation=solar_radiation)
        gamma = self.get_psychrometric_constant(variables['temperature'],
                                                variables['pressure'])
        r_so = self.get_extraterrestrial_radiation(adatetime) * (
            0.75 + 2e-5 * self.elevation)  # Eq. 37, p. 51
        return self.penman_monteith(
            incoming_solar_radiation=variables['solar_radiation'],
            clear_sky_solar_radiation=r_so,
            psychrometric_constant=gamma,
            mean_wind_speed=variables['wind_speed'],
            mean_temperature=variables['temperature'],
            mean_relative_humidity=variables['humidity'])

    def convert_units(self, **kwargs):
        result = {}
        for item in kwargs:
            result[item] = self.unit_converters.get(item, lambda x: x)(
                kwargs[item])
        return result

    def get_extraterrestrial_radiation(self, adatetime):
        """
        Calculates the solar radiation we would receive if there were no
        atmosphere. This is a function of date, time and location.
        """

        j = adatetime.timetuple().tm_yday  # Day of year

        # Inverse relative distance Earth-Sun, eq. 23, p. 46.
        dr = 1 + 0.033 * cos(2 * pi * j / 365)

        # Solar declination, eq. 24, p. 46.
        decl = 0.409 * sin(2 * pi * j / 365 - 1.39)

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

    def penman_monteith(self, incoming_solar_radiation,
                        clear_sky_solar_radiation,
                        psychrometric_constant,
                        mean_wind_speed, mean_temperature,
                        mean_relative_humidity):
        """
        Calculates and returns the reference evapotranspiration according
        to Allen et al. (1998), eq. 53, p. 74.

        As explained in Allen et al. (1998, p. 74), the function is
        modified in relation to the original Penman-Monteith equation, so
        that it is suitable for hourly data.
        """

        # Saturation and actual vapour pressure
        svp = self.get_saturation_vapour_pressure(mean_temperature)
        avp = svp * mean_relative_humidity / 100.0  # Eq. 54, p. 74

        # Net incoming radiation; p. 51, eq. 38
        rns = (1.0 - self.albedo) * incoming_solar_radiation

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
        numerator_term2 = psychrometric_constant * 37 / \
            (mean_temperature + 273.16) * mean_wind_speed * (svp - avp)
        denominator = delta + psychrometric_constant * (1 +
                                                        0.34 * mean_wind_speed)

        return (numerator_term1 + numerator_term2) / denominator

    def get_net_outgoing_radiation(self, mean_temperature,
                                   incoming_solar_radiation,
                                   clear_sky_solar_radiation,
                                   mean_actual_vapour_pressure):
        """
        Allen et al. (1998), p. 52, eq. 39, modified according to end of page
        74.
        """
        factor1 = self.sigma * (mean_temperature + 273.16) ** 4
        factor2 = 0.34 - 0.14 * (mean_actual_vapour_pressure ** 0.5)

        # Solar radiation ratio Rs/Rs0 (Allen et al., 1998, top of p. 75).
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
        return 0.6108 * math.e ** (17.27 * temperature / (237.3 + temperature))

    def get_soil_heat_flux_density(self, incoming_solar_radiation, rn):
        "Allen et al. (1998), p. 55, eq. 45 & 46."
        coefficient = np.where(incoming_solar_radiation > 0.05, 0.1, 0.5)
        return coefficient * rn

    def get_saturation_vapour_pressure_curve_slope(self, temperature):
        "Allen et al. (1998), p. 37, eq. 13."
        numerator = 4098 * self.get_saturation_vapour_pressure(temperature)
        denominator = (temperature + 237.3) ** 2
        return numerator / denominator


class GerardaApp(CliApp):
    name = 'gerarda'
    description = 'Calculate evapotranspiration'
                          # Section     Option            Default
    config_file_options = {'General': {'base_dir':        None,
                                       'step_length':     None,
                                       'elevation':       None,
                                       'albedo':          None, 
                                       'nighttime_solar_radiation_ratio': None,
                                       'unit_converter_temperature':      'x',
                                       'unit_converter_humidity':         'x',
                                       'unit_converter_wind_speed':       'x',
                                       'unit_converter_pressure':         'x',
                                       'unit_converter_solar_radiation':  'x',
                                       },
                           'other':   {'temperature':     None,
                                       'humidity':        None,
                                       'wind_speed':      None,
                                       'pressure':        None,
                                       'solar_radiation': None,
                                       'result':          None,
                                       },
                           }

    def read_configuration(self):
        super(GerardaApp, self).read_configuration()

        self.read_configuration_step_length()
        self.read_configuration_unit_converters()
        self.base_dir = self.config['General']['base_dir']
        if self.base_dir:
            os.chdir(self.base_dir)
        self.read_configuration_elevation()
        self.read_configuration_albedo()
        self.read_configuration_nighttime_solar_radiation_ratio()
        if len(self.config) <= 1:
            raise WrongValueError(
                'Configuration file must contain at least one section '
                'other than General')

    def read_configuration_step_length(self):
        s = self.config['General']['step_length']
        try:
            minutes = int(s)
            if minutes > 60 or minutes < 1:
                raise ValueError("only up to hourly in this version")
        except ValueError:
            raise WrongValueError(
                '"{}" is not an appropriate time step; in this version of '
                'gerarda, the step must be an integer number of minutes '
                'smaller than or equal to 60.'.format(s))
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
        if input_file is None:
            raise IOError('An error occured when trying to open {}'.format(s))
        return input_file.GetRasterBand(1).ReadAsArray()

    def read_configuration_elevation(self):
        s = self.config['General']['elevation']
        self.elevation = self.get_number_or_grid(s)
        if self.elevation < -427 or self.elevation > 8848:
            raise WrongValueError('The elevation must be between -427 '
                                  'and 8848')

    def read_configuration_albedo(self):
        # from ipdb;ipdb.set_trace()
        albedo_config = self.config['General']['albedo']
        try:
            if len(albedo_config) <= 1:
                self.albedo = self.get_number_or_grid(albedo_config)
            else:
                try:
                    months = " ".join(str(x) for x in range(1,13)).split()
                    self.albedo = { month_index:albedo for month_index,albedo in zip(months,albedo_config)}
                except ValueError:
                    print "Got an empty albedo list or Got more albedo.tiff than 12 months!!"

            if self.albedo < 0.0 or self.albedo > 1.0:
                raise WrongValueError('The albedo must be between 0.0 and 1.0')
        except:
            raise ConfigError("albedo parameter is not config")



        self.albedo = self.get_number_or_grid(s)

        if self.albedo < 0.0 or self.albedo > 1.0:
            raise WrongValueError('The albedo must be between 0.0 and 1.0')

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
        this by picking up a random variable (temperature) from a random
        configuraton section and extracting the data from the GeoTIFF file.
        Elsewhere other GeoTIFF files are checked for consistency with this
        data.
        """
        # Read data from GeoTIFF file
        self.asection = next((x for x in self.config if x != 'General'))
        filename = self.config[self.asection]['temperature']
        fp = gdal.Open(filename)
        if fp is None:
            raise IOError('An error occured when trying to open ' + filename)
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
        self.get_coordinates()
        self.penman_monteith = PenmanMonteith(
            self.albedo, self.nighttime_solar_radiation_ratio, self.elevation,
            self.latitude, self.longitude, self.step, self.unit_converters)
        sections = (x for x in self.config if x != 'General')
        for section in sections:
            self.process_section(section)

    def process_section(self, section):
        input_data = {'temperature': None, 'humidity': None,
                      'wind_speed': None, 'pressure': None,
                      'solar_radiation': None}
        timestamp = None
        for variable in input_data:
            # Open file
            filename = self.config[section][variable]
            fp = gdal.Open(filename)
            if fp is None:
                raise IOError('An error occured when trying to open {}'
                              .format(filename))

            # Get timestamp and verify consistency
            timestamp1 = fp.GetMetadata()['TIMESTAMP']
            timestamp = timestamp or timestamp1
            if timestamp != timestamp1:
                raise Exception('Not all input files have the same '
                                'timestamp (configuration section: {})'
                                .format(section))

            # Also verify consistency of geographical data
            consistent = all(
                (self.width == fp.RasterXSize,
                 self.height == fp.RasterYSize,
                 self.geo_transform == fp.GetGeoTransform(),
                 self.projection.ExportToWkt() == fp.GetProjection()))
            if not consistent:
                raise Exception('Not all input files have the same '
                                'width, height, geo_transform and projection '
                                '(offending items: {}/temperature and {}/{})'
                                .format(self.asection, section, variable))

            # Read array
            input_data[variable] = fp.GetRasterBand(1).ReadAsArray()

            # Close file
            fp = None

        input_data['adatetime'] = iso8601.parse_date(timestamp,
                                                     default_timezone=None)
        if input_data['adatetime'].tzinfo is None:
            raise Exception('The TIMESTAMP in the input files does not '
                            'have a time zone specified.')

        result = self.penman_monteith.calculate(**input_data)

        # Create destination data source
        output_filename = self.config[section]['result']
        output = gdal.GetDriverByName('GTiff').Create(
            output_filename, self.width, self.height, 1,
            gdal.GDT_Float32)
        if not output:
            raise IOError('An error occured when trying to open {}'.format(
                output_filename))
        try:
            output.SetMetadataItem('TIMESTAMP', timestamp)
            output.SetGeoTransform(self.geo_transform)
            output.SetProjection(self.projection.ExportToWkt())
            output.GetRasterBand(1).WriteArray(result)
        finally:
            # Close the dataset
            output = None
