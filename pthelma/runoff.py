import datetime


class SCS(object):
    """
    class runoff.SCS:
        Calculates runoff based on emprical Curve Number.

        Attributes:
            CN: The curve number emprical parameter
            precipitation: A daily Timeseries object [mm]

        Methods:
            scs_runoff:
                Calculates runoff based on emprical Curve Number
                Inputs:
                    start_date: A datetime object
                    end_date: A datetime object
                    L_factor: Initial Abstration factor
                Output:
                    runoff: Surface runoff at end_date [mm]
    """

    def __init__(self, CN, precipitation):
        self.cn = CN
        self.precip = precipitation

    def calculate(self, start_date, end_date, L_factor=0.2):
        S_max = (1000 / self.cn) - 10  # Soil Max
        delta = datetime.timedelta(days=1)
        day = start_date + delta
        while day <= end_date:
            if self.precip[day] <= L_factor * S_max:
                runoff = 0
            else:
                runoff = (self.precip[day] - L_factor * S_max) ** 2 / self.precip[day] - (L_factor * S_max) + S_max
            day += delta
        return runoff
