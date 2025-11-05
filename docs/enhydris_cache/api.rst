.. _enhydris_cache_api:

==================
enhydris-cache API
==================

``import enhydris_cache``

.. class:: enhydris_cache.TimeseriesCache(timeseries_groups)
  
   Keeps certain time series cached in the filesystem. The time series
   is downloaded from Enhydris using the Enhydris web service API.
   *timeseries_groups* is a list; each item is a dictionary
   representing an Enhydris time series; its keys are *base_url*,
   *auth_token*, *station_id*, *timeseries_group_id*, *timeseries_id*,
   and *file*; the latter is the filename of the file to which the
   time series will be cached (absolute or relative to the current
   working directory).

   .. method:: update()

      Downloads everything that has not already been downloaded (or all
      the time series if nothing is in the cache).
