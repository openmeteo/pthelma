from datetime import datetime
import textwrap
from unittest import TestCase
from six import StringIO

from pthelma.timeseries import Timeseries, TimeStep
from pthelma.runoff import SCS


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


class SCSTestCase(TestCase):

    def test_scs_runoff(self):
        precipitation = Timeseries(time_step=TimeStep(1440, 0))
        instring = StringIO(precipitation_test_timeseries)
        precipitation.read_file(instring)

        scs = SCS(78, precipitation)
        scs_runoff = scs.calculate(datetime(2014, 11, 1),
                                   datetime(2014, 11, 10), 0.2)
        self.assertAlmostEqual(scs_runoff, 0)
