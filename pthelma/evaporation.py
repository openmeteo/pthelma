

def penman_monteith_hourly(incoming_solar_radiation,
                           albedo,
                           clear_sky_solar_radiation,
                           psychrometric_constant,
                           mean_wind_speed,
                           mean_temperature,
                           mean_actual_vapour_pressure,
                           nighttime_solar_radiation_ratio):

    # Net radiation at grass surface
    rns = get_net_solar_radiation(albedo, incoming_solar_radiation)
    rnl = get_net_outgoing_radiation(mean_temperature,
                                     incoming_solar_radiation,
                                     clear_sky_solar_radiation,
                                     nighttime_solar_radiation_ratio,
                                     mean_actual_vapour_pressure)
    rn = rns - rnl

    # Saturation vapour pressure
    svp = get_saturation_vapour_pressure(mean_temperature)

    # Saturation vapour pressure curve slope
    delta = get_saturation_vapour_pressure_curve_slope(mean_temperature)

    # Soil heat flux density
    g = get_soil_heat_flux_density(incoming_solar_radiation, rn)

    # Apply the formula
    numerator_term1 = 0.408 * delta * (rn - g)
    numerator_term2 = g * 37 / (mean_temperature + 273.16) * mean_wind_speed \
        * (svp - mean_actual_vapour_pressure)
    denominator = delta + psychrometric_constant * (1 + 0.34 * mean_wind_speed)

    return (numerator_term1 + numerator_term2) / denominator


def get_net_solar_radiation(albedo, incoming_solar_radiation):
    """Allen et al. (1998), p. 51, eq. 38."""
    return (1.0 - albedo) * incoming_solar_radiation


sigma = 2.043e-10  # Modified Stefan-Boltzmann constant (Allen et al., 1998,
                   # end of p. 74)


def get_net_outgoing_radiation(mean_temperature,
                               incoming_solar_radiation,
                               clear_sky_solar_radiation,
                               nighttime_solar_radiation_ratio,
                               mean_actual_vapour_pressure):
    """
    Allen et al. (1998), p. 52, eq. 39, modified according to end of page 74.
    """
    factor1 = sigma * (mean_temperature + 273.16) ** 4
    factor2 = 0.34 - 0.14 * (mean_actual_vapour_pressure ** 0.5)

    # Solar radiation ratio Rs/Rs0 (Allen et al., 1998, top of p. 75).
    solar_radiation_ratio = \
        incoming_solar_radiation / clear_sky_solar_radiation \
        if clear_sky_solar_radiation > .05 else nighttime_solar_radiation_ratio
    solar_radiation_ratio = max(solar_radiation_ratio, 0.3)
    solar_radiation_ratio = min(solar_radiation_ratio, 1.0)

    factor3 = 1.35 * solar_radiation_ratio - 0.35

    return factor1 * factor2 * factor3


def get_saturation_vapour_pressure(temperature):
    "Allen et al. (1998), p. 36, eq. 11."
    return 0.6108 * 2.7183 ** (17.27 * temperature / (237.3 + temperature))


def get_soil_heat_flux_density(incoming_solar_radiation, rn):
    "Allen et al. (1998), p. 55, eq. 45 & 46."
    coefficient = 0.1 if incoming_solar_radiation > 0.05 else 0.5
    return coefficient * rn


def get_saturation_vapour_pressure_curve_slope(temperature):
    "Allen et al. (1998), p. 37, eq. 13."
    numerator = 4098 * get_saturation_vapour_pressure(temperature)
    denominator = (temperature + 237.3) ** 2
    return numerator / denominator
