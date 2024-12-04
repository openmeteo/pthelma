===========================================
rocc - Rate-of-change check for time series
===========================================

.. class:: Threshold

   A named tuple whose items are :attr:`delta_t` (a pandas interval
   specification) and :attr:`allowed_diff` (a floating point number).

.. function:: rocc.rocc(ahtimeseries, thresholds, symmetric=False, flag="TEMPORAL")

   Example ::

      from rocc import Threshold, rocc

      result = rocc(
         timeseries=a_htimeseries_object,
         thresholds=(
            Threshold("10min", 10),
            Threshold("20min", 15),
            Threshold("h", 40),
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

   If ``symmetric`` is ``True``, it is the absolute value of the change
   that matters, not its direction. In this case, ``allowed_diff`` must be
   positive. If ``symmetric`` is ``False`` (the default), only rates larger
   than positive ``allow_diff`` or rates smaller than negative
   ``allow_diff`` are flagged.
