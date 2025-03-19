.. _hspatial_api:

==============
hspatial - API
==============

``import hspatial``


.. function:: hspatial.idw(point, data_layer, alpha=1)

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

.. function:: hspatial.integrate(mask, data_layer, target_band, funct, kwargs={})

   Performs integration on an entire surface.

   *mask* is a gdal dataset whose first band is the mask; the
   gridpoints of the mask have value zero or non-zero. *mask* can also be a
   :class:`django.contrib.gis.gdal.GDALRaster` object.

   *data_layer* is an :class:`ogr.Layer` object containing one or more points
   with values (all *data_layer* features must be points and must also have a
   *value* attribute, which may, however, have the value :const:`NaN`).

   *target_band* is a band on which the result will be written; it must have
   the same GeoTransform as *mask*, and these two must be in the same
   co-ordinate reference system as *data_layer*. *target_band* can be either a
   :class:`django.contrib.gis.gdal.GDALBand` object or a gdal band object.

   *funct* is a python function
   whose first two arguments are an :class:`ogr.Point` and *data_layer*, and
   *kwargs* is a dictionary with keyword arguments to be given to *funct*.

   This function calls *funct* for each non-zero gridpoint of the
   mask.

   NOTE: It is assumed that there is no x_rotation and y_rotation
   (i.e. that :samp:`mask.GetGeoTransform()[3]` and :samp:`[4]` are
   zero).

.. function:: hspatial.create_ogr_layer_from_timeseries(filenames, epsg, data_source)

   Creates and returns an :class:`ogr.Layer` with stations as its
   points.

   *filenames* is a sequence of filenames; each file must be a
   timeseries in `file format`_ that includes the ``Location`` header.
   This function transforms the co-ordinates so that they are in the
   reference system specified by *epsg* (an integer), and creates a
   layer in the specified ogr *data_source* whose features are points;
   as many points as there are stations/timeseries; each point is also
   given a *filename* attribute.

.. function:: hspatial.h_integrate(mask, stations_layer, date, output_filename_prefix, date_fmt, funct, kwargs)

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
   are converted to hyphens.  *funct* and *kwargs* are passed to
   :func:`integrate()`.

   If some of the time series referenced in *stations_layer* don't
   have *date*, they are not taken into account in the integration. If
   no time series has *date*, the function does nothing.

   The function stores in the output file a gdal metadata item that
   records the list of input files from which the output has been
   calculated. This can be the same as the list of files in
   *stations_layer*, but it can be less if some of these files do not
   include *date*. If the output file already exists, the function
   examines the recorded list and checks whether it has been
   calculated from all available data (occasionally more data becomes
   available between subsequent runs); if yes, the function returns
   without doing anything.

.. function:: hspatial.extract_point_from_raster(point, data_source, band_number=1)

   *data_source* is either a GDAL data source with a raster or a
   GeoDjango :class:`GDALRaster` object. *point* is either an OGR point,
   or a GeoDjango point object.  The function returns the value of the
   pixel of the specified band of *data_source* in which the *point*
   falls.

   *point* and *data_source* need not be in the same reference system,
   but they must both have an appropriate spatial reference defined.

   If the *point* does not fall in the raster, :exc:`RuntimeError` is
   raised.

.. class:: hspatial.PointTimeseries(point, filenames=None, prefix=None, date_fmt=None, start_date=None, end_date=None, default_time=dt.time(0, 0, tzinfo=dt.timezone.utc))

   A class that can extract a point timeseries from a set of rasters.

   The set of rasters is specified either with *filenames* or with
   *prefix*.  Exactly one of these must be ``None``. *filenames*, if
   specified, must be a sequence or set of names of raster files which
   should contain the same variable in different times; for example, the
   rasters can be representing spatial rainfall, each raster at a
   different time. If, instead, *prefix* is specified, the raster files
   are named :samp:`{prefix}-{timestamp}.tif`. In that case, the
   timestamp must be in the format specified by *date_fmt*. If
   *date_fmt* is ``None``, the format is either ``%Y-%m-%d`` or
   ``%Y-%m-%d-%H-%M``, whichever matches.

   However, when creating the time series, the timestamp is obtained
   from the ``TIMESTAMP`` GDAL metadata item of each raster, which must
   be in ISO 8601 format. The timestamp on the filename is only used
   when determining whether it's worth to open a file or not (e.g.
   because a start timestamp or end timestamp has been requested, or
   because it is being determined whether a cache is up-to-date).

   *point* is either an OGR point object or a GeoDjango point object. It
   need not be in the same reference system as the rasters; however, the
   rasters must contain spatial reference (projection) information, and so
   must *point*, so that it is converted if necessary.

   If *start_date* or *end_date* are specified, only that part of the
   time series is read from the rasters. This is only valid when the
   class has been initialized with a prefix (not with a list of
   filenames).

   If the ``TIMESTAMP`` GDAL metadata item of the raster does not
   contain a time, then *default_time* is assumed. *default_time* must
   be aware. If ``TIMESTAMP`` does contain a time, but not a time zone,
   then the time zone from *default_time* is used.

   .. method:: hspatial.PointTimeseries.get()

      Extracts and returns a HTimeseries_ object that corresponds to the
      values of the point in the rasters.

      Usage example::

         from glob import glob

         from osgeo import ogr, osr

         from hspatial import PointTimeseries

         point = ogr.Geometry(ogr.wkbPoint)

         # Specify that the point uses the WGS84 reference system
         sr = osr.SpatialReference()
         sr.ImportFromEPSG(4326)
         if int(gdal.__version__.split(".")[0]) > 2:
             sr.SetAxisMappingStrategy(osr.OAMS_TRADITIONAL_GIS_ORDER)
         point.AssignSpatialReference(sr)

         # Point's co-ordinates (in WGS84 it's latitude and longitude)
         point.AddPoint(23.78901, 37.98765)

         filenames = glob('/var/opt/hspatial/rainfall*.tif')

         ts = PointTimeseries(point, filenames=filenames).get()

   .. method:: hspatial.PointTimeseries.get_cached(dest, force=False, version=4)

      This is like :meth:`~hspatial.PointTimeseries.get`, but in addition
      to returning an object, it saves the time series to the file with
      filename *dest*, in `file format`_. It works only when the class
      has been initialized with a prefix (not with filenames).

      If the file does not already exist, or if *force* is ``True``, the
      time series is extracted from the rasters and written to the file,
      overwriting it if it existed.

      If the file already exists and *force* is ``False``, the time series
      file is overwritten only if it is not up to date. A time series file
      is considered to be up to date if it contains records for all the
      timestamps of the rasters and only those. Thus, the time series file
      is opened and read in order to compare its timestamps with the
      timestamps of the rasters.

      The time series is returned, whether it was extracted from the
      rasters or read from an up-to-date *dest*.

      The *version* parameter is passed to HTimeseries_'s .write()
      method.

.. function:: hspatial.coordinates2point(x, y, srid=4326)

   Returns an ogr.Geometry object of type point. If srid=4326, x is the
   longitude and y is the latitude.

.. _file format: https://github.com/openmeteo/htimeseries#file-format
.. _htimeseries: https://github.com/openmeteo/htimeseries
