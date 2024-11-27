.. _testutils:

=======================
hspatial test utilities
=======================

``from hspatial.test import setup_test_raster``


.. function:: hspatial.test.setup_test_raster(filename, value, timestamp=None, srid=4326)

   Creates a 3x3 raster file for use in unit tests.

   *filename* is the filename of the raster that will be created, e.g.
   ``os.path.join(self.tempdir, "myraster.tif")``.

   *value* is a 3x3 numpy array with the values of the raster, e.g.
   ``np.array([[1.1, nan, 1.3], [2.1, 2.2, nan], [3.1, 3.2, 3.3]])``.

   If *timestamp* is specified, it must be a ``datetime`` object. In
   that case, the ``TIMESTAMP`` attribute is set as metadata in the
   file.

   *srid* can be 4326 or 2100. If it is 4326, the top left corner has
   latitude 22.0, longitude 38.0, and the step is 0.01 degree (so the
   lower right corner has latitude 22.02, 37.98). If it is 2100, the
   top left corner has coordinates (320,000, 4,210,000) and the step is
   1000 meters, so the lower right corner is (322,000, 4,208,000).
