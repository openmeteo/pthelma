=========
Changelog
=========

2.2.1 (2025-03-19)
==================

The hspatial.integrate() function now accepts GeoDjango objects as some
of its arguments in addition to plain GDAL objects.

2.2.0 (2025-03-04)
==================

Added function "evaporation.cloud2radiation()" that estimates average
daily solar radiation given cloud cover.

2.1.1 (2025-02-21)
==================

We now depend on numpy<1, because some modules are not yet compatible
with numpy 2.

2.1.0 (2025-01-10)
==================

* haggregate: The ``missing_flag`` parameter to ``aggregate()`` can now
  include the substring "{}", which will be replaced with the number of
  missing values.

2.0.0 (2024-12-04)
==================

We now use "h" instead of "H", and generally we use modern pandas time
step ("frequency") designations.

1.1.0 (2024-12-01)
==================

Added package rocc (equivalent to rocc 3.0).

1.0.0 (2024-11-29)
==================

This is a different pthelma from the old 0.14, which had been abandoned
in favor of a number of separate packages. However, maintaining all
these separate packages was too cumbersome and now we re-combine them
here.

The packages recombined in pthelma 1.0.0 are:
  * htimeseries 8.0
  * hspatial 4.1
  * evaporation 2.0
  * haggregate 3.1
  * enhydris-api-client 4.0
  * enhydris-cache 2.0
