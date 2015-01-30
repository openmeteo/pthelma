from datetime import datetime
from datetime import timedelta
import textwrap
from unittest import TestCase

from six import StringIO

from pthelma.timeseries import Timeseries, TimeStep
from pthelma.swb import SoilWaterBalance


precipitation_test_daily_timeseries_summer = textwrap.dedent("""
            2008-08-01 0:00,0
            2008-08-02 0:00,0
            2008-08-03 0:00,0
            2008-08-04 0:00,0
            2008-08-05 0:00,0
            2008-08-06 0:00,0
            2008-08-07 0:00,0
            2008-08-08 0:00,0
            2008-08-09 0:00,0
            2008-08-10 0:00,0
            2008-08-11 0:00,0
            2008-08-12 0:00,0
            2008-08-13 0:00,0
            2008-08-14 0:00,0
            2008-08-15 0:00,0
            2008-08-16 0:00,0
            2008-08-17 0:00,0
            2008-08-18 0:00,0
            2008-08-19 0:00,0
            2008-08-20 0:00,0
            2008-08-21 0:00,0
            2008-08-22 0:00,0
            2008-08-23 0:00,0
            2008-08-24 0:00,0
            2008-08-25 0:00,0
            2008-08-26 0:00,0
            2008-08-27 0:00,0
            2008-08-28 0:00,0
            2008-08-29 0:00,0
            2008-08-30 0:00,0
            """)

evapotranspiration_test_daily_timeseries_summer = textwrap.dedent("""
            2008-08-01 0:00,6.910
            2008-08-02 0:00,6.240
            2008-08-03 0:00,5.730
            2008-08-04 0:00,5.560
            2008-08-05 0:00,5.530
            2008-08-06 0:00,5.700
            2008-08-07 0:00,5.660
            2008-08-08 0:00,5.460
            2008-08-09 0:00,5.320
            2008-08-10 0:00,5.210
            2008-08-11 0:00,5.460
            2008-08-12 0:00,5.550
            2008-08-13 0:00,5.160
            2008-08-14 0:00,5.530
            2008-08-15 0:00,5.820
            2008-08-16 0:00,5.370
            2008-08-17 0:00,5.250
            2008-08-18 0:00,5.320
            2008-08-19 0:00,5.580
            2008-08-20 0:00,5.790
            2008-08-21 0:00,5.530
            2008-08-22 0:00,5.480
            2008-08-23 0:00,5.450
            2008-08-24 0:00,5.180
            2008-08-25 0:00,5.510
            2008-08-26 0:00,5.430
            2008-08-27 0:00,5.060
            2008-08-28 0:00,5.220
            2008-08-29 0:00,4.700
            2008-08-30 0:00,4.110
            """)

precipitation_test_hourly_timeseries = textwrap.dedent("""
            2008-08-01 00:00,0
            2008-08-01 01:00,0
            2008-08-01 02:00,0
            2008-08-01 03:00,0
            2008-08-01 04:00,0
            2008-08-01 05:00,0
            2008-08-01 06:00,0
            2008-08-01 07:00,0
            2008-08-01 08:00,0
            2008-08-01 09:00,0
            2008-08-01 10:00,0
            2008-08-01 11:00,0
            2008-08-01 12:00,0
            2008-08-01 13:00,0
            2008-08-01 14:00,0
            2008-08-01 15:00,0
            2008-08-01 16:00,0
            2008-08-01 17:00,0
            2008-08-01 18:00,0
            2008-08-01 19:00,0
            2008-08-01 20:00,0
            2008-08-01 21:00,0
            2008-08-01 22:00,0
            2008-08-01 23:00,0
            2008-08-02 00:00,0
            2008-08-02 01:00,0
            2008-08-02 02:00,0
            2008-08-02 03:00,0
            2008-08-02 04:00,0
            2008-08-02 05:00,0
            """)

