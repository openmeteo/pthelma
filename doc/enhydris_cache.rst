.. _enhydris_cache:

:mod:`enhydris_cache` --- Local caching of data from an Enhydris server
=======================================================================

.. module:: enhydris_cache
   :synopsis: Local caching of data from an Enhydris server
.. moduleauthor:: Antonis Christofides <anthony@itia.ntua.gr>
.. sectionauthor:: Antonis Christofides <anthony@itia.ntua.gr>

.. class:: TimeseriesCache(cache_dir, timeseries_groups)
  
   Keeps certain time series cached in the filesystem. The time series
   is downloaded from Enhydris using the Enhydris web service API.
   *timeseries_groups* is a list; each item is a dictionary
   representing an Enhydris time series; its keys are *base_url*,
   *user*, *password*, *id*.

   .. method:: update()

      Downloads everything that has not already been downloaded (or all
      the time series if nothing is in the cache).

   .. method:: get_filename(base_url, timeseries_id)

      Returns the full pathname of the file containing the cached
      specified time series (the time series data in file format).
      The filename has the format
      :samp:`{cache_dir}/{qbase_url}_{id}`, where *qbase_url* is the
      ``urllib.parse.quote_plus(base_url)`` and *id* is the time
      series id.

.. class:: PondApp

   This class contains the :doc:`pond` command-line application. The
   :file:`pond` executable does little other than this::

      application = PondApp()
      application.run()
