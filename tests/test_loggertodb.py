import textwrap
from unittest import TestCase

from six import StringIO
from six.moves.configparser import RawConfigParser

from pthelma.loggertodb import check_configuration
from pthelma.meteologger import ConfigurationError


class LoggertodbTestCase(TestCase):

    def _create_config_parser(self):
        result = RawConfigParser()

        # Python 2 compatibility
        if not getattr(result, 'read_file', None):
            result.read_file = result.readfp

        return result

    def test_check_configuration(self):
        cp = self._create_config_parser()

        cp.read_file(StringIO(textwrap.dedent('''\
            [General]
            user = a_user
            password = a_password
            ''')))
        self.assertRaises(ConfigurationError, check_configuration, cp)

        cp = self._create_config_parser()
        cp.read_file(StringIO(textwrap.dedent('''\
            [General]
            base_url = a_base_url
            user = a_user
            password = a_password
            nonexistent_option = an_option
            ''')))
        self.assertRaises(ConfigurationError, check_configuration, cp)

        cp = self._create_config_parser()
        cp.read_file(StringIO(textwrap.dedent('''\
            [General]
            base_url = a_base_url
            user = a_user
            password = a_password
            loglevel = NONEXISTENT_LOG_LEVEL
            ''')))
        self.assertRaises(ConfigurationError, check_configuration, cp)

        # Call it correctly and expect it doesn't raise anything
        cp = self._create_config_parser()
        cp.read_file(StringIO(textwrap.dedent('''\
            [General]
            base_url = a_base_url
            user = a_user
            password = a_password
            ''')))
        check_configuration(cp)

        # Again, with different options
        cp = self._create_config_parser()
        cp.read_file(StringIO(textwrap.dedent('''\
            [General]
            base_url = a_base_url
            user = a_user
            password = a_password
            loglevel = ERROR
            ''')))
        check_configuration(cp)