evapotranspiration_test_hourly_timeseries = textwrap.dedent("""
            2008-08-01 00:00,6.910
            2008-08-01 01:00,6.240
            2008-08-01 02:00,5.730
            2008-08-01 03:00,5.560
            2008-08-01 04:00,5.530
            2008-08-01 05:00,5.700
            2008-08-01 06:00,5.660
            2008-08-01 07:00,5.460
            2008-08-01 08:00,5.320
            2008-08-01 09:00,5.210
            2008-08-01 10:00,5.460
            2008-08-01 11:00,5.550
            2008-08-01 12:00,5.160
            2008-08-01 13:00,5.530
            2008-08-01 14:00,5.820
            2008-08-01 15:00,5.370
            2008-08-01 16:00,5.250
            2008-08-01 17:00,5.320
            2008-08-01 18:00,5.580
            2008-08-01 19:00,5.790
            2008-08-01 20:00,5.530
            2008-08-01 21:00,5.480
            2008-08-01 22:00,5.450
            2008-08-01 23:00,5.180
            2008-08-02 00:00,5.510
            2008-08-02 01:00,5.430
            2008-08-02 02:00,5.060
            2008-08-02 03:00,5.220
            2008-08-02 04:00,4.700
            2008-08-02 05:00,4.110
            """)

precipitation_test_daily_timeseries_winter = textwrap.dedent("""
            2008-10-01 00:00,20.0000
            2008-10-02 00:00,31.2000
            2008-10-03 00:00,71.4000
            2008-10-04 00:00,37.2000
            2008-10-05 00:00,0.6000
            2008-10-06 00:00,0.0000
            2008-10-07 00:00,0.0000
            2008-10-08 00:00,0.0000
            2008-10-09 00:00,0.0000
            2008-10-10 00:00,6.4000
            2008-10-11 00:00,0.0000
            2008-10-12 00:00,0.0000
            2008-10-13 00:00,0.0000
            2008-10-14 00:00,0.0000
            2008-10-15 00:00,0.0000
            2008-10-16 00:00,0.0000
            2008-10-17 00:00,0.0000
            2008-10-18 00:00,0.0000
            2008-10-19 00:00,0.0000
            2008-10-20 00:00,0.0000
            2008-10-21 00:00,0.0000
            2008-10-22 00:00,0.0000
            2008-10-23 00:00,0.0000
            2008-10-24 00:00,0.0000
            2008-10-25 00:00,0.0000
            2008-10-26 00:00,0.0000
            2008-10-27 00:00,0.0000
            2008-10-28 00:00,0.0000
            2008-10-29 00:00,0.0000
            2008-10-30 00:00,0.6000
            2008-10-31 00:00,1.0000
""")

evapotranspiration_test_daily_timeseries_winter = textwrap.dedent("""
            2008-10-01 00:00,2.1500
            2008-10-02 00:00,1.6900
            2008-10-03 00:00,2.0000
            2008-10-04 00:00,1.6300
            2008-10-05 00:00,1.9400
            2008-10-06 00:00,2.1900
            2008-10-07 00:00,2.3000
            2008-10-08 00:00,2.3300
            2008-10-09 00:00,2.4600
            2008-10-10 00:00,2.4300
            2008-10-11 00:00,2.2400
            2008-10-12 00:00,2.5200
            2008-10-13 00:00,2.5000
            2008-10-14 00:00,2.5100
            2008-10-15 00:00,2.1100
            2008-10-16 00:00,1.9300
            2008-10-17 00:00,1.9500
            2008-10-18 00:00,1.6500
            2008-10-19 00:00,1.6100
            2008-10-20 00:00,1.9900
            2008-10-21 00:00,1.9800
            2008-10-22 00:00,2.0800
            2008-10-23 00:00,1.9700
            2008-10-24 00:00,1.9000
            2008-10-25 00:00,1.7700
            2008-10-26 00:00,1.4800
            2008-10-27 00:00,1.1700
            2008-10-28 00:00,1.7700
            2008-10-29 00:00,1.8800
            2008-10-30 00:00,1.6100
            2008-10-31 00:00,1.7300

                                                                  """)


