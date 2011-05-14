from pthelma.timeseries import (Timeseries, 
                               timeseries_bounding_dates_from_db)
import fpconst
from meteocalcs import HeatIndex, SSI
import copy


def GetTimeseriesCommonPeriod(tslist, start_date=None, end_date=None,
                              interval_exclusive=False, reject_nulls=True):
    assert(len(tslist)>0)
    common_period = []
    for date in tslist[0].iterkeys():
        if start_date and (date<start_date if not interval_exclusive\
                           else date<=start_date):
            continue
        if end_date and (date>end_date if not interval_exclusive\
                           else date>=end_date) :
            break
        value_rejected = False
        if reject_nulls and fpconst.isNaN(tslist[0][date]):
            continue
        for i in xrange(1, len(tslist)):
            if (not date in tslist[i]) or \
                       (reject_nulls and fpconst.isNaN(tslist[i][date])):
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
        else:
            assert(False)
        out_timeseries[date] = v
        

def MultiTimeseriesProcessDb(method, timeseries_arg, out_timeseries_id,
                             db, transaction=None, commit=True, options={}):
    out_timeseries = Timeseries(id = out_timeseries_id)
    opts = copy.deepcopy(options)
    if 'append_only' in opts:
        bounds = timeseries_bounding_dates_from_db(db, 
                                                   id = out_timeseries_id)
        opts['start_date'] = bounds[1] if bounds else None;
        opts['interval_exclusive'] = True
    tseries_arg={}
    for key in timeseries_arg:
        ts = Timeseries(id=timeseries_arg[key])
        if 'append_only' in opts and opts['start_date'] is not None:
            ts.read_from_db(db, onlybottom=True)
            if ts.bounding_dates()[0]>opts['start_date']:
                ts.read_from_db(db)
        else:
            ts.read_from_db(db)
        tseries_arg[key] = ts
    MultiTimeseriesProcess(method, tseries_arg, out_timeseries, opts)
    if 'append_only' in opts:
        out_timeseries.append_to_db(db=db, transaction=transaction,
                                    commit=commit)
    else:
        out_timeseries.write_to_db(db=db, transaction=transaction, 
                                   commit=commit)


def AggregateDbTimeseries(source_id, dest_id, db, read_tstep_func, transaction=None,
                          commit=True, missing_allowed=0.0,
                          missing_flag='MISSING', append_only=False):
    source = Timeseries(id=source_id, time_step=read_tstep_func(source_id))
    dest_step = read_tstep_func(dest_id)
    if append_only:
        bounds = timeseries_bounding_dates_from_db(db = db, id = dest_id)
        end_date = bounds[1] if bounds else None
    source.read_from_db(db)
    dest = source.aggregate(target_step=dest_step,
                            missing_allowed=missing_allowed, 
                            missing_flag=missing_flag)[0]
    dest.id = dest_id
    if append_only:
        d=dest.bounding_dates()
        while (d is not None) and (end_date is not None) and d[0]<=end_date:
            del dest[d[0]]
            d=dest.bounding_dates()
        dest.append_to_db(db=db, transaction=transaction, commit=commit)
    else:
        dest.write_to_db(db=db, transaction=transaction, commit=commit)
