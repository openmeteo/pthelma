from datetime import datetime, timedelta, tzinfo
from unittest import TestCase

import numpy as np

from pthelma.evaporation import PenmanMonteith


class PenmanMonteithTest(TestCase):

    class SenegalTzinfo(tzinfo):
        """
        We test using Example 19, p. 75, of Allen et al. (1998). The example
        calculates evaporation in Senegal.  Although Senegal has time
        Afrika/Dakar, which is the same as UTC, Example 19 apparently assumes
        that its time zone is actually UTC-01:00 (which would be more
        consistent with its longitude, which may be the reason for the error).
        So we make the same assumption as example 19, in order to get the same
        result.
        """

        def utcoffset(self, dt):
            return -timedelta(hours=1)

        def dst(self, dt):
            return timedelta(0)

    tzinfo = SenegalTzinfo()

    def test_point(self):
        # Apply Allen et al. (1998) Example 19 page 75.
        pm = PenmanMonteith(albedo=0.23,
                            nighttime_solar_radiation_ratio=0.8,
                            elevation=8,
                            latitude=16.217,
                            longitude=-16.25,
                            step_length=timedelta(hours=1)
                            )

        result = pm.calculate(temperature=38,
                              humidity=52,
                              wind_speed=3.3,
                              pressure=101.3,
                              solar_radiation=2.450,
                              adatetime=datetime(2014, 10, 1, 15, 0,
                                                 tzinfo=self.tzinfo))
        self.assertAlmostEqual(result, 0.63, places=2)
        result = pm.calculate(temperature=28,
                              humidity=90,
                              wind_speed=1.9,
                              pressure=101.3,
                              solar_radiation=0,
                              adatetime=datetime(2014, 10, 1, 2, 30,
                                                 tzinfo=self.tzinfo))
        self.assertAlmostEqual(result, 0.0, places=2)

    def test_grid(self):
        # We use a 2x1 grid, where point 1, 1 is the same as Example 19, and
        # point 1, 2 has some different values.
        pm = PenmanMonteith(albedo=0.23,
                            nighttime_solar_radiation_ratio=0.8,
                            elevation=8,
                            latitude=16.217,
                            longitude=np.array([-16.25, -15.25]),
                            step_length=timedelta(hours=1)
                            )
        result = pm.calculate(temperature=np.array([38, 28]),
                              humidity=np.array([52, 42]),
                              wind_speed=np.array([3.3, 2.3]),
                              pressure=101.3,
                              solar_radiation=np.array([2.450, 1.450]),
                              adatetime=datetime(2014, 10, 1, 15, 0,
                                                 tzinfo=self.tzinfo))
        np.testing.assert_almost_equal(result, np.array([0.63, 0.36]),
                                       decimal=2)
