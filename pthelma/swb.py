import datetime

class SoilWaterBalance(object):

    """
    class swb.SoilWaterBalance:
        Calculates soil water balance.

        for more details visit : http://pthelma.readthedocs.org/
    """

    def __init__(self, fc, wp, rd, kc, p, peff, irrigation_efficiency,
                 theta_s, precipitation, evapotranspiration, a=0, b=0,
                 rd_factor=1000, draintime=None):
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
        self.a = a # draintime parameters
        self.b = b # draintime parameters
        self.rd_factor = rd_factor
        self.wbm_report = []
        self.draintime = draintime
        if not self.draintime:
            self.draintime = self.__set_draintime(a, b, rd)
        self.__set_parameters_in_mm()

    def __set_parameters_in_mm(self ):
        """Called during Init of the object. Covert values in mm"""
        self.theta_s_mm = self.theta_s * self.rd * self.rd_factor
        self.fc_mm = self.fc * self.rd * self.rd_factor
        self.wp_mm = self.wp * self.rd * self.rd_factor
        self.taw = self.fc - self.wp
        self.taw_mm = self.fc_mm - self.wp_mm
        self.raw = self.p * self.taw  # eq. 83
        self.raw_mm = self.p * self.taw_mm
        self.lowlim_theta = self.fc - self.raw
        self.lowlim_theta_mm = self.fc_mm - self.raw_mm

    def __set_draintime(self, a, b, rd):
        """Calculate draintime"""
        return float(self.a * (self.rd * 100) ** self.b)

    def __get_timedelta__(self):
        if self.precip.time_step.length_minutes == 1440:
            return datetime.timedelta(days=1)
        if self.precip.time_step.length_minutes == 60:
            return datetime.timedelta(hours=1)
        raise ValueError("Timeseries should be Daily or Hourly")

    def __get_applied_water_idx(self, irr_event_days, step):
        return next((i for i, v in enumerate(irr_event_days) if v[0] == step), None)

    def __Peff_calc__(self, date):
        temp_peff = self.precip[date] * self.peff
        temp_eteff = self.evap[date] * (1 - self.peff)
        if temp_peff <= temp_eteff:
            return 0
        return self.precip[date] * self.peff

    def __Ks_calc__(self, Dr):
        # eq (84)
        if (self.taw_mm - Dr) / (self.taw_mm - self.raw_mm) > 1:
            return 1
        return (self.taw_mm - Dr) / (self.taw_mm - self.raw_mm)

    def __ETc_calc__(self, date, Dr):
        return self.evap[date] * self.__Ks_calc__(Dr) * self.kc

    def __irrigate_advice__(self, Dr_i):
        if Dr_i >= self.raw_mm:
            return 1
        return 0

    def __Dr_i_calc__(self, Dr_i, Inet_i):
        if Dr_i - Inet_i > self.taw_mm:
            return self.taw_mm
        return Dr_i - Inet_i

    def __Theta_calc__(self, theta_init, Dr_i, Inet):
        if theta_init - Dr_i >= self.theta_s_mm:
            return self.theta_s_mm
        return self.fc_mm - Dr_i + Inet

    def __Inet_calc__(self, day, Dr_i, FC_IRT, irr_event_days, Applied_Inet):
        if irr_event_days:
            return Applied_Inet * FC_IRT
        if Dr_i >= self.raw_mm:
            return Dr_i * FC_IRT
        return 0.0

    def __RO_calc__(self, Peff, theta_1):
        if theta_1 - self.theta_s_mm + Peff <= 0:
            return 0.0
        else:
            return theta_1 - self.theta_s_mm + Peff

    def __DP_calc__(self, Peff, theta_i_1):
        if theta_i_1 - self.fc_mm + Peff <= 0:
            return 0.0
        return (theta_i_1  - self.fc_mm + Peff ) / self.draintime

    def __Applied_Inet_calc__(self, step, irr_event_days):
        applied_water = 0.0
        if not irr_event_days:
            return applied_water
        applied_idx = self.__get_applied_water_idx(irr_event_days, step)
        if applied_idx != None: # due index can be 0, if 0 --> False
            return irr_event_days[applied_idx][1]  * self.irr_effi
        return applied_water

    def water_balance(self, theta_init, irr_event_days, start_date, end_date,
                      FC_IRT=1, Dr_historical=None, as_report=False):

        # Initialize Model run
        Dr_i = float(Dr_historical) if Dr_historical else self.fc_mm - theta_init
        Dr_i_1 = Dr_i
        theta_i_1 = theta_init
        CR = 0.0  # Static exists for later dev improvement

        delta = self.__get_timedelta__()
        step = start_date
        while step <= end_date:
            # sequence for variable calculations matters.
            Peff = self.__Peff_calc__(step)
            RO = self.__RO_calc__(Peff, theta_i_1)
            ETc = self.__ETc_calc__(step, Dr_i_1)
            DP = self.__DP_calc__(Peff, theta_i_1)
            Ks = self.__Ks_calc__(Dr_i_1)

            SWB = - Peff - CR + ETc + DP + RO

            Dr_i_missing_Inet = Dr_i_1 + SWB
            Applied_Inet = self.__Applied_Inet_calc__(step, irr_event_days)
            Inet = self.__Inet_calc__(step, Dr_i_missing_Inet, FC_IRT,
                                      irr_event_days, Applied_Inet)

            Dr_i = self.__Dr_i_calc__(Dr_i_missing_Inet, Inet)

            theta = self.__Theta_calc__(theta_init, Dr_i_missing_Inet, Inet)
            theta_persent = theta / (self.rd * self.rd_factor)
            irrigate = self.__irrigate_advice__(Dr_i_missing_Inet)

            # Next step initialization
            Dr_i_1 = Dr_i
            theta_i_1 = theta

            self.wbm_report.append({
                'date': step,
                'Dr_i': Dr_i,
                'Dr_i_missing_Inet': Dr_i_missing_Inet,
                'SWB': SWB,
                'P': self.precip[step],
                'Peff': Peff,
                'RO': RO,
                'Inet': Inet,
                'Applied_Inet': Applied_Inet,
                'CR': CR,
                'ETo': self.evap[step],
                'Ks': Ks,
                'ETc': ETc,
                'DP': DP,
                'theta': theta,
                'irrigate': irrigate,
                'Ifinal': Inet / self.irr_effi,
                'Theta_p': theta_persent
            })
            step += delta
        if as_report:
            return self.wbm_report
        return Dr_i
