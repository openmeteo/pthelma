import datetime


class SoilWaterBalance(object):
    """
    class swb.SoilWaterBalance:
        Calculates soil water balance.

        Attributes:
            fc: The field capacity [mm]
            wp: The wilting point [cm]
            rd: The crop root depth [cm]
            kc: The crop coefficient
            p: The crop depletion fraction
            precipitation: A daily Timeseries object [mm]
            evapotranspiration:  A daily Timeseries object [mm]
            rd_factor: root depth conversion fraction
            taw: Total available water, [m3m-3]
            raw: Readily available water,  [m3m-3]
            irrigation_efficiency: The irrigation efficiency factor

        Methods:
            root_zone_depletion:
                Calculates root zone depletion
                Inputs:
                    start_date: A datetime object
                    initial_soil_moisture: Initial Soil Moisture [mm]
                    end_date: A datetime object
                Output:
                    depletion: root zone depletion for end_date [mm]

            irrigation_water_amount:
                Calculates irrigation water needs based in irrigation method
                        efficiency
                Inputs:
                    start_date: A datetime object
                    initial_soil_moisture: Initial Soil Moisture [mm]
                    end_date: A datetime object
                Output:
                    irrigation_amount: irrigation water needs for end_date [mm]

    """

    def __init__(self, fc, wp, rd, kc, p, precipitation,
                 evapotranspiration, irrigation_efficiency, rd_factor=1):
        self.fc = fc
        self.wp = wp
        self.rd = rd
        self.kc = kc
        self.p = p
        self.precip = precipitation
        self.evap = evapotranspiration
        self.rd_factor = rd_factor
        self.taw = (self.fc - self.wp) * self.rd
        self.raw = self.p * self.taw
        self.irrigation_efficiency = irrigation_efficiency

    def root_zone_depletion(self, start_date, initial_soil_moisture, end_date):
        depletion = (initial_soil_moisture * self.rd * self.rd_factor) / self.fc
        delta = datetime.timedelta(days=1)
        day = start_date + delta
        while day <= end_date:
                depletion = depletion - self.precip[day] + self.kc * self.evap[day]
                if depletion < 0:
                    depletion = 0
                day += delta
        return depletion

    def irrigation_water_amount(self, start_date, initial_soil_moisture,
                                end_date):
        depletion = self.root_zone_depletion(start_date, initial_soil_moisture,
                                             end_date)
        irrigation_water_amount = depletion / self.irrigation_efficiency
        return irrigation_water_amount
