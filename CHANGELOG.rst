=========
Changelog
=========

2.8.1 (2025-12-08)
==================

* Use more recent Click (>=8.2).

2.8.0 (2025-12-08)
==================

* enhydris_api_client.post_tsdata() now accepts an optional "mode"
  argument.

2.7.0 (2025-11-07)
==================

* Added enhydris_api_client.put_timeseries().
* enhydris_api_client.list_stations() now accepts a query string.
* Added textbisect module.
* Added type hints.

2.6.0 (2025-10-01)
==================

* haggregate now accepts any fixed time step, not just "1h" and "1D".

2.5.2 (2025-09-30)
==================

* Rocc is now much faster when there is a considerable number of records
  that fail the test.
* Rocc can now be passed a progress callback (the purpose of this is for
  debugging speed issues).

2.5.1 (2025-09-29)
==================

* Fixed some rocc bugs.

2.5.0 (2025-09-27)
==================

Large improvements in the operation of rocc:

* It now supports implied thresholds
* It now only compares each record to previous records that have not
  failed the check.

2.4.1 (2025-09-17)
==================

* Fixed rocc not working properly with negative thresholds.

2.4.0 (2025-09-14)
==================

* Added ``enhydris_api_client.EnhydrisApiClient.list_timeseries_groups()``.

2.3.1 (2025-09-14)
==================

* This release REMOVES Python 3.13 compatibility which was wrongly added
  in 2.3.0. We can't add Python 3.13 compatibility before Ubuntu 26.04
  is released (see comment in pyproject.toml for more).

2.3.0 (2025-09-13)
==================

* Added ``enhydris_api_client.EnhydrisApiClient.list_stations()``.

2.2.3 (2025-03-26)
==================

Fixed an edge case in daily evaporation calculation: if an array was
provided and it had NaN at some point of the elevation raster, it was
crashing—now it returns NaN at that point in the result.

2.2.2 (2025-03-23)
==================

Fixed an error in daily evaporation calculation where, if the pressure
was provided, it was not converted with the unit converter.

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

We now depend on numpy<2, because some modules are not yet compatible
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
