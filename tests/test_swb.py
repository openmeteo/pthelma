import csv
from datetime import datetime, timedelta
from unittest import TestCase
from six import StringIO

from pthelma.timeseries import Timeseries, TimeStep
from pthelma.swb import SoilWaterBalance


DRY_SEASON_METEO_FILE = 'tests/data/swb/dry_season/meteorological_data.csv'
DRY_SEASON_DAILY_GENERAL_RESULTS_FILE = 'tests/data/swb/dry_season/daily_general_results.csv'
DRY_SEASON_DAILY_GENERAL_NO_IRRIGATION_DATES_RESULTS_FILE = 'tests/data/swb/dry_season/daily_general_results_no_irrigation_dates.csv'
DRY_SEASON_DAILY_GENERAL_WITH_IRRIGATION_DATES_RESULTS_FILE = 'tests/data/swb/dry_season/daily_general_results_with_irrigation_dates.csv'

WET_SEASON_METEO_FILE = 'tests/data/swb/wet_season/meteorological_data.csv'
WET_SEASON_DAILY_GENERAL_RESULTS_FILE = 'tests/data/swb/wet_season/daily_general_results.csv'
WET_SEASON_DAILY_GENERAL_NO_IRRIGATION_DATES_RESULTS_FILE = 'tests/data/swb/wet_season/daily_general_results_no_irrigation_dates.csv'
WET_SEASON_DAILY_GENERAL_WITH_IRRIGATION_DATES_RESULTS_FILE = 'tests/data/swb/wet_season/daily_general_results_with_irrigation_dates.csv'


def _get_csv_data(filepath):
    """Return csv data as dict

    :filepath: Absolute path of csv
    """
    with open(filepath) as f:
        data = [i for i in csv.DictReader(f)]
    return data

def _test_each_result_row(test, model_report, compare_model_results, columns):
    """Test each results csv row with model return results based on columns

    :test: TestCase object
    :model_report: Swb model results
    :compare_model_results: csv data results
    :columns: List of result key (header) to be tested
    """
    report_keys = model_report[0].keys()
    compare_keys = compare_model_results[0].keys()
    for i, (mr, cmr) in enumerate(zip(model_report, compare_model_results)):
        for key in columns:
            test.assertAlmostEqual(mr[key], float(cmr[key]), 2)


