#!/usr/bin/env python

import atexit
from compileall import compile_file
from ctypes import CDLL, c_char_p
import os
import platform
import shutil
import sys
import tempfile
import textwrap
try:
    # Python 3
    from urllib.request import urlopen
except ImportError:
    # Python 2
    from urllib2 import urlopen
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
    dickinson = CDLL(
        (platform.system() == 'Windows' and 'dickinson.dll') or
        (platform.system().startswith('Darwin') and 'libdickinson.dylib') or
        'libdickinson.so')
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


installation_requirements = ["pytz",
                             "simpletail>=0.1.1",
                             "requests>=1,<3",
                             "six>=1.9,<2",
                             "iso8601",
                             "affine",
                             ]
if sys.platform != 'win32':
    installation_requirements.extend(["numpy>=1.5,<2",
                                      "gdal>=1.9,<2",
                                      ])
else:
    installation_requirements.extend(["pyodbc>=3,<4",
                                      ])

kwargs = {
    'name': "pthelma",
    'version': "0.13.0",
    'license': "GPL3",
    'description': "Hydro/meteorological timeseries library",
    'author': "Antonis Christofides",
    'author_email': "anthony@itia.ntua.gr",
    'packages': find_packages(),
    'scripts': ['bin/loggertodb', 'bin/spatialize', 'bin/enhydris_cache',
                'bin/aggregate', 'bin/vaporize'],
    'test_suite': "tests",
    'install_requires': installation_requirements,
    'options': {'py2exe': {'includes': ['pyodbc',

                                        # The following two are required by
                                        # pyodbc but might not be found by
                                        # py2exe, which doesn't look in C++
                                        # files.
                                        'decimal',
                                        'datetime',

                                        # ConfigParser is not automatically
                                        # found by py2exe when imported as
                                        # six.moves.configparser.
                                        'ConfigParser',
                                        ],
                           'excludes': ['spatial']}},
}

if len(sys.argv) >= 2 and sys.argv[1] == 'py2exe':
    import py2exe
    import requests
    py2exe  # Does nothing, but lint checkers won't warn about unused py2exe

    # Download and save MSVC++ 2008 redistributable in a temporary directory
    # that will be removed when the program exits
    response = urlopen('http://download.microsoft.com/download/'
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
    kwargs['console'] = ['bin/loggertodb', 'bin/enhydris_cache',
                         'bin/aggregate']

    # python-requests' cacert.pem.
    # First, we need to add cacert.pem to the bundle. That's the easy part.
    # However, requests.certs looks for cacert.pem in the directory from which
    # requests.certs has been loaded (i.e.
    # os.path.dirname(requests.certs.__file__). This is probably wrong; it
    # should be using pkg_resources to load it. The problem is that py2exe puts
    # requests in library.zip, so attempting to read stuff from the above
    # directory won't work.  So, instead, we add cacert.pem to the bundle,
    # deploy it alongside library.zip, and modify requests/certs.py at bundle
    # creation time so that, when deployed, it will read certs.py from the
    # bundle location.
    cacert_filename = os.path.join(os.path.dirname(requests.__file__),
                                   'cacert.pem')
    kwargs['data_files'][0][1].append(cacert_filename)
    certs_path = os.path.join(
        os.path.dirname(requests.__file__),
        'certs.py')  # We can't use requests.certs.__file__; it may be the .pyc
    try:
        os.remove(certs_path + '.bak')
    except:
        pass
    os.rename(certs_path, certs_path + '.bak')

    def restore_certs():
        os.remove(certs_path)
        os.rename(certs_path + '.bak', certs_path)
        compile_file(certs_path, force=True)

    atexit.register(restore_certs)
    with open(certs_path, 'w') as f:
        f.write(textwrap.dedent("""\
            import os
            import sys

            def where():
                # This is not the function packaged by python-requests, but
                # a patch made by py2exe setup. If you are looking at the code
                # bundled by py2exe (unlikely, since it normally doesn't
                # include the source), this is normal. If, however, you are
                # looking at the python-requests code installed on the system
                # where you run py2exe, it is likely that something went wrong
                # and py2exe failed to revert this file to the original, as it
                # should have done after creating the bundle. You should delete
                # and re-install python-requests. See pthelma's setup.py for
                # more information.
                return os.path.join(os.path.dirname(sys.executable),
                                    'cacert.pem')
            """))
    compile_file(certs_path, force=True)

setup(**kwargs)


if len(sys.argv) >= 2 and sys.argv[1] == 'py2exe':
    # Add pytz zoneinfo to library.zip
    import pytz
    zoneinfo_dir = os.path.join(os.path.dirname(pytz.__file__), 'zoneinfo')
    with ZipFile(os.path.join('dist', 'library.zip'), 'a') as z:
        add_dir_to_zipfile(z, zoneinfo_dir, os.path.join('pytz', 'zoneinfo'))
