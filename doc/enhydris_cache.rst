.. _enhydris_cache:

:mod:`enhydris_cache` --- Local caching of data from an Enhydris server
=======================================================================

.. module:: enhydris_cache
   :synopsis: Local caching of data from an Enhydris server
.. moduleauthor:: Antonis Christofides <anthony@itia.ntua.gr>
.. sectionauthor:: Antonis Christofides <anthony@itia.ntua.gr>

.. class:: TimeseriesCache(timeseries_groups)
  
   Keeps certain time series cached in the filesystem. The time series
   is downloaded from Enhydris using the Enhydris web service API.
   *timeseries_groups* is a list; each item is a dictionary
   representing an Enhydris time series; its keys are *base_url*,
   *user*, *password*, *id*, and *file*; the latter is the filename of
   the file to which the time series will be cached (absolute or
   relative to the current working directory).

   .. method:: update()

      Downloads everything that has not already been downloaded (or all
      the time series if nothing is in the cache).

.. class:: PondApp

   This class contains the :doc:`pond` command-line application. The
   :file:`pond` executable does little other than this::

      application = PondApp()
      application.run()
