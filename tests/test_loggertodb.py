from ConfigParser import RawConfigParser
from StringIO import StringIO
import textwrap
from unittest import TestCase

from pthelma.loggertodb import check_configuration
from pthelma.meteologger import ConfigurationError


class LoggertodbTestCase(TestCase):

    def test_check_configuration(self):
        cp = RawConfigParser()
        cp.readfp(StringIO(textwrap.dedent('''\
            [General]
            user = a_user
            password = a_password
            ''')))
        self.assertRaises(ConfigurationError, check_configuration, cp)

        cp = RawConfigParser()
        cp.readfp(StringIO(textwrap.dedent('''\
            [General]
            base_url = a_base_url
            user = a_user
            password = a_password
            nonexistent_option = an_option
            ''')))
        self.assertRaises(ConfigurationError, check_configuration, cp)

        cp = RawConfigParser()
        cp.readfp(StringIO(textwrap.dedent('''\
            [General]
            base_url = a_base_url
            user = a_user
            password = a_password
            loglevel = NONEXISTENT_LOG_LEVEL
            ''')))
        self.assertRaises(ConfigurationError, check_configuration, cp)

        # Call it correctly and expect it doesn't raise anything
        cp = RawConfigParser()
        cp.readfp(StringIO(textwrap.dedent('''\
            [General]
            base_url = a_base_url
            user = a_user
            password = a_password
            ''')))
        check_configuration(cp)

        # Again, with different options
        cp = RawConfigParser()
        cp.readfp(StringIO(textwrap.dedent('''\
            [General]
            base_url = a_base_url
            user = a_user
            password = a_password
            loglevel = ERROR
            ''')))
        check_configuration(cp)