class SoilWaterBalanceDrySeasonDailyTestCase(TestCase):

    def setUp(self):
        input_data = _get_csv_data(DRY_SEASON_METEO_FILE)

        # Precipitatin
        self.precip = Timeseries(time_step=TimeStep(1440, 0))
        self.precip.read_file(StringIO(
            ''.join(["\n{}, {}\n".format(r['date'], r['p']) for r in input_data])
        ))
        # Evapotranspiration
        self.evap = Timeseries(time_step=TimeStep(1440, 0))
        self.evap.read_file(StringIO(
            ''.join(["\n{}, {}\n".format(r['date'], r['et']) for r in input_data])
        ))

        # Testing Period
        self.start_date = datetime(2008, 8, 1)
        self.end_date = datetime(2008, 8, 30)

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
        self.a = 0.424
        self.b = 0.932

        self.test_results_columns = [
            'CR', 'RO', 'Peff', 'DP', 'SWB', 'Dr_i', 'Dr_i_missing_Inet',
            'Inet', 'SWB', 'Ks', 'theta', 'irrigate'
        ]


        # Soil Water Balance Instance
        self.swb = SoilWaterBalance(
            self.fc, self.wp, self.rd,
            self.kc, self.p, self.peff, self.irr_eff,
            self.theta_s, self.precip, self.evap,
            self.a, self.b,
            self.rd_factor, 16.2
        )

    def test_input_data_precip(self):
        self.assertTrue(
            self.precip.bounding_dates(), (self.start_date, self.end_date)
        )
        self.assertTrue(len(self.precip), 30)

    def test_input_data_evap(self):
        self.assertTrue(
            self.evap.bounding_dates(), (self.start_date, self.end_date)
        )
        self.assertTrue(len(self.evap), 30)

    def test_parameters_convertions(self):
        self.assertEqual(self.swb.fc_mm, 143.5)
        self.assertEqual(self.swb.wp_mm, 70.0)
        self.assertEqual(self.swb.theta_s_mm, 212.5)
        self.assertAlmostEqual(self.swb.taw, 0.147)
        self.assertEqual(self.swb.taw_mm, 73.5)
        self.assertAlmostEqual(self.swb.raw, 0.0735)
        self.assertEqual(self.swb.raw_mm, 36.75)
        self.assertEqual(self.swb.lowlim_theta, 0.2135)
        self.assertEqual(self.swb.lowlim_theta_mm, 106.75)
        self.assertAlmostEqual(self.swb.draintime, 16.2, 1)

    def test_swd_against_daily_general_results(self):
        theta_init = self.swb.fc_mm
        compare_model_results = _get_csv_data(
            DRY_SEASON_DAILY_GENERAL_RESULTS_FILE
        )
        model_report =  self.swb.water_balance(
            theta_init, [], self.start_date, self.end_date,
            FC_IRT=1, as_report=True
        )
        self.assertTrue(compare_model_results, list)
        self.assertTrue(model_report, list)
        self.assertEqual(self.swb.__get_timedelta__(), timedelta(1))

        _test_each_result_row(self, model_report, compare_model_results,
                              self.test_results_columns)

    def test_swd_against_daily_general_results_no_irrigation_dates(self):
        theta_init = 143.5
        compare_model_results = _get_csv_data(
            DRY_SEASON_DAILY_GENERAL_NO_IRRIGATION_DATES_RESULTS_FILE
        )
        model_report =  self.swb.water_balance(
            theta_init, [], self.start_date, self.end_date,
            FC_IRT=1, as_report=True
        )
        self.assertTrue(compare_model_results, list)
        self.assertTrue(model_report, list)
        self.assertEqual(self.swb.__get_timedelta__(), timedelta(1))

        _test_each_result_row(self, model_report, compare_model_results,
                              self.test_results_columns)

    def test_swd_against_daily_general_results_with_irrigation_dates(self):
        theta_init = 143.5
        irr_event_days = [
            (datetime(2008, 8, 11, 0, 0), 30.0),
            (datetime(2008, 8, 24, 0, 0), 90.0),
        ]

        compare_model_results = _get_csv_data(
            DRY_SEASON_DAILY_GENERAL_WITH_IRRIGATION_DATES_RESULTS_FILE
        )
        model_report =  self.swb.water_balance(
            theta_init, irr_event_days, self.start_date, self.end_date,
            FC_IRT=1, as_report=True
        )
        self.assertTrue(compare_model_results, list)
        self.assertTrue(model_report, list)
        self.assertEqual(self.swb.__get_timedelta__(), timedelta(1))

        _test_each_result_row(self, model_report, compare_model_results,
                            self.test_results_columns )


