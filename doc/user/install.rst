.. _install:

============
Installation
============

.. highlight:: bash

loggertodb, enhydris_cache, and aggregate on Windows
====================================================

Download and execute the Windows executable installer
(``pthelma-X.Y.Z-setup.exe``) from
https://github.com/openmeteo/pthelma/releases/ (not all ``pthelma``
releases include a Windows installer; select the latest that does).

Linux
=====

First, you need to install Dickinson_. Then, install ``pthelma`` with
pip::

    pip install pthelma

or clone it with ``git``::

    git clone https://github.com/openmeteo/pthelma.git

Generic way to install on Windows
=================================

Manually installing on Windows has some difficulties, the main reason
being that some dependencies, namely ``numpy`` and especially
``gdal``, need compilation and are not trivial to compile. We
therefore use OSGeo4W_, which has Python, ``numpy`` and ``gdal``
preinstalled. The procedure is this:

1. Install OSGeo4W_.

2. Open the ``OSGeo4W`` shell (this is a command prompt for which the
   environment has been tweaked; unfortunately it does not seem easy to
   continue with (git/)bash; it has to be the ``OSGeo4W`` shell).

3. ``easy_install pthelma`` (if this doesn't work, it may be that
   another Python installation is interfering; make sure the ``PATH``
   doesn't include the directory of another Python installation.)

That should do it. An alternative is to clone ``pthelma`` and install
its dependencies instead (search for ``install_requires`` in
``setup.py``), except for ``numpy`` and ``gdal``.

Also note that creating an installer with ``py2exe`` or similar is
difficult because of OSGeo4W_; therefore we only make an installer for
the applications that do not have OSGeo4W_ dependencies.

.. _dickinson: http://dickinson.readthedocs.org/
.. _osgeo4w: http://trac.osgeo.org/osgeo4w/
