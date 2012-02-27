#!/usr/bin/python
"""
meteocalcs - meteorological calculations such as Heat Index, Wind
Chill, Evaporation etc.

Copyright (C) 2005-2011 National Technical University of Athens
Copyright (C) 2011 Stefanos Kozanis

This program is free software; you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation; either version 2 of the License, or
(at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.
"""

from math import exp, isnan

#Gravitational acceleration at phi=45deg m^2/s
g0 = 9.80665
#Universal gas constant for air in N.m/(mol.K)
Rs = 8.31432
#Molar mass of Earth's air in kg/mol
Mair = 0.0289644


def HeatIndex(Tc, RH):
    """Return the Heat Index in degrees C. Tc in degrees C,
    RH rel. hum. in % (e.g. 40%). When Tc<26.7
    returns the actual Tc.
    """
    if isnan(Tc) or isnan(RH):
        return float('NaN')
    if Tc<26.7:
        return Tc
    Tf = float(Tc)*9/5 + 32
    HI = -42.379 + 2.04901523*Tf + 10.14333127*RH - 0.22475541*Tf*RH -\
         6.83783e-3* Tf**2 - 5.481717e-2* RH**2 +\
         1.22874e-3* Tf**2 * RH + 8.5282e-4* Tf* RH**2 -\
         1.99e-6* Tf**2 * RH**2
    return (HI-32)*5/9

def SSI(Tc, RH):
    """Return the Summer Simmer Index in degrees C. Tc in degrees C,
    RH rel. hum. in % (e.g. 40%). When Tc<22
    returns the actual Tc.
    """
    if isnan(Tc) or isnan(RH):
        return float('NaN')
    if Tc<22:
        return Tc
    Tf = float(Tc)*9/5 + 32
    ssi =  1.98*(Tf-(0.55-0.0055*RH)*(Tf-58))-56.83
    return (ssi-32)*5/9

def IDM(T, Precip, is_annual=False):
    """Return the de Martonne Aridity Index. T in degrees C,
    Precip in mm. If is_annual=False values should be monthly
    or else annual.
    """
    if isnan(T) or isnan(Precip):
        return float('NaN')
    f=1 if is_annual else 12
    return f*Precip/(T+10)

def BarometricFormula(T, Pb, hdiff):
    """Return the barometric pressure at a level
    h if the pressure Pb at an altutde hb is given for
    atmospheric temperature T, according to the
    barometric formula. hdiff is h-hb.
    """
    for v in (T, Pb, hdiff):
        if isnan(v):
            return float('NaN')
            break
    T+= 273.75
    return Pb * exp( (-g0*Mair*hdiff)/(Rs * T) )
