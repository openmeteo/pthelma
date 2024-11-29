============
Installation
============

::

    pip install pthelma[all]

The above will install ``pthelma`` with all its dependencies. Some of
the dependencies, however, may be hard to install, namely ``gdal``. If
you don't need the spatial features of ``pthelma`` (such as
``hspatial``), use the following, which will install all dependencies
except for ``gdal``::

    pip install pthelma
