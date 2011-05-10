from pthelma.timeseries import Timeseries
import fpconst
from meteocalcs import HeatIndex, SSI

def GetTimeseriesCommonPeriod(tslist, start_date=None, end_date=None,
                              reject_nulls=True):
    assert(len(tslist)>0)
    common_period = []
    for date in tslist[0].iterkeys():
        if start_date and (date<start_date):
            continue
        if end_date and (date>end_date):
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
    if 'start_date' in options:
        start_date = options['start_date']
    if 'end_date' in options:
        end_date = options['end_date']
    common_period = GetTimeseriesCommonPeriod( timeseries_arg.values(),
                    start_date=start_date, end_date=end_date, reject_nulls=False)
    out_timeseries.clear()
    v = 0.0000
    for date in common_period:
        if method == 'HeatIndex':
            v = HeatIndex(timeseries_arg['temp'][date],
                          timeseries_arg['rh'][date])
        elif method == 'SSI':
            v = SSI(timeseries_arg['temp'][date],
                    timeseries_arg['rh'][date])
        else:
            assert(False)
        out_timeseries[date] = v
    
        


