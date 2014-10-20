.. _spatial:

:mod:`spatial` --- Utilities for spatial integration
====================================================

.. module:: spatial
   :synopsis: Utilities for spatial integration.
.. moduleauthor:: Antonis Christofides <anthony@itia.ntua.gr>
.. sectionauthor:: Antonis Christofides <anthony@itia.ntua.gr>

.. function:: idw(point, data_layer, alpha=1)

   Uses the inverse distance weighting method to calculate the value
   for a single point.

   *data_layer* is an :class:`ogr.Layer` object containing one or more
   points with values (all data_layer features must be points and must
   also have a *value* attribute, which may, however, have the value
   :const:`NaN`).  *point* is an :class:`ogr.Point` object.  This
   function applies the IDW method to calculate the value of *point*
   given the values of the points of *data_layer*. Points with a value
   of :const:`NaN` are not taken into account in the calculations.

   Distances are raised to power -*alpha*; this means that for *alpha*
   > 1, the so-called distance-decay effect will be more than
   proportional to an increase in distance, and vice-versa.

.. function:: integrate(mask, data_layer, target_band, funct, kwargs={})

   Performs integration on an entire surface.

   *mask* is a gdal dataset whose first band is the mask; the
   gridpoints of the mask have value zero or non-zero. *data_layer* is
   an :class:`ogr.Layer` object containing one or more points with
   values (all *data_layer* features must be points and must also have
   a *value* attribute, which may, however, have the value
   :const:`NaN`). *target_band* is a band on which the result will be
   written; it must have the same GeoTransform as *mask*, and these
   two must be in the same co-ordinate reference system as
   *data_layer*. *funct* is a python function whose first two
   arguments are an :class:`ogr.Point` and *data_layer*, and *kwargs*
   is a dictionary with keyword arguments to be given to *funct*.

   This function calls *funct* for each non-zero gridpoint of the
   mask.

   NOTE: It is assumed that there is no x_rotation and y_rotation
   (i.e. that :samp:`mask.GetGeoTransform()[3]` and :samp:`[4]` are
   zero).

.. function:: create_ogr_layer_from_timeseries(filenames, epsg, data_source)

   Creates and returns an :class:`ogr.Layer` with stations as its
   points.

   *filenames* is a sequence of filenames; each file must be a
   timeseries in :ref:`file format <fileformat>` that includes the
   Location header.  This function transform the co-ordinates so that
   they are in the reference system specified by *epsg* (an integer),
   and creates a layer in the specified ogr *data_source* whose
   features are points; as many points as there are
   stations/timeseries; each point is also given a *filename*
   attribute.

.. function:: h_integrate(mask, stations_layer, date, output_filename_prefix, date_fmt, funct, kwargs)

   Given an area mask and a layer with stations, performs spatial
   integration and writes the result to a GeoTIFF file. The *h* in the
   name signifies that this is a high level function, in contrast to
   :func:`integrate()`, which does the actual job.

   *mask* is a raster with the area of study, in the form accepted by
   :func:`integrate()`.  *stations_layer* is an :class:`ogr.Layer`
   object like the one returned by
   :func:`create_ogr_layer_from_timeseries()`; *mask* and
   *stations_layer* must be in the same co-ordinate reference system.
   *date* is a :class:`~datetime.datetime` object specifying the date
   and time for which we are to perform integration.  The filename of
   the resulting file has the form
   :samp:`{output_filename_prefix}-{d}.tif`, where *d* is the *date*
   formatted by :func:`datetime.strftime()` with the format
   *date_fmt*; however, if *date_fmt* contains spaces or colons, they
   are converted to hyphens. If the file already exists, the function
   returns immediately without doing anything. *funct* and *kwargs*
   are passed to :func:`integrate()`.

   If some of the time series referenced in *stations_layer* don't
   have *date*, they are not taken into account in the integration. If
   no time series has *date*, the function does nothing.

.. class:: BitiaApp

   This class contains the :doc:`../user/bitia` command-line
   application. The :file:`bitia` executable does little other than
   this::

      application = BitiaApp()
      application.run()
