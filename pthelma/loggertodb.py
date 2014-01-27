#!/usr/bin/env python
"""
loggertodb - insert automatic meteorological station data to the database

Copyright (C) 2005-2007 National Technical University of Athens
Copyright (C) 2005 Antonios Christofides

This program is free software; you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation; either version 2 of the License, or
(at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.
"""

import sys
from datetime import datetime
from ConfigParser import RawConfigParser
import logging
from urllib2 import build_opener, HTTPCookieProcessor
import cookielib
import traceback

from pthelma import meteologger
from pthelma.meteologger import ConfigurationError


def check_configuration(config):
    required_options = ['base_url', 'user', 'password']
    optional_options = ['loglevel', 'logfile']
    all_options = required_options + optional_options
    for option in required_options:
        if not config.has_option('General', option):
            raise ConfigurationError('Option "{}" is required'.format(option))
    for option in config.options('General'):
        if option not in all_options:
            raise ConfigurationError('Unknown option "{}"'.format(option))
    warning_levels = ['ERROR', 'WARNING', 'INFO', 'DEBUG']
    if config.has_option('General', 'loglevel'):
        if config.get('General', 'loglevel') not in warning_levels:
            raise ConfigurationError('loglevel must be one of {}'.format(
                ', '.join(warning_levels)))


def read_configuration(config_file):
    defaults = (('General', 'loglevel', 'WARNING'),
                )
    config = RawConfigParser()
    config.read((config_file,))
    for d in defaults:
        if not config.has_option(d[0], d[1]):
            config.set(d[0], d[1], d[2])
    config.base_url = config.get('General', 'base_url')
    if not config.base_url.endswith('/'):
        config.base_url += '/'
    return config


def setup_logger(config):
    logger = logging.getLogger('loggertodb')
    logger.setLevel(logging.__dict__[config.get('General', 'loglevel')])
    if config.has_option('General', 'logfile'):
        logger.addHandler(logging.FileHandler(config.get('General',
                                                         'logfile')))
    else:
        logger.addHandler(logging.StreamHandler())
    return logger


def login_to_enhydris(config):
    cookiejar = cookielib.CookieJar()
    opener = build_opener(HTTPCookieProcessor(cookiejar))
    login_url = config.base_url + 'accounts/login/'
    opener.open(login_url)
    opener.addheaders = [('X-CSRFToken', cookie.value)
                         for cookie in cookiejar if cookie.name == 'csrftoken'
                         ] + [('Referer', login_url)]
    data = 'username={0}&password={1}'.format(
        config.get('General', 'user'), config.get('General', 'password'))
    opener.open(login_url, data)
    opener.addheaders = [('X-CSRFToken', cookie.value)
                         for cookie in cookiejar if cookie.name == 'csrftoken'
                         ]
    return opener


def execute():
    logger = None
    config = None
    try:
        if len(sys.argv) != 2:
            raise RuntimeError('usage: %s configfile' % (sys.argv[0]))
        config = read_configuration(sys.argv[1])
        logger = setup_logger(config)
        logger.info('Starting loggertodb, %s' % (datetime.today().isoformat()))
        opener = login_to_enhydris(config)
        sections = config.sections()[:]
        sections.remove('General')
        for section in sections:
            datafileclass = eval('meteologger.Datafile_%s' %
                                (config.get(section, 'datafile_format'),))
            adatafile = datafileclass(config.base_url, opener,
                                      dict(config.items(section)), logger)
            try:
                adatafile.update_database()
            except meteologger.MeteologgerError, e:
                msg = 'Error while processing item {0}: {1}'.format(section,
                                                                    str(e))
                sys.stderr.write(msg + '\n')
                logger.error(msg)
                logger.debug(traceback.format_exc())
    except Exception as e:
        msg = str(e)
        sys.stderr.write(msg + '\n')
        if logger:
            logger.error(msg)
        if config and config.get('General', 'loglevel') == 'DEBUG':
            raise
        sys.exit(1)
    finally:
        if logger:
            logger.info('Loggertodb finished, {}'.format(
                datetime.today().isoformat()))
