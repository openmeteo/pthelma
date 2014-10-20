:mod:`tsprocess` --- Time series processing
===========================================

.. module:: tsprocess
   :synopsis: Time series processing.
.. moduleauthor:: Stefanos Kozanis <S.Kozanis@itia.ntua.gr>
.. sectionauthor:: Antonis Christofides <anthony@itia.ntua.gr>

This module provides some helper functions for time series
processing such as calculation of Evaporation, Bioclimatic
Indeces time series etc

Helper functions
----------------

.. function::  GetTimeseriesCommonPeriod(tslist[, start_date=None][, end_date=None][, interval_exclusive=False][, reject_nulls=True])

   A function inspired from delphi version of thelma.tsprocess.pas
   GetCommonPeriod. Reads the time series contained in the list
   object *tslist* and returns a list of datetime objects representing
   their common period.
   By default the common period would not contain time stamp of
   time series with null values. To override this set the
   *reject_nulls* paremeter to ``True``.
   By specifying *start_date* and / or *end_date* it returns a common
   period bounded by the interval defined by these two parameters respectively.
   Set *interval_exclusive* if you want the above interval to be
   exclusive for dates or else it is inclusive by default.

.. function:: MultiTimeseriesProcess(method, timeseries_arg, out_timeseries[, options={}])

   Execute processing of multi time series, e.g. calculates the heat
   index time series by airtemp and relhum timeseries.
   *method* is a string with possible values of:

    * ``HeatIndex``
    * ``SSI`` 
    * ``IDM_monthly``
    * ``IDM_annual``
    * ``BaromFormula``
    * ``OneStepDiff`` 

   *timeseries_arg* is a dictionary
   containg the input time series. For HeatIndex and SSI processing
   it should contain two time series specified by the keys
   ``'temp'`` and ``'rh'`` (e.g. ``{'temp': temp_ts, 'rh': rh_ts}``).
   For ``IDM`` a total (monthly or annual respect.) preciptiation should
   be specified with the ``'precip'`` key.
   For Barometric Formula , method name is ``BaromFormula``,
   'temp' is temperature time series (in deg C) and 'press'
   the atmospheric pressure (in hPa), you have also to pass and altitude
   difference in options as options['hdiff'].
   *out_timeseries* should be a :class:`Timeseries` object to write results.
   *options* is a dictionary holding the options. `'start_date'`
   and `'end_date'` in options could contain the bounds for the
   process. These dates are being passed in
   :func:`GetTimeseriesCommonPeriod`. When null values are passed, the
   output in these dates is also null.
   For ``OneStepDiff`` method, the time step of timeseries should be
   strict (it should have time_step defined) or else an exception is
   raised.

.. function:: MultiTimeseriesProcessDb(method, timeseries_arg, out_timeseries_id, db, read_tstep_func[, transaction=None][, commit=True][, options={}])

   Execute processing of multi time series by using the
   :func:`MultiTimeseriesProcess` function.
   For *method* see MultiTimeseriesProcess. *timeseries_arg* is a
   dictionary holding source time series ids as values, for keys
   values and their meaning see  MultiTimeseriesProcess. 
   *out_timeseries_id* is the id of the time series that will be written 
   in the database *db*. You may also set a database *transaction* or
   set the *commit* control. Add a key 'append_only' in options with
   a value of ``True`` if you want to just append new values in destination
   time series. In the case of append, the function will try to
   obtain data from source time series bottom fields to gain performance.
   ``read_tstep_func`` should be a function taking the argument of 
   time series id.

.. function:: AggregateDbTimeseries(source_id, dest_id, db, read_tstep_func[, transaction=None][, commit=None][, missing_allowed=0.0][, missing_flag='MISSING'][, append_only=False][, last_incomplete=False],[ all_incomplete=False])

   Do time series aggregation. For details on aggregation algorithm
   see the help of :meth:`pthelma.timeseries.aggregate`.
   *source_id* and *dest_id* are the database ids of source and
   destination time series respectively.
   *db* is database object. read_tstep_func should be a function
   taking the argument of time series id. For other options see
   aggregate and timeseries.write_to_db. If *append_only* is set
   to ``True``, the writing process will execute with the
   timeseries.append_to_db by writing only the new records.
   Currently the AggregateDbTimeseries will read the full source
   time series from database. In a future version, to improve
   performace, it should try to obtain records from time series
   bottom field.

.. function:: InterpolateDbTimeseries(source_id, dest_id, curve_type, curve_data, db[, data_columns=(0,1)][, logarithmic=False][, offset=0][, append_only=False][, transaction=None][, commit=True])

   Interpolate the time series with *source_id* in the curve described
   by *curve_data* and then write the results to a database time series
   with id of *dest_id*. *curve_data* is a string containing the
   curve(s) definition according to pthelma.curves specifications.
   *curve_type* is a string that should provided and takes one of the values
   ``'SingleCurve'`` or ``'StageDischargeMulti'``. *data_columns*,
   *logarithmic* and *offset* have meaning only if 'SingleCurve' is
   considered. For *data_columns*, *logarithmic* see pthelma.curves
   documentation. *offset* is the offset for independent variable,
   used only if *logarithmic* set to ``True``.
   You may also set a database *transaction* or
   set the *commit* control. Set *append_only* to ``True``
   if you want to just append new values in destination
   time series. In the case of append, the function will try to
   obtain data from source time series bottom fields to gain performance.
