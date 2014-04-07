"""
In order to run these tests, you must specify the
PTHELMA_TEST_ENHYDRIS_API variable to contain a json-formatted string
of parameters, like this:

    { "base_url": "http://localhost:8001/",
      "username": "admin",
      "password": "topsecret",
    }

Note that some other testing modules may also use
PTHELMA_TEST_ENHYDRIS_API, but might require additional parameters.

Don't use a production database for that; some testing functionality
may write to the database. Although things are normally cleaned up
(e.g. test timeseries created are deleted), id serial numbers will be
affected and things might not be cleaned up if there is an error.
"""

import json
import os
from unittest import TestCase, skipUnless

import requests

from pthelma import enhydris_api


@skipUnless(os.getenv('PTHELMA_TEST_ENHYDRIS_API'),
            'set PTHELMA_TEST_ENHYDRIS_API')
class LoginTestCase(TestCase):

    def test_login(self):
        v = json.loads(os.getenv('PTHELMA_TEST_ENHYDRIS_API'))
        base_url, user, password = v['base_url'], v['username'], v['password']
        if base_url[-1] != '/':
            base_url += '/'

        # Verify we are logged out
        r = requests.get(base_url)
        self.assertEquals(r.status_code, 200)
        self.assertTrue('Login' in r.text)
        self.assertFalse('Logout' in r.text)

        # Now login and verify we're logged on
        cookies = enhydris_api.login(base_url, user, password)
        r = requests.get(base_url, cookies=cookies)
        self.assertEquals(r.status_code, 200)
        self.assertFalse('Login' in r.text)
        self.assertTrue('Logout' in r.text)
