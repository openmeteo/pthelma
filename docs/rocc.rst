===========================================
rocc - Rate-of-change check for time series
===========================================

.. class:: Threshold

   A named tuple whose items are :attr:`delta_t` (a pandas interval
   specification) and :attr:`allowed_diff` (a floating point number).

.. function:: rocc.rocc(ahtimeseries, thresholds, symmetric=False, flag="TEMPORAL", progress_callback=lambda x: None)

   Example ::

      from rocc import Threshold, rocc

      result = rocc(
         timeseries=a_htimeseries_object,
         thresholds=(
            Threshold("10min", 10),
            Threshold("20min", 15),
            Threshold("1h", 40),
         ),
         symmetric=True,
         flag="MYFLAG",
      )

   ``timeseries`` is a :class:`HTimeseries` object.  ``thresholds`` is
   a list of :class:`Threshold` objects.

   The function checks whether there exist intervals during which the
   value of the time series changes by more than the specified
   threshold. The offending records are flagged with the specified
   ``flag``.

   ``progress_callback`` is a function that is periodically called
   (every 10 thousand records processed) with the percentage completed
   (as a number between 0 and 1).

   It returns a list of strings describing where the thresholds have been
   exceeded.

   If ``flag`` is ``None`` or the empty string, then the offending records
   are not flagged, and the only result is the returned value.

   Here is an example time series::

      2020-10-06 14:30    24.0
      2020-10-06 14:40    25.0  
      2020-10-06 14:50    36.0 *
      2020-10-06 15:01    51.0
      2020-10-06 15:21    55.0  
      2020-10-06 15:31    65.0  
      2020-10-06 15:41    75.0 *
      2020-10-06 15:51    70.0

   After running ``rocc()`` with the ``thresholds`` specified in the
   example above, the records marked with a star will be flagged. The
   record ``14:50`` will be flagged because in the preceding 10-minute
   interval the value increases by 11, which is more than 10. The record
   ``15:41`` will be flagged because in the preceding 20-minute interval
   the value increases by 20, which is more than 15. The record ``15:01``
   will be unflagged; although there's a large difference since ``14:40``,
   this is 21 minutes, not 20, so the 20-minute threshold of 15 does not
   apply; likewise, there's a difference of 15 from ``14:50``, which does
   not exceed the 20-minute threshold of 15, and while it does exceed the
   10-minute threshold of 10, it's 11 minutes, not 10. There's also not any
   difference larger than 40 within an hour anywhere.

   The return value in this example will be a list of two strings::

      "2020-10-06T14:50  +11.0 in 10min (> 10.0)"
      "2020-10-06T15:41  +20.0 in 20min (> 15.0)"

   The return value should only be used for consumption by humans; it is
   subject to change.

   If a 10min threshold is 10, then a 20min threshold of 20 is
   automatically implied, and a 30min threshold of 30, and so on. The
   implied thresholds can be overriden with lower values.  Likewise, if
   the 10min threshold is 10, and the (explicit) 20min threshold is 15,
   then a 30min threshold of 25, and so on, is implied. The implied
   thresholds are checked only against the previous valid record (a
   valid record is one that has not already failed the rate-of-change
   check), so, with the thresholds ``"10min", 10`` and ``"20min", 15``,
   the second record of the following will fail the check::

      2020-10-06 14:30,25.00,
      2020-10-06 15:00,50.01,

   The explicit thresholds, on the other hand, are checked against all
   applicable previous valid records.

   The implied thresholds are checked only if the difference between the
   timestamp of the current record and the timestamp of the previous
   valid record is up to 100 times the explicit threshold with the
   largest time step. So with the thresholds ``"10min", 2`` and ``"1h",
   6``, if a record is more than 100 hours after the previous valid
   record will always pass.

   If ``symmetric`` is ``True``, it is the absolute value of the change
   that matters, not its direction. In this case, ``allowed_diff`` should
   be positive (its sign is actually ignored). If ``symmetric`` is
   ``False`` (the default), only rates larger than positive ``allow_diff``
   or rates smaller than negative ``allow_diff`` fail.
