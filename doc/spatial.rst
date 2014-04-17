.. _spatial:

:mod:`spatial` --- Utilities for spatial interpolation
======================================================

.. module:: spatial
   :synopsis: Utilities for spatial interpolation.
.. moduleauthor:: Antonis Christofides <anthony@itia.ntua.gr>
.. sectionauthor:: Antonis Christofides <anthony@itia.ntua.gr>

.. function:: idw(point, data_layer, alpha=1)

   Uses the inverse distance weighting method to calculate the value
   for a single point.

   *data_layer* is an :class:`ogr.Layer` object containing one or more
   points with values (all data_layer features must be points and must
   also have a value property).  *point* is an :class:`ogr.Point`
   object.  This function applies the IDW method to calculate the
   value of *point* given the values of the points of *data_layer*.

   Distances are raised to power -*alpha*; this means that for *alpha*
   > 1, the so-called distance-decay effect will be more than
   proportional to an increase in distance, and vice-versa.

.. function:: interpolate_spatially(dataset, data_layer, target_band, funct, kwargs={})

   Performs interpolation on an entire surface.

   *dataset* is a gdal dataset whose first band is the mask; the
   gridpoints of the mask have value zero or non-zero. *data_layer* is
   an :class:`ogr.Layer` object containing one or more points with
   values (all *data_layer* features must be points and must also have
   a *value* attribute). *target_band* is a band on which the result
   will be written; it must have the same GeoTransform as *dataset*.
   *funct* is a python function whose first two arguments are an
   :class:`ogr.Point` and *data_layer*, and *kwargs* is a dictionary
   with keyword arguments to be given to *funct*.

   This function calls *funct* for each non-zero gridpoint of the
   mask.

   NOTE: It is assumed that there is no x_rotation and y_rotation
   (i.e. that :samp:`dataset.GetGeoTransform()[3]` and :samp:`[4]` are
   zero).

.. function:: create_ogr_layer_from_stations(group, data_source, cache_dir)

   Creates and returns an :class:`ogr.Layer` with stations as its
   points.

   *group* is a list of dictionaries; each dictionary is an Enhydris
   time series; it has keys *base_url*, *user*, *password*, and *id*.
   Each time series refers to a station.  This function retrieves the
   co-ordinates of each station from Enhydris (unless we have them
   cached) and creates a layer in the specified ogr *data_source*
   whose features are points; as many points as there are
   stations/timeseries; each point is also given a *timeseries_id*
   attribute.

.. function:: update_timeseries_cache(cache_dir, groups)

   Downloads the newer part of time series from Enhydris.

   We keep some time series in our cache, which we download from
   Enhydris using the Enhydris web service API. This function
   downloads the part that has not already been downloaded (or all the
   timeseries if nothing is in the cache). *groups* is a dictionary;
   each item is a list of dictionaries, each one representing an
   Enhydris time series; its keys are *base_url*, *user*, *password*,
   *id*.
