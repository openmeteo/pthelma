==============
haggregate API
==============

.. function:: haggregate.regularize(ts, new_date_flag="DATEINSERT", mode=haggregate.RegularizationMode.INTERVAL)

   Process *ts* (a HTimeseries_ object) and return a new time series
   (HTimeseries_ object), with a strict time step.

   *ts* must have the ``time_step`` attribute set (see HTimeseries_).

   If an error occurs, such as *ts* not having the ``time_step``
   attribute, :exc:`RegularizeError` (or a sublcass) is raised.

   *mode* can be :attr:`RegularizationMode.INSTANTANEOUS` or
   :attr:`RegularizationMode.INTERVAL` (:class:`RegularizationMode` is
   an :class:`Enum` class in module ``haggregate``). This affects the
   algorithm used. See :ref:`regularization-algorithm` below. The
   default is :attr:`RegularizationMode.INTERVAL` for backwards
   compatibility reasons, but letting it use the default is
   deprecated—you should always specify it.

.. function:: haggregate.aggregate(ts, target_step, method[, min_count=None][, missing_flag][, target_timestamp_offset])

   Process *ts* (a HTimeseries_ object) and return a new time series
   (HTimeseries_ object), with the aggregated series.  "target_step" and
   "target_timestamp_offset" are pandas "frequency" strings (see
   :ref:`haggregate_usage` for more).  *method* is "sum", "mean", "max" or
   "min".  *ts* must have a strictly regular step. If in doubt, call
   :func:`regularize` before calling :func:`aggregate`.

   If some of the source records corresponding to a destination record
   are missing, *min_count* specifies what will be done. If there fewer
   than *min_count* source records corresponding, the resulting
   destination record is null; otherwise, the destination record is
   derived even though some records are missing.  In that case, the flag
   specified by *missing_flag* is raised in the destination record. If
   missing flag contains the string ``{}``, it is replaced with the
   number of missing records. The recommended setting for *missing_flag*
   is ``MISSING{}``, which, for example, will result in ``MISSING3``
   when three records are missing. The default for *missing_flag* is
   ``MISS`` for backwards compatibility (it was ``MISS`` for some years,
   however this was undocumented), but this is deprecated; use
   ``MISSING{}``.

   If an error occurs, such as *ts* not having a strictly regular step,
   :exc:`AggregateError` (or a subclass) is raised.

.. _regularization-algorithm:

How regularization is performed
===============================

The source time series, *ts*, must not be an irregular time series;
it must have a time step, but this time step may have disturbances.
For example, it may be a ten-minute time series like this::

      2008-02-07 10:10 10.54
      2008-02-07 10:20 10.71
      2008-02-07 10:41 10.93
      2008-02-07 10:50 11.10
      2008-02-07 11:00 11.23

The above has a missing record (10:30) and a disturbance in the time
stamp of another record (10:41). :func:`regularize` would convert it
to this::

      2008-02-07 10:10 10.54
      2008-02-07 10:20 10.71
      2008-02-07 10:30 empty
      2008-02-07 10:40 10.93
      2008-02-07 10:50 11.10
      2008-02-07 11:00 11.23

That is, the result of :func:`regularize` is a time series with a
regular time step from beginning to end, with no missing records.

Specifically, he returned time series begins with the regular timestamp
A which is nearest to the timestamp of the first record of *ts*, and
ends at the timestamp B which is nearest to the last record of *ts*.
Between A and B, the returned time series contains records for all
regular timestamps, although some may be null.

The regularization does not perform any interpolation or otherwise
modify the time series values; it only modifies the time stamps,
leaving the values as is.  If you think the algorithm is insufficient
and you intend to extend it with a more clever one that does
interpolation, first check commit 67bceaa, which had one (or the
difference with the next commit).

A **regular timestamp** is one that falls exactly on the round time
step; e.g. for a ten-minute step, regular timestamps are 10:10,
10:20, etc., whereas irregular timestamps are 10:11, 10:25, etc. For
hourly time step, regular timestamps end in :00.

Instantaneous mode
------------------

When :samp:`{mode}=RegularizationMode.INSTANTANEOUS`, the value and
flags for each resulting record with (regular) timestamp *t* are
determined as follows:

1. If a nonempty record exists in *ts* and has timestamp *t*, that
   record's value and flags are used.
2. Otherwise, if a not null record exists in *ts* such that its
   timestamp is between ``t - time_step/2`` (inclusive) and ``t +
   time_step/2`` (non-inclusive), then the value and flags of this
   record (or the nearest such record, if there are more than one)
   are used (plus *new_date_flag*, explained below).
3. Otherwise, the value is null and no flags are set.

Whenever the algorithm results in creating a non-null record whose
timestamp does not have an exact match in *ts*, the flag specified
by *new_date_flag* is raised in the destination record, unless
*new_date_flag* is the empty string.

Interval mode
-------------

When :samp:`{mode}=RegularizationMode.INTERVAL`, essentially the same
rules are followed as for instantaneous, with these differences:

 * Step (1) applies even if the source time series record is empty. For
   example, consider these source records::

      09:00 4.7
      09:09 5.9
      09:10 empty
      09:20 3.1

   In this case, the regularized time series will have an empty record at
   09:10 rather than 5.9. (It would have 5.9 if a 09:10 record did not
   exist at all in the source time series.)

 * Step (2) applies only if there is exactly one record in the interval,
   and it is not null. For example::

      09:00 4.7
      09:09 5.9
      09:13 5.8
      09:20 3.1

   In this case, the resulting 09:10 record will be empty.

Rationale for the different modes
---------------------------------

If the variable is cumulative, such as rainfall, the time series record
indicates not what the value was in that time instant, but what happened
in the preceding interval. So, in the last example, what is the meaning
of the record ``09:13 5.8``? Does it mean that 5.8 mm of rain fell
between 09:09 and 09:13? Or is it between 09:03 and 09:13? And if that
is the case, why do we also have another record at 09:09? The situation
is too fishy to allow a safe conclusion when aggregating automatically,
and therefore we choose the conservative approach of marking 09:10 as
null, effectively declaring that we don't know what happened at that
time. Likewise, the existence of an empty record at 09:10 in the example
of step (1) is an indication of something fishy happening.

In instantaneous variables like temperature, the value of a record
doesn't always refer to the indicated instant, but depends on how the
measurement was made—sometimes it's the mean value of several samples
taken in the preceding interval. One way or the other, there doesn't
seem to be a reason to be too picky, so the rules are relaxed.

.. _HTimeseries: https://github.com/openmeteo/htimeseries
