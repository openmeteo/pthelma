#!/usr/bin/env python

from ctypes import CDLL, c_char_p
import platform
import sys
import textwrap

from setuptools import setup, find_packages
from pkg_resources import parse_version


REQUIRED_DICKINSON_VERSION = '0.1.0'


class VersionError(Exception):
    pass


try:
    dickinson = CDLL('dickinson.dll'
                     if platform.system() == 'Windows'
                     else 'libdickinson.so')
    dickinson_version = c_char_p.in_dll(dickinson, 'dickinson_version').value
    if dickinson_version != 'dev' and parse_version(dickinson_version) \
            < parse_version(REQUIRED_DICKINSON_VERSION):
        raise VersionError('Too old version of dickinson: {0}'.format(
                           dickinson_version))
except OSError as e:
    sys.stderr.write(str(e) + '\n')
    sys.stderr.write(textwrap.dedent('''
        Please make sure you have installed dickinson
        (see http://dickinson.readthedocs.org/).
        '''))
    sys.exit(1)
except ValueError as e:
    sys.stderr.write(str(e) + '\n')
    sys.stderr.write(textwrap.dedent('''
        Apparently the version of dickinson that is installed doesn't export
        a dickinson_version variable. Maybe it's too old. Please install at
        least version {0} (see http://dickinson.readthedocs.org/).
        '''.format(REQUIRED_DICKINSON_VERSION)))
    sys.exit(1)
except VersionError as e:
    sys.stderr.write(str(e) + '\n')
    sys.stderr.write(textwrap.dedent('''
        Please install at least version {0} of dickinson
        (see http://dickinson.readthedocs.org/)
        '''.format(REQUIRED_DICKINSON_VERSION)))
    sys.exit(1)


setup(
    name="pthelma",
    version="0.4.1",
    license="GPL3",
    description="Hydro/meteorological-related library, including timeseries",
    author="Antonis Christofides",
    author_email="anthony@itia.ntua.gr",
    packages=find_packages(),
    scripts=['bin/loggertodb'],
    test_suite="tests",
    install_requires=[
        "pytz",
    ]
)