class SoilWaterBalanceWinterTestCase(TestCase):
    # Case Study: IRMA_DW_Balance_winter.ods

    def setUp(self):
        # PUT data .ods
        self.precip = Timeseries(time_step=TimeStep(1440, 0))
        instring = StringIO(precipitation_test_daily_timeseries_winter)
        self.precip.read_file(instring)

        self.evap = Timeseries(time_step=Timeseries(1440, 0))
        instring = StringIO(evapotranspiration_test_daily_timeseries_winter)
        self.evap.read_file(instring)
        # Parameters
        self.fc = 0.287
        self.wp = 0.140
        self.rd = 0.5
        self.kc = 0.7
        self.p = 0.5
        self.peff = 0.8
        self.irr_eff = 0.8
        self.theta_s = 0.425
        self.rd_factor = 1000
        # swb instance
        self.swb = SoilWaterBalance(self.fc, self.wp, self.rd,
                                    self.kc, self.p, self.peff, self.irr_eff,
                                    self.theta_s, self.precip, self.evap,
                                    self.rd_factor)

    def test_swb_daily_general_winter(self):
        start_date = datetime(2008, 10, 1)
        end_date = datetime(2008, 10, 31)
        theta_init = self.swb.fc_mm
        irr_event_days = []

        self.swb.water_balance(theta_init, irr_event_days,
                               start_date, end_date, Dr_historical=None)

        # Parameters
        self.assertEqual(self.swb.fc_mm, 143.5)
        self.assertEqual(self.swb.wp_mm, 70.0)
        self.assertEqual(self.swb.theta_s_mm, 212.5)
        self.assertAlmostEqual(self.swb.taw, 0.147)
        self.assertEqual(self.swb.taw_mm, 73.5)
        self.assertAlmostEqual(self.swb.raw, 0.0735)
        self.assertEqual(self.swb.raw_mm, 36.75)
        self.assertEqual(self.swb.lowlim_theta, 0.2135)
        self.assertEqual(self.swb.lowlim_theta_mm, 106.75)

        # Check timedelta
        self.assertEqual(self.swb.get_timedelta(), timedelta(1))

        # i = 1
        values1 = self.swb.wbm_report[0]
        self.assertEqual(values1['ETc'], 1.50500)
        self.assertAlmostEqual(values1['Dr_i'], -14.49500)
        self.assertAlmostEqual(values1['Dr_1_next'], -14.49500)
        self.assertEqual(values1['theta'], 157.99500)
        self.assertEqual(values1['Peff'], 16.0)
        self.assertEqual(values1['RO'], 0.0)
        self.assertEqual(values1['Inet'], 0.0)
        self.assertEqual(values1['Ks'], 1)
        self.assertAlmostEqual(values1['SWB'], -14.49500)

        # Other dates
        values2 = self.swb.wbm_report[2]
        self.assertEqual(values2['date'], datetime(2008, 10, 3, 0, 0))
        self.assertEqual(values2['ETc'], 1.4)
        self.assertEqual(values2['P'], 71.400)
        self.assertAlmostEqual(values2['Peff'], 57.12000)
        self.assertAlmostEqual(values2['RO'], 26.39200)
        self.assertEqual(values2['irrigate'], 0.0)
        self.assertAlmostEqual(values2['Inet'], 0.0)
        self.assertAlmostEqual(values2['Dr_i'], -67.6000)
        self.assertAlmostEqual(values2['SWB'], -29.32800)
        self.assertAlmostEqual(values2['theta'], 211.1000)

    def test_swb_daily_winter_with_no_irrigation_date(self):
        start_date = datetime(2008, 10, 1)
        end_date = datetime(2008, 10, 31)
        theta_init = self.swb.fc_mm
        irr_event_days = []

        self.swb.water_balance(theta_init, irr_event_days,
                               start_date, end_date)

        # i = 1
        values1 = self.swb.wbm_report[0]
        self.assertEqual(values1['ETc'], 1.50500)
        self.assertAlmostEqual(values1['Dr_i'], -14.49500)
        self.assertAlmostEqual(values1['Dr_1_next'], -14.49500)
        self.assertEqual(values1['theta'], 157.99500)
        self.assertEqual(values1['Peff'], 16.0)
        self.assertEqual(values1['RO'], 0.0)
        self.assertEqual(values1['Inet'], 0.0)
        self.assertEqual(values1['Ks'], 1)
        self.assertAlmostEqual(values1['SWB'], -14.49500)

        # Other dates
        values2 = self.swb.wbm_report[2]
        self.assertEqual(values2['date'], datetime(2008, 10, 3, 0, 0))
        self.assertEqual(values2['ETc'], 1.4)
        self.assertEqual(values2['P'], 71.400)
        self.assertAlmostEqual(values2['Peff'], 57.12000)
        self.assertAlmostEqual(values2['RO'], 26.39200)
        self.assertEqual(values2['irrigate'], 0.0)
        self.assertAlmostEqual(values2['Inet'], 0.0)
        self.assertAlmostEqual(values2['Dr_i'], -67.6000)
        self.assertAlmostEqual(values2['SWB'], -29.32800)
        self.assertAlmostEqual(values2['theta'], 211.1000)

        values3 = self.swb.wbm_report[-1]
        self.assertEqual(values3['date'], datetime(2008, 10, 31, 0, 0))
        self.assertAlmostEqual(values3['Dr_i'], -36.9390)
        self.assertAlmostEqual(values3['SWB'], 0.4109999999)
        self.assertAlmostEqual(values3['theta'], 180.43900)

    def test_swb_daily_winter_with_irrigations_dates(self):
        start_date = datetime(2008, 10, 1)
        end_date = datetime(2008, 10, 31)
        theta_init = self.swb.fc_mm
        irr_event_days = [datetime(2008, 10, 1, 0, 0),
                          datetime(2008, 10, 15, 0, 0)]

        self.swb.water_balance(theta_init, irr_event_days,
                               start_date, end_date)

        # i = 1
        values1 = self.swb.wbm_report[0]
        self.assertEqual(values1['ETc'], 1.50500)
        self.assertAlmostEqual(values1['Dr_i'], -14.49500)
        self.assertAlmostEqual(values1['Dr_1_next'], -14.49500)
        self.assertEqual(values1['theta'], 157.99500)
        self.assertEqual(values1['Peff'], 16.0)
        self.assertEqual(values1['RO'], 0.0)
        self.assertEqual(values1['Inet'], 0.0)
        self.assertEqual(values1['Ks'], 1)
        self.assertAlmostEqual(values1['SWB'], -14.49500)

        # Other dates
        values2 = self.swb.wbm_report[14]
        self.assertEqual(values2['date'], datetime(2008, 10, 15, 0, 0))
        self.assertEqual(values2['ETc'], 1.4769999999999999)
        self.assertEqual(values2['P'], 0.0)
        self.assertAlmostEqual(values2['Peff'], 0.0)
        self.assertAlmostEqual(values2['RO'], 0.0)
        self.assertEqual(values2['irrigate'], 0.0)
        self.assertAlmostEqual(values2['Inet'], 0.0)
        self.assertAlmostEqual(values2['Dr_i'], -55.58800)
        self.assertAlmostEqual(values2['SWB'], 1.47700)
        self.assertAlmostEqual(values2['theta'], 199.08800)

        values3 = self.swb.wbm_report[-1]
        self.assertEqual(values3['date'], datetime(2008, 10, 31, 0, 0))
        self.assertAlmostEqual(values3['Dr_i'], -36.9390)
        self.assertAlmostEqual(values3['SWB'], 0.4109999999)
        self.assertAlmostEqual(values3['theta'], 180.43900)


