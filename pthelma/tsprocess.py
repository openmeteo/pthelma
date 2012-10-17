#!/usr/bin/python
"""
tsprocess - time series processing

Copyright (C) 2005-2011 National Technical University of Athens
Copyright (C) 2011 Stefanos Kozanis, Antonis Christofides

This program is free software; you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation; either version 2 of the License, or
(at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.
"""

from pthelma.timeseries import (Timeseries, 
                               timeseries_bounding_dates_from_db)
import math
from StringIO import StringIO
from pthelma.meteocalcs import HeatIndex, SSI, IDM, BarometricFormula
from pthelma.curves import (CurvePoint, TransientCurveList,
                            TransientCurve,)
from pthelma.datetimelist import DatetimeList
import copy


def GetTimeseriesCommonPeriod(tslist, start_date=None, end_date=None,
                              interval_exclusive=False, reject_nulls=True):
    assert(len(tslist)>0)
    common_period = DatetimeList()
    for date in tslist[0].iterkeys():
        if start_date and (date<start_date if not interval_exclusive\
                           else date<=start_date):
            continue
        if end_date and (date>end_date if not interval_exclusive\
                           else date>=end_date) :
            break
        value_rejected = False
        if reject_nulls and math.isnan(tslist[0][date]):
            continue
        for i in xrange(1, len(tslist)):
            if (not date in tslist[i]) or \
                       (reject_nulls and math.isnan(tslist[i][date])):
                value_rejected = True
                break
        if not value_rejected:
            common_period.append(date)
    return common_period


def MultiTimeseriesProcess(method, timeseries_arg, out_timeseries,
                           options={}):
    start_date = None
    end_date = None
    interval_exclusive = False
    if 'start_date' in options:
        start_date = options['start_date']
    if 'end_date' in options:
        end_date = options['end_date']
    if 'interval_exclusive' in options:
        interval_exclusive = options['interval_exclusive']
    common_period = GetTimeseriesCommonPeriod( timeseries_arg.values(),
                    start_date=start_date, end_date=end_date, 
                    interval_exclusive = interval_exclusive, reject_nulls=False)
    out_timeseries.clear()
    v = 0.0000
    first_timeseries = timeseries_arg[timeseries_arg.keys()[0]]
    for date in common_period:
        if method == 'HeatIndex':
            v = HeatIndex(timeseries_arg['temp'][date],
                          timeseries_arg['rh'][date])
        elif method == 'SSI':
            v = SSI(timeseries_arg['temp'][date],
                    timeseries_arg['rh'][date])
        elif method == 'IDM_monthly':
            v = IDM(timeseries_arg['temp'][date],
                    timeseries_arg['precip'][date], False)
        elif method == 'IDM_annual':
            v = IDM(timeseries_arg['temp'][date],
                    timeseries_arg['precip'][date], True)
        elif method == 'BaromFormula':
            v = BarometricFormula(timeseries_arg['temp'][date],
                    timeseries_arg['press'][date], options['hdiff'])
        elif method == 'OneStepDiff':
            prev_date = first_timeseries.time_step.previous(date)
            if prev_date<first_timeseries.bounding_dates()[0]:
                v = float('NaN')
            else:
                v = first_timeseries[date]-first_timeseries[prev_date]
        else:
            assert(False)
        out_timeseries[date] = v
        

def MultiTimeseriesProcessDb(method, timeseries_arg, out_timeseries_id,
                             db, read_tstep_func, transaction=None, 
                             commit=True, options={}):
    out_timeseries = Timeseries(id = out_timeseries_id)
    opts = copy.deepcopy(options)
    if 'append_only' in opts and opts['append_only']:
        bounds = timeseries_bounding_dates_from_db(db, 
                                                   id = out_timeseries_id)
        opts['start_date'] = bounds[1] if bounds else None;
        opts['interval_exclusive'] = True
    tseries_arg={}
    for key in timeseries_arg:
        ts = Timeseries(id=timeseries_arg[key])
        if ('append_only' in opts and opts['append_only']) \
                         and opts['start_date'] is not None:
            ts.read_from_db(db, bottom_only=True)
            if ts.bounding_dates()[0]>opts['start_date']:
                ts.read_from_db(db)
        else:
            ts.read_from_db(db)
        ts.time_step = read_tstep_func(ts.id)
        tseries_arg[key] = ts
    MultiTimeseriesProcess(method, tseries_arg, out_timeseries, opts)
    if 'append_only' in opts and opts['append_only']:
        out_timeseries.append_to_db(db=db, transaction=transaction,
                                    commit=commit)
    else:
        out_timeseries.write_to_db(db=db, transaction=transaction, 
                                   commit=commit)


def AggregateDbTimeseries(source_id, dest_id, db, read_tstep_func, transaction=None,
                          commit=True, missing_allowed=0.0,
                          missing_flag='MISSING', append_only=False,
                          last_incomplete=False, all_incomplete=False):
    source = Timeseries(id=source_id, time_step=read_tstep_func(source_id))
    dest_step = read_tstep_func(dest_id)
    if append_only:
        bounds = timeseries_bounding_dates_from_db(db = db, id = dest_id)
        end_date = bounds[1] if bounds else None
    source.read_from_db(db)
    dest = source.aggregate(target_step=dest_step,
                            missing_allowed=missing_allowed, 
                            missing_flag=missing_flag,
                            last_incomplete=last_incomplete,
                            all_incomplete=all_incomplete)[0]
    dest.id = dest_id
    if append_only:
        d=dest.bounding_dates()
        while (d is not None) and (end_date is not None) and d[0]<=end_date:
            del dest[d[0]]
            d=dest.bounding_dates()
        dest.append_to_db(db=db, transaction=transaction, commit=commit)
    else:
        dest.write_to_db(db=db, transaction=transaction, commit=commit)


def InterpolateDbTimeseries(source_id, dest_id, curve_type, curve_data,
                            db, data_columns=(0,1), logarithmic=False,
                            offset=0, append_only=False,
                            transaction=None, commit=True):
    if append_only:
        bounds = timeseries_bounding_dates_from_db(db, id = dest_id)
        start_date = bounds[1] if bounds else None;
    ts = Timeseries(id=source_id)
    if append_only and start_date is not None:
        ts.read_from_db(db, bottom_only=True)
        if ts.bounding_dates()[0]>start_date:
            ts.read_from_db(db)
        while ts.bounding_dates()[0]<=start_date:
            del(ts[ts.bounding_dates()[0]])
            if len(ts)==0: return
    else:
        ts.read_from_db(db)
    curve_list = TransientCurveList()
    if curve_type=='SingleCurve':
        curve_list.add(logarithmic=logarithmic, 
                       offset=CurvePoint(offset, 0))
        super(TransientCurve, 
              curve_list[0]).read_fp(StringIO(curve_data),
                                                data_columns)
    elif curve_type=='StageDischargeMulti':
        curve_list.read_fp(StringIO(curve_data))
    else:
        assert(False)
    out_timeseries = curve_list.interpolate_ts(ts)
    out_timeseries.id = dest_id
    if append_only:
        out_timeseries.append_to_db(db=db, transaction=transaction,
                                    commit=commit)
    else:
        out_timeseries.write_to_db(db=db, transaction=transaction, 
                                   commit=commit)


