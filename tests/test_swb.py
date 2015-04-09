from datetime import datetime
from datetime import timedelta
import textwrap
from unittest import TestCase

from six import StringIO

from pthelma.timeseries import Timeseries, TimeStep
from pthelma.swb import SoilWaterBalance


precipitation_test_daily_timeseries = textwrap.dedent("""
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

evapotranspiration_test_daily_timeseries = textwrap.dedent("""
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


class SoilWaterBalanceDailyTestCase(TestCase):
    # Case Study: IRMA_DW_Balance3.ods

    def setUp(self):
        # Water Balance 3
        self.precip = Timeseries(time_step=TimeStep(1440, 0))
        instring = StringIO(precipitation_test_daily_timeseries)
        self.precip.read_file(instring)

        self.evap = Timeseries(time_step=Timeseries(1440, 0))
        instring = StringIO(evapotranspiration_test_daily_timeseries)
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

    def test_swb_daily_general(self):
        start_date = datetime(2008, 8, 1)
        end_date = datetime(2008, 8, 30)
        theta_init = self.swb.fc_mm
        irr_event_days = []

        self.swb.water_balance(theta_init, irr_event_days,
                               start_date, end_date, FC_IRT=1)

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
        self.assertEqual(self.swb.__get_timedelta__(), timedelta(1))

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

    def test_swb_daily_with_no_irrigation_date(self):
        start_date = datetime(2008, 8, 1)
        end_date = datetime(2008, 8, 30)
        theta_init = self.swb.fc_mm - 0.75 * self.swb.raw_mm
        self.assertEqual(theta_init, 115.9375)
        irr_event_days = []

        self.swb.water_balance(theta_init, irr_event_days,
                               start_date, end_date, FC_IRT=1)

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

    def test_swb_daily_with_irrigations_dates(self):
        start_date = datetime(2008, 8, 1)
        end_date = datetime(2008, 8, 30)
        theta_init = 131.93750
        irr_event_days = [datetime(2008, 8, 8, 0, 0),
                          datetime(2008, 8, 15, 0, 0)]

        self.swb.water_balance(theta_init, irr_event_days,
                               start_date, end_date, FC_IRT=1)

        values1 = self.swb.wbm_report[0]
        self.assertEqual(values1['ETc'], 4.837)
        self.assertEqual(values1['Inet'], 0.0)
        self.assertEqual(values1['SWB'], 4.837)
        self.assertAlmostEqual(values1['Dr_i'], 16.39950)
        self.assertAlmostEqual(values1['Dr_1_next'], 16.39950)
        self.assertEqual(values1['Peff'], 0.0)
        self.assertEqual(values1['RO'], 0.0)
        self.assertEqual(values1['Inet'], 0.0)
        self.assertEqual(values1['Ks'], 1)
        self.assertEqual(values1['theta'], 127.1005)

        # Catch Inet
        values2 = self.swb.wbm_report[14]
        self.assertEqual(values2['date'], datetime(2008, 8, 15, 0, 0))
        self.assertEqual(values2['irrigate'], 0.0)
        self.assertAlmostEqual(values2['Dr_i'], 26.634999999999998)
        self.assertEqual(values2['Inet'], 26.634999999999998)
        self.assertEqual(values2['theta'], 143.5)

        values3 = self.swb.wbm_report[-1]
        self.assertEqual(values3['date'], datetime(2008, 8, 30, 0, 0))
        self.assertEqual(values3['irrigate'], 1.0)
        self.assertAlmostEqual(values3['Dr_i'], 51.83859483)
        self.assertAlmostEqual(values3['theta'], 91.66140517)

    def test_swb_daily_Inet_in_wrong_input(self):
        start_date = datetime(2008, 8, 1)
        end_date = datetime(2008, 8, 30)
        theta_init = 131.93750
        irr_event_days = [datetime(2008, 8, 8, 0, 0),
                          datetime(2008, 8, 15, 0, 0)]

        with self.assertRaises(ValueError):
            self.swb.water_balance(theta_init, irr_event_days,
                                   start_date, end_date,
                                   FC_IRT=1, Inet_in="Something Else")
