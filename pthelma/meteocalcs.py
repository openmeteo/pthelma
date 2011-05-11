from fpconst import isNaN, NaN

def HeatIndex(Tc, RH):
    """Return the Heat Index in degrees C. Tc in degrees C,
    RH rel. hum. in % (e.g. 40%). When Tc<26.7
    returns the actual Tc.
    """
    if isNaN(Tc) or isNaN(RH):
        return NaN
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
    if isNaN(Tc) or isNaN(RH):
        return NaN
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
    if isNaN(T) or isNaN(Precip):
        return NaN
    f=1 if is_annual else 12
    return f*Precip/(T+10)
