.. _evaporation:

:mod:`evaporation` --- Calculation of evaporation and transpiration
===================================================================

.. module:: evaporation
   :synopsis: Calculation of evaporation and transpiration
.. moduleauthor:: Antonis Christofides <anthony@itia.ntua.gr>
.. sectionauthor:: Antonis Christofides <anthony@itia.ntua.gr>

.. function:: penman_monteith_hourly(incoming_solar_radiation, albedo, clear_sky_solar_radiation, psychrometric_constant, mean_wind_speed, mean_temperature, mean_actual_vapour_pressure, nighttime_solar_radiation_ratio)

   Calculates and returns the reference evapotranspiration according
   to Allen et al. (1998), equation 53, page 74.

   As explained in Allen et al. (1998, p. 74), the function is
   modified in relation to the original Penman-Monteith equation, so
   that it is suitable for hourly data.

   In order to estimate the outgoing radiation, the ratio
   *incoming_solar_radiation* / *clear_sky_solar_radiation* is used as a
   representation of cloud cover. This, however, does not work during the
   night, so whenever *clear_sky_solar_radiation* is zero, the
   *nighttime_solar_radiation_ratio* is used as a rough approximation of that
   ratio. It should be a number between 0.4 and 0.8; see Allen et al.  (1998),
   top of page 75.

   The units are as follows:

   ========================  =====================
   Parameter                 Unit
   ========================  =====================
   solar radiation           MJ/m²/h
   albedo                    dimensionless
   psychrometric constant    kPa/℃
   wind speed                m/s
   temperature               ℃
   vapour pressure           kPa
   evapotranspiration        mm/h
   ========================  =====================


References
----------

R. G. Allen, L. S. Pereira, D. Raes, and M. Smith, Crop evapotranspiration -
Guidelines for computing crop water requirements, FAO Irrigation and drainage
paper no. 56, 1998.
