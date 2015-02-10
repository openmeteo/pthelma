from datetime import datetime
import textwrap
from unittest import TestCase

from six import StringIO

from pthelma.timeseries import Timeseries, TimeStep
from pthelma.swb import SoilWaterBalance


precipitation_test_timeseries = textwrap.dedent("""\
            2014-11-01,0,
            2014-11-02,0,
            2014-11-03,0,
            2014-11-04,10,
            2014-11-05,7,
            2014-11-06,4,
            2014-11-07,0,
            2014-11-08,2,
            2014-11-09,1,
            2014-11-10,0,
            """)

evapotranspiration_test_timeseries = textwrap.dedent("""\
            2014-11-01,0,
            2014-11-02,0,
            2014-11-03,0,
            2014-11-04,2,
            2014-11-05,1.4,
            2014-11-06,0.8,
            2014-11-07,0,
            2014-11-08,0.4,
            2014-11-09,0.2,
            2014-11-10,0,
            """)


class SoilWaterBalanceTestCase(TestCase):

    def setUp(self):
        self.precip = Timeseries(time_step=TimeStep(1440, 0))
        instring = StringIO(precipitation_test_timeseries)
        self.precip.read_file(instring)

        self.evap = Timeseries(time_step=Timeseries(1440, 0))
        instring = StringIO(evapotranspiration_test_timeseries)
        self.evap.read_file(instring)
        self.swb = SoilWaterBalance(0.5, 1, 0.5, 0.75,
                                    1, self.precip, self.evap, 1.2, 1)

    def test_root_zone_depletion(self):
        # pthelma/tests/data/SoilWaterBalance_calculations.obs
        depletion = self.swb.root_zone_depletion(datetime(2014, 11, 1), 100,
                                                 datetime(2014, 11, 10))
        self.assertAlmostEqual(depletion, 79.6)

    def test_depletion_report(self):
        self.swb.root_zone_depletion(datetime(2014, 11, 1), 100,
                                     datetime(2014, 11, 10))

        len_report = len(self.swb.depletion_report)
        sample_report_item = self.swb.depletion_report[4]
        report_keys = [k for k in sample_report_item.keys()]
        expected_keys = ['precip', 'evap', 'rd', 'depletion',
                         'fc', 'ism', 'date']

        self.assertEqual(len_report, 9)
        self.assertEqual(sample_report_item['precip'], 4)
        self.assertListEqual(report_keys, expected_keys)

    def test_irrigation_water_amount(self):
        # pthelma/tests/data/SoilWaterBalance_calculations.obs
        iwa = self.swb.irrigation_water_amount(datetime(2014, 11, 1),
                                               100, datetime(2014, 11, 10))
        self.assertAlmostEqual(iwa, 66.3333333)
