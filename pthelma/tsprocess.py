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
        opts['start_date'] = timeseries_bounding_dates_from_db(db, 
                                                   id = out_timeseries_id)[1]
        opts['interval_exclusive'] = True
    tseries_arg={}
    for key in timeseries_arg:
        ts = Timeseries(id=timeseries_arg[key])
        if 'append_only' in opts:
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
