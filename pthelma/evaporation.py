from datetime import timedelta
import math
from math import cos, pi, sin


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
        r_a = self.get_extraterrestrial_radiation(adatetime) * (
            0.75 + 2e-5 * self.elevation)  # Eq. 37, p. 51
        return self.penman_monteith(
            solar_radiation=variables['solar_radiation'],
            clear_sky_solar_radiation=r_a,
            psychrometric_constant=gamma,
            wind_speed=variables['wind_speed'],
            temperature=variables['temperature'],
            humidity=variables['humidity'])

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
        utc_offset = adatetime.tzinfo.utcoffset()
        utc_offset_hours = utc_offset.hours + utc_offset.minutes / 60.0
        lz = -utc_offset_hours * 15

        # Solar time angle at midpoint of the time period, eq. 31, p. 48.
        t = adatetime - self.step_length / 2.0
        omega = pi / 12 * ((t + 0.06667 * (lz - self.longitude) + sc) - 12)

        # Solar time angles at beginning and end of the period, eqs. 29 and 30,
        # p. 48.
        t1 = self.step_length.hours + self.step_length.minutes / 60.0
        omega1 = omega - pi * t1 / 24
        omega2 = omega + pi * t1 / 24

        # Result: eq. 28, p. 47.
        phi = self.latitude / 180.0 * pi
        return 12 * 60 / pi * 0.0820 * dr * (
            (omega2 - omega1) * sin(phi) * sin(decl)
            + cos(phi) * cos(decl) * (sin(omega2) - sin(omega1)))

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
        return 1013e-3 * pressure / 0.622 / lambda_

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
        numerator_term2 = g * 37 / (mean_temperature + 273.16) \
            * mean_wind_speed * (svp - avp)
        denominator = delta + psychrometric_constant * (1 +
                                                        0.34 * mean_wind_speed)

        return (numerator_term1 + numerator_term2) / denominator

    def get_net_outgoing_radiation(self, mean_temperature,
                                   incoming_solar_radiation,
                                   clear_sky_solar_radiation,
                                   nighttime_solar_radiation_ratio,
                                   mean_actual_vapour_pressure):
        """
        Allen et al. (1998), p. 52, eq. 39, modified according to end of page
        74.
        """
        factor1 = self.sigma * (mean_temperature + 273.16) ** 4
        factor2 = 0.34 - 0.14 * (mean_actual_vapour_pressure ** 0.5)

        # Solar radiation ratio Rs/Rs0 (Allen et al., 1998, top of p. 75).
        solar_radiation_ratio = \
            incoming_solar_radiation / clear_sky_solar_radiation \
            if clear_sky_solar_radiation > 0.05 \
            else nighttime_solar_radiation_ratio
        solar_radiation_ratio = max(solar_radiation_ratio, 0.3)
        solar_radiation_ratio = min(solar_radiation_ratio, 1.0)

        factor3 = 1.35 * solar_radiation_ratio - 0.35

        return factor1 * factor2 * factor3

    def get_saturation_vapour_pressure(self, temperature):
        "Allen et al. (1998), p. 36, eq. 11."
        return 0.6108 * math.e ** (17.27 * temperature / (237.3 + temperature))

    def get_soil_heat_flux_density(self, incoming_solar_radiation, rn):
        "Allen et al. (1998), p. 55, eq. 45 & 46."
        coefficient = 0.1 if incoming_solar_radiation > 0.05 else 0.5
        return coefficient * rn

    def get_saturation_vapour_pressure_curve_slope(self, temperature):
        "Allen et al. (1998), p. 37, eq. 13."
        numerator = 4098 * self.get_saturation_vapour_pressure(temperature)
        denominator = (temperature + 237.3) ** 2
        return numerator / denominator