class SoilWaterBalanceWetSeasonDailyTestCase(TestCase):

    def setUp(self):
        input_data = _get_csv_data(WET_SEASON_METEO_FILE)

        # Precipitatin
        self.precip = Timeseries(time_step=TimeStep(1440, 0))
        self.precip.read_file(StringIO(
            ''.join(["\n{}, {}\n".format(r['date'], r['p']) for r in input_data])
        ))
        # Evapotranspiration
        self.evap = Timeseries(time_step=TimeStep(1440, 0))
        self.evap.read_file(StringIO(
            ''.join(["\n{}, {}\n".format(r['date'], r['et']) for r in input_data])
        ))

        # Testing Period
        self.start_date = datetime(2016, 3, 9)
        self.end_date = datetime(2016, 5, 9)

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
        self.a = 0.424
        self.b = 0.932

        self.test_results_columns = [
            'ETo', 'ETc', 'CR', 'RO', 'Peff', 'DP', 'SWB', 'Dr_i', 'Dr_i_missing_Inet',
            'Inet', 'SWB', 'Ks', 'theta', 'irrigate'
        ]

        # Soil Water Balance Instance
        self.swb = SoilWaterBalance(
            self.fc, self.wp, self.rd,
            self.kc, self.p, self.peff, self.irr_eff,
            self.theta_s, self.precip, self.evap,
            self.a, self.b,
            self.rd_factor, 16.2
        )

    def test_input_data_precip(self):
        self.assertEqual(
            self.precip.bounding_dates(), (self.start_date, self.end_date)
        )
        self.assertEqual(len(self.precip), 62)

    def test_input_data_evap(self):
        self.assertEqual(
            self.evap.bounding_dates(), (self.start_date, self.end_date)
        )
        self.assertEqual(len(self.evap), 62)

    def test_parameters_convertions(self):
        self.assertEqual(self.swb.fc_mm, 143.5)
        self.assertEqual(self.swb.wp_mm, 70.0)
        self.assertEqual(self.swb.theta_s_mm, 212.5)
        self.assertAlmostEqual(self.swb.taw, 0.147)
        self.assertEqual(self.swb.taw_mm, 73.5)
        self.assertAlmostEqual(self.swb.raw, 0.0735)
        self.assertEqual(self.swb.raw_mm, 36.75)
        self.assertEqual(self.swb.lowlim_theta, 0.2135)
        self.assertEqual(self.swb.lowlim_theta_mm, 106.75)
        self.assertAlmostEqual(self.swb.draintime, 16.2, 1)

    def test_swd_against_daily_general_results(self):
        theta_init = self.swb.fc_mm
        compare_model_results = _get_csv_data(
            WET_SEASON_DAILY_GENERAL_RESULTS_FILE
        )
        model_report =  self.swb.water_balance(
            theta_init, [], self.start_date, self.end_date,
            FC_IRT=1, as_report=True
        )
        self.assertTrue(compare_model_results, list)
        self.assertTrue(model_report, list)
        self.assertEqual(self.swb.__get_timedelta__(), timedelta(1))

        _test_each_result_row(self, model_report, compare_model_results,
                              self.test_results_columns)

    def test_swd_against_daily_general_results_no_irrigation_dates(self):
        theta_init = 143.5
        compare_model_results = _get_csv_data(
            WET_SEASON_DAILY_GENERAL_NO_IRRIGATION_DATES_RESULTS_FILE
        )
        model_report =  self.swb.water_balance(
            theta_init, [], self.start_date, self.end_date,
            FC_IRT=1, as_report=True
        )
        self.assertTrue(compare_model_results, list)
        self.assertTrue(model_report, list)
        self.assertEqual(self.swb.__get_timedelta__(), timedelta(1))

        _test_each_result_row(self, model_report, compare_model_results,
                              self.test_results_columns)

    def test_swd_against_daily_general_results_with_irrigation_dates(self):
        theta_init = 143.5
        irr_event_days = [
            (datetime(2016, 4, 26, 0, 0), 40.0),
            (datetime(2016, 5, 8, 0, 0), 40.0),
        ]

        compare_model_results = _get_csv_data(
            WET_SEASON_DAILY_GENERAL_WITH_IRRIGATION_DATES_RESULTS_FILE
        )
        model_report =  self.swb.water_balance(
            theta_init, irr_event_days, self.start_date, self.end_date,
            FC_IRT=1, as_report=True
        )
        self.assertTrue(compare_model_results, list)
        self.assertTrue(model_report, list)
        self.assertEqual(self.swb.__get_timedelta__(), timedelta(1))

        _test_each_result_row(self, model_report, compare_model_results,
                              self.test_results_columns)
