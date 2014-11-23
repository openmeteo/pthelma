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

    def test_root_zone_depletion(self):
        # pthelma/tests/data/SoilWaterBalance_calculations.obs
        precipitation = Timeseries(time_step=TimeStep(1440, 0))
        instring = StringIO(precipitation_test_timeseries)
        precipitation.read_file(instring)

        evapotranspiration = Timeseries(time_step=Timeseries(1440, 0))
        instring = StringIO(evapotranspiration_test_timeseries)
        evapotranspiration.read_file(instring)

        swb = SoilWaterBalance(0.5, 1, 0.5, 0.75,
                               1, precipitation, evapotranspiration, 1.2, 1)
        depletion = swb.root_zone_depletion(datetime(2014, 11, 1), 100,
                                            datetime(2014, 11, 10))
        self.assertAlmostEqual(depletion, 79.6)

    def test_irrigation_water_amount(self):
        # pthelma/tests/data/SoilWaterBalance_calculations.obs
        precipitation = Timeseries(time_step=TimeStep(1440, 0))
        instring = StringIO(precipitation_test_timeseries)
        precipitation.read_file(instring)

        evapotranspiration = Timeseries(time_step=Timeseries(1440, 0))
        instring = StringIO(evapotranspiration_test_timeseries)
        evapotranspiration.read_file(instring)

        swb_model = SoilWaterBalance(0.5, 1, 0.5, 0.75, 1,
                                     precipitation, evapotranspiration, 1.2, 1)
        iwa = swb_model.irrigation_water_amount(datetime(2014, 11, 1),
                                                100, datetime(2014, 11, 10))
        self.assertAlmostEqual(iwa, 66.3333333)