class SoilWaterBalanceDailySummerTestCase(TestCase):
    # Case Study: IRMA_DW_Balance_summer.ods

    def setUp(self):
        # IRMA_DW_Balance.xlxs
        self.precip = Timeseries(time_step=TimeStep(1440, 0))
        instring = StringIO(precipitation_test_daily_timeseries_summer)
        self.precip.read_file(instring)

        self.evap = Timeseries(time_step=Timeseries(1440, 0))
        instring = StringIO(evapotranspiration_test_daily_timeseries_summer)
        self.evap.read_file(instring)
        # Parameters
        self.fc = 0.287
        self.wp = 0.140
        self.rd = 0.5
        self.kc = 0.7
        self.p = 0.5
        self.peff = 0.8
        self.irr_eff = 0.8
        self.theta_s = 0.425
        self.rd_factor = 1000
        # swb instance
        self.swb = SoilWaterBalance(self.fc, self.wp, self.rd,
                                    self.kc, self.p, self.peff, self.irr_eff,
                                    self.theta_s, self.precip, self.evap,
                                    self.rd_factor)

    def test_swb_daily_general_summer(self):
        start_date = datetime(2008, 8, 1)
        end_date = datetime(2008, 8, 30)
        theta_init = self.swb.fc_mm
        irr_event_days = []

        self.swb.water_balance(theta_init, irr_event_days,
                               start_date, end_date)

        # Parameters
        self.assertEqual(self.swb.fc_mm, 143.5)
        self.assertEqual(self.swb.wp_mm, 70.0)
        self.assertEqual(self.swb.theta_s_mm, 212.5)
        self.assertAlmostEqual(self.swb.taw, 0.147)
        self.assertEqual(self.swb.taw_mm, 73.5)
        self.assertAlmostEqual(self.swb.raw, 0.0735)
        self.assertEqual(self.swb.raw_mm, 36.75)
        self.assertEqual(self.swb.lowlim_theta, 0.2135)
        self.assertEqual(self.swb.lowlim_theta_mm, 106.75)

        # Check timedelta
        self.assertEqual(self.swb.get_timedelta(), timedelta(1))

        # i = 1
        values1 = self.swb.wbm_report[0]
        self.assertEqual(values1['ETc'], 4.837)
        self.assertAlmostEqual(values1['Dr_i'], 4.837)
        self.assertAlmostEqual(values1['Dr_1_next'], 4.837)
        self.assertEqual(values1['theta'], 138.663)
        self.assertEqual(values1['Peff'], 0.0)
        self.assertEqual(values1['RO'], 0.0)
        self.assertEqual(values1['Inet'], 0.0)
        self.assertEqual(values1['Ks'], 1)
        self.assertEqual(values1['SWB'], 4.837)

        # Catch Inet
        values2 = self.swb.wbm_report[9]
        self.assertEqual(values2['date'], datetime(2008, 8, 10, 0, 0))
        self.assertEqual(values2['irrigate'], 1.0)
        self.assertAlmostEqual(values2['Inet'], 40.124)
        self.assertEqual(values2['theta'], 143.500)

        values3 = self.swb.wbm_report[19]
        self.assertEqual(values3['date'], datetime(2008, 8, 20, 0, 0))
        self.assertEqual(values3['irrigate'], 1.0)
        self.assertAlmostEqual(values3['Inet'], 38.3810)
        self.assertEqual(values3['theta'], 143.500)

        # end_date
        values4 = self.swb.wbm_report[29]
        self.assertEqual(values4['date'], datetime(2008, 8, 30, 0, 0))
        self.assertEqual(values3['irrigate'], 1.0)
        self.assertEqual(values4['Dr_i'], 36.169)
        self.assertEqual(values4['theta'], 107.3310)

    def test_swb_daily_summer_with_no_irrigation_date(self):
        start_date = datetime(2008, 8, 1)
        end_date = datetime(2008, 8, 30)
        theta_init = self.swb.fc_mm - 0.75 * self.swb.raw_mm
        irr_event_days = []

        self.swb.water_balance(theta_init, irr_event_days,
                               start_date, end_date)

        # i = 1
        values1 = self.swb.wbm_report[0]
        self.assertEqual(values1['ETc'], 4.837)
        self.assertAlmostEqual(values1['Dr_i'], 32.39950)
        self.assertAlmostEqual(values1['Dr_1_next'], 32.39950)
        self.assertEqual(values1['theta'], 111.100500)
        self.assertEqual(values1['Peff'], 0.0)
        self.assertEqual(values1['RO'], 0.0)
        self.assertEqual(values1['Inet'], 0.0)
        self.assertEqual(values1['Ks'], 1)
        self.assertEqual(values1['SWB'], 4.837)

        # Catch Inet
        values2 = self.swb.wbm_report[11]
        self.assertEqual(values2['date'], datetime(2008, 8, 12, 0, 0))
        self.assertEqual(values2['irrigate'], 1.0)
        self.assertAlmostEqual(values2['Inet'], 38.626000)
        self.assertEqual(values2['theta'], 143.500)

        values3 = self.swb.wbm_report[21]
        self.assertEqual(values3['date'], datetime(2008, 8, 22, 0, 0))
        self.assertEqual(values3['irrigate'], 1.0)
        self.assertAlmostEqual(values3['Inet'], 38.3810)
        self.assertEqual(values3['theta'], 143.500)

        # end_date
        values4 = self.swb.wbm_report[29]
        self.assertEqual(values4['date'], datetime(2008, 8, 30, 0, 0))
        self.assertEqual(values3['irrigate'], 1.0)
        self.assertAlmostEqual(values4['Dr_i'], 28.46200)
        self.assertAlmostEqual(values4['theta'], 115.038)

    def test_swb_daily_summer_with_irrigations_dates(self):
        start_date = datetime(2008, 8, 1)
        end_date = datetime(2008, 8, 30)
        theta_init = self.swb.fc_mm
        irr_event_days = [datetime(2008, 8, 1, 0, 0),
                          datetime(2008, 8, 15, 0, 0)]

        self.swb.water_balance(theta_init, irr_event_days,
                               start_date, end_date)

        values1 = self.swb.wbm_report[0]
        self.assertEqual(values1['ETc'], 4.837)
        self.assertAlmostEqual(values1['Dr_i'], 4.837)
        self.assertAlmostEqual(values1['Dr_1_next'], 4.837)
        self.assertEqual(values1['theta'], 138.66300)
        self.assertEqual(values1['Peff'], 0.0)
        self.assertEqual(values1['RO'], 0.0)
        self.assertEqual(values1['Inet'], 0.0)
        self.assertEqual(values1['Ks'], 1)
        self.assertEqual(values1['SWB'], 4.837)

        # Catch Inet
        values2 = self.swb.wbm_report[14]
        self.assertEqual(values2['date'], datetime(2008, 8, 15, 0, 0))
        self.assertEqual(values2['irrigate'], 1.0)
        self.assertAlmostEqual(values2['Dr_i'], 54.31683154)

        values3 = self.swb.wbm_report[-1]
        self.assertEqual(values3['date'], datetime(2008, 8, 30, 0, 0))
        self.assertEqual(values3['irrigate'], 1.0)
        self.assertAlmostEqual(values3['Dr_i'], 51.83859483)
        self.assertAlmostEqual(values3['theta'], 91.66140517)


