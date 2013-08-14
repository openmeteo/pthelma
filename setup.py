#!/usr/bin/env python

from setuptools import setup, find_packages

setup(
    name = "pthelma",
    version = "0.1.0",
    license = "GPL3",
    description = "Hydro/meteorological-related library, including timeseries",
    author = "Antonis Christofides",
    author_email = "anthony@itia.ntua.gr",
    packages = find_packages(),
    scripts = ['bin/loggertodb'],
    test_suite = "tests"
)
