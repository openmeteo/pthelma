import datetime


class SoilWaterBalance(object):

    """
    class swb.SoilWaterBalance:
        Calculates soil water balance.
        Reference: (2006) R.G. ALLEN, L.S. PEREIRA, D.RAES, M.SMITH,
                    "FAO Irrigation and Drainage Paper No56"

        for more details visit : http://pthelma.readthedocs.org/
    """

    def __init__(self, fc, wp, rd, kc, p, peff, irrigation_efficiency,
                 theta_s, precipitation, evapotranspiration, rd_factor=1000):
        self.fc = fc  # field capacity
        self.wp = wp  # wilting point
        self.rd = rd  # root depth
        self.kc = kc  # crop coeff
        self.p = p  # crop depletion coeff
        self.peff = peff  # effective rainfall coeff
        self.irr_effi = irrigation_efficiency
        self.theta_s = theta_s
        self.precip = precipitation
        self.evap = evapotranspiration
        self.rd_factor = rd_factor
        # Calculations at __init__ corvert to mm
        self.theta_s_mm = self.theta_s * self.rd * self.rd_factor
        self.fc_mm = self.fc * self.rd * self.rd_factor
        self.wp_mm = self.wp * self.rd * self.rd_factor
        self.taw = self.fc - self.wp
        self.taw_mm = self.fc_mm - self.wp_mm
        self.raw = self.p * self.taw  # eq. 83
        self.raw_mm = self.p * self.taw_mm
        self.lowlim_theta = self.fc - self.raw
        self.lowlim_theta_mm = self.fc_mm - self.raw_mm
        self.wbm_report = []

    def Peff_calc(self, date):
        temp_peff = self.precip[date] * self.peff
        temp_eteff = self.evap[date] * (1 - self.peff)
        if temp_peff <= temp_eteff:
            return 0
        return self.precip[date] * self.peff

    def ks_calc(self, Dr):
        # eq (84)
        if (self.taw_mm - Dr) / (self.taw_mm - self.raw_mm) > 1:
            return 1
        return (self.taw_mm - Dr) / (self.taw_mm - self.raw_mm)

    def ETc_calc(self, date, Dr):
        return self.evap[date] * self.ks_calc(Dr) * self.kc

    def irrigate_question(self, Dr_i):
        if Dr_i >= self.raw_mm:
            return 1
        return 0

    def Dr_i_1_calc(self, Dr_i, Inet_i, theta):
        if theta < self.theta_s_mm:
            tempDr_i_1 = Dr_i - Inet_i
        else:
            tempDr_i_1 = 0.0
        if tempDr_i_1 > self.taw_mm:
            return self.taw_mm
        return tempDr_i_1

    def theta_calc(self, theta_init, Dr_i, Inet_i):
        if theta_init - Dr_i >= self.theta_s_mm:
            return self.theta_s_mm
        return self.fc_mm - Dr_i + Inet_i

    def Inet_calc(self, Dr_i):
        if Dr_i >= self.raw_mm:
            return Dr_i
        else:
            return 0.0

    def irr_events_calc(self, irr_event_days, day, Dr_i):
        if len(irr_event_days) >= 1:
            if day not in irr_event_days:
                return 0.0
            else:
                return self.Inet_calc(Dr_i)
        return self.Inet_calc(Dr_i)

    def get_timedelta(self):
        if self.precip.time_step.length_minutes == 1440:
            return datetime.timedelta(days=1)
        if self.precip.time_step.length_minutes == 60:
            return datetime.timedelta(hours=1)
        raise ValueError("Timeseries should be Daily or Hourly")

    def RO_calc(self, Peff_i, theta_1):
        if theta_1 - self.theta_s_mm + Peff_i <= 0:
            return 0.0
        else:
            return theta_1 - self.theta_s_mm + Peff_i

    def check_forecast_Dr(self, Dr_historical, theta):
        # For aira usage: Aira needs two separate runs,
        # one with Daily-Historical values second with Hourly-Forecast values.
        # In order to connect the runs, only Dr_i  from historical values
        # must be pass as Dr_0 of forecast values init value
        if Dr_historical is not None:
            return Dr_historical
        return self.fc_mm - theta

    def water_balance(self, theta_init, irr_event_days,
                      start_date, end_date, Dr_historical=None):
        if len(self.wbm_report) >= 1:
            self.depletion_report = []
        # i = 0
        theta = theta_init
        # check_forecast_Dr for aira
        Dr_i = self.check_forecast_Dr(Dr_historical, theta)
        CR = 0.0  # Static exists for later dev improvement
        DP = 0.0  # Static exists for later dev improvement
        # Next step preparation / (t-1) values
        Dr_i_1 = Dr_i
        theta_i_1 = theta
        delta = self.get_timedelta()
        step = start_date
        while step <= end_date:
            Peff_i = self.Peff_calc(step)
            RO_i = self.RO_calc(Peff_i, theta_i_1)
            ETc = self.ETc_calc(step, Dr_i_1)
            SWB = - Peff_i - CR + ETc + DP + RO_i
            Dr_i = Dr_i_1 + SWB
            Inet_i = self.irr_events_calc(irr_event_days, step, Dr_i)
            theta = self.theta_calc(theta_init, Dr_i, Inet_i)
            Dr_i_1 = self.Dr_i_1_calc(Dr_i, Inet_i, theta)
            theta_i_1 = theta
            theta_p = theta / (self.rd * self.rd_factor)
            self.wbm_report.append({'date': step,
                                    'Dr_i': Dr_i,
                                    'SWB': SWB,
                                    'P': self.precip[step],
                                    'Peff': Peff_i,
                                    'RO': RO_i,
                                    'Inet': Inet_i,
                                    'CR': CR,
                                    'ETo': self.evap[step],
                                    'Ks': self.ks_calc(Dr_i_1),
                                    'ETc': ETc,
                                    'DP': DP,
                                    'theta': theta,
                                    'irrigate': self.irrigate_question(Dr_i),
                                    'Ifinal': Inet_i / self.irr_effi,
                                    'Dr_1_next': Dr_i_1,
                                    'Theta_p': theta_p})
            step += delta
        return Dr_i
