#!/usr/bin/env python

import atexit
from ctypes import CDLL, c_char_p
import os
import platform
import shutil
import sys
import tempfile
import textwrap
import urllib2
from zipfile import ZipFile

from setuptools import setup, find_packages
from pkg_resources import parse_version


REQUIRED_DICKINSON_VERSION = '0.2.0'


def add_dir_to_zipfile(zipfile, dir, zipdir):
    """Recursively adds all files of dir in the zipfile, modifying their
    location by replacing dir with zipdir."""
    for dirpath, dirnames, filenames in os.walk(dir):
        assert(dirpath.startswith(dir))
        zippath = dirpath.replace(dir, zipdir, 1)
        for f in filenames:
            zipfile.write(os.path.join(dirpath, f), os.path.join(zippath, f))


class VersionError(Exception):
    pass


try:
    dickinson = CDLL('dickinson.dll'
                     if platform.system() == 'Windows'
                     else 'libdickinson.so')
    dickinson_version = c_char_p.in_dll(dickinson, 'dickinson_version'
                                        ).value.decode('ascii')
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


kwargs = {
    'name': "pthelma",
    'version': "0.7.3",
    'license': "GPL3",
    'description': "Hydro/meteorological timeseries library",
    'author': "Antonis Christofides",
    'author_email': "anthony@itia.ntua.gr",
    'packages': find_packages(),
    'scripts': ['bin/loggertodb'],
    'test_suite': "tests",
    'install_requires': [
        "pytz",
    ],
}

try:
    # Py2exe stuff; ignored if not in Windows or if py2exe is not installed

    import py2exe
    py2exe  # Does nothing, but lint checkers won't warn about unused py2exe

    # Download and save MSVC++ 2008 redistributable in a temporary directory
    # that will be removed when the program exits
    response = urllib2.urlopen('http://download.microsoft.com/download/'
                               '1/1/1/1116b75a-9ec3-481a-a3c8-1777b5381140/'
                               'vcredist_x86.exe')
    tmpdir = tempfile.mkdtemp()
    atexit.register(lambda: shutil.rmtree(tmpdir, ignore_errors=True))
    vcredist_filename = os.path.join(tmpdir, 'vcredist_x86.exe')
    with open(vcredist_filename, 'wb') as f:
        f.write(response.read())

    # Add the MSVC++ 2008 redistributable and dickinson to the produced files
    kwargs['data_files'] = [('', [r'\Windows\System32\dickinson.dll',
                                  vcredist_filename])]

    # Specify program executable
    kwargs['console'] = ['bin/loggertodb']
except ImportError:
    pass

setup(**kwargs)


if len(sys.argv) >= 2 and sys.argv[1] == 'py2exe':
    # Add pytz zoneinfo to library.zip
    import pytz
    zoneinfo_dir = os.path.join(os.path.dirname(pytz.__file__), 'zoneinfo')
    with ZipFile(os.path.join('dist', 'library.zip'), 'a') as z:
        add_dir_to_zipfile(z, zoneinfo_dir, os.path.join('pytz', 'zoneinfo'))