class SoilWaterBalanceHourlySummerTestCase(TestCase):
    # Case Study: IRMA_DW_Balance_summer.ods
    # Using daily values as hourly values

    def setUp(self):
        self.precip = Timeseries(time_step=TimeStep(60, 0))
        instring = StringIO(precipitation_test_hourly_timeseries)
        self.precip.read_file(instring)

        self.evap = Timeseries(time_step=Timeseries(60, 0))
        instring = StringIO(evapotranspiration_test_hourly_timeseries)
        self.evap.read_file(instring)
        # Parameters
        self.fc = 0.287
        self.wp = 0.140
        self.rd = 0.5
        self.kc = 0.7
        self.p = 0.5
        self.peff = 0.8
        self.irr_eff = 0.8
        self.theta_s = 0.425
        self.rd_factor = 1000
        # swb instance
        self.swb = SoilWaterBalance(self.fc, self.wp, self.rd,
                                    self.kc, self.p, self.peff, self.irr_eff,
                                    self.theta_s, self.precip, self.evap,
                                    self.rd_factor)

    def test_parameters_hourly_general(self):
        start_date = datetime(2008, 8, 1, 0, 0)
        end_date = datetime(2008, 8, 2, 5, 0)
        theta_init = self.swb.fc_mm
        irr_event_days = []

        self.swb.water_balance(theta_init, irr_event_days,
                               start_date, end_date)

        # i = 0
        self.assertEqual(self.swb.fc_mm, 143.5)
        self.assertEqual(self.swb.wp_mm, 70.0)
        self.assertEqual(self.swb.theta_s_mm, 212.5)
        self.assertAlmostEqual(self.swb.taw, 0.147)
        self.assertEqual(self.swb.taw_mm, 73.5)
        self.assertAlmostEqual(self.swb.raw, 0.0735)
        self.assertEqual(self.swb.raw_mm, 36.75)
        self.assertEqual(self.swb.lowlim_theta, 0.2135)
        self.assertEqual(self.swb.lowlim_theta_mm, 106.75)

        # Check timedelta
        self.assertEqual(self.swb.get_timedelta(), timedelta(0, 3600))

        # i = 1
        values1 = self.swb.wbm_report[0]
        self.assertEqual(values1['ETc'], 4.837)
        self.assertAlmostEqual(values1['Dr_i'], 4.837)
        self.assertAlmostEqual(values1['Dr_1_next'], 4.837)
        self.assertEqual(values1['theta'], 138.663)
        self.assertEqual(values1['Peff'], 0.0)
        self.assertEqual(values1['RO'], 0.0)
        self.assertEqual(values1['Inet'], 0.0)
        self.assertEqual(values1['Ks'], 1)
        self.assertEqual(values1['SWB'], 4.837)
