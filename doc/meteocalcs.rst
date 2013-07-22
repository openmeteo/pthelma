:mod:`meteocalcs` --- Meteorological Calculations
=================================================

.. module:: meteocalcs
   :synopsis: Meteorological calculations.
.. moduleauthor:: Stefanos Kozanis <S.Kozanis@itia.ntua.gr>
.. sectionauthor:: Antonis Christofides <anthony@itia.ntua.gr>

This module provides some helper functions for meteorological
calculations such as Heat Index, Wind Chill, Evaporation etc.

Helper functions
----------------

.. function:: HeatIndex(Tc, RH)

   Returns the Heat Index in Celsius degrees when Tc>=26.7
   or else returns Tc. Tc is the mean air temperature in
   Celsius Degrees (e.g. 29.0), RH the Relative Hummydity
   in percent (e.g. 40). If Tc and/or RH are NaN, 
   returns NaN as well.

.. function:: SSI(Tc, RH)

   Returns the Summer Simmer Index in Celsius degrees when
   Tc>22 or else returns Tc. Tc is the mean air temperature in
   Celsius Degrees (e.g. 29.0), RH the Relative Hummydity
   in percent (e.g. 40). If Tc and/or RH are NaN, 
   returns NaN as well.

.. function:: IDM(T, Precip[, is_annual=False])

   Return the de Martonne Aridity Index. T in degrees C,
   Precip in mm. Precip is the cumulative preciptation
   for a month or a year respectively.
   If is_annual=False values should be monthly
   or else annual. If T and/or Precip are NaN,
   return NaN as well.


.. function:: BarometricFormula(T, Pb, hdiff)
    Return the barometric pressure at a level
    h if the pressure Pb at an altutde hb is given for
    atmospheric temperature T, according to the
    barometric formula. hdiff is h-hb.
    If any of the arguments is Nan, return NaN as well.
