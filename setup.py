#!/usr/bin/python

from setuptools import setup, find_packages

setup(
    name = "pthelma",
    version = "0.1",
    license = "GPL3",
    description = "Hydro/meteorological-related library, including timeseries",
    author = "Antonis Christofides",
    author_email = "anthony@itia.ntua.gr",
    packages = find_packages(),
    test_suite = "tests"
)
