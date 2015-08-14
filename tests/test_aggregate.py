from copy import copy
import os
import shutil
from six.moves import configparser
import sys
import tempfile
import textwrap
from unittest import TestCase

from pthelma.cliapp import WrongValueError
from pthelma.aggregate import AggregateApp
from pthelma.timeseries import Timeseries


class AggregateAppTestCase(TestCase):

    def __init__(self, *args, **kwargs):
        super(AggregateAppTestCase, self).__init__(*args, **kwargs)

        # Python 2.7 compatibility
        try:
            self.assertRaisesRegex
        except AttributeError:
            self.assertRaisesRegex = self.assertRaisesRegexp

    def setUp(self):
        self.tempdir = tempfile.mkdtemp()
        self.config_file = os.path.join(self.tempdir, 'aggregate.conf')
        self.saved_argv = copy(sys.argv)
        sys.argv = ['aggregate', '--traceback', self.config_file]
        self.savedcwd = os.getcwd()

        # Create two time series
        self.filenames = [os.path.join(self.tempdir, x)
                          for x in ('ts1', 'ts2')]
        self.output_filenames = [x + 'a' for x in self.filenames]
        with open(self.filenames[0], 'w') as f:
            f.write("Location=23.78743 37.97385 4326\n"
                    "Time_step=10,0\n"
                    "Timestamp_rounding=0,0\n"
                    "Timestamp_offset=0,0\n"
                    "Timezone=EET (UTC+0200)\n"
                    "\n"
                    "2014-06-16 14:50,14.1,\n"
                    "2014-06-16 15:00,15.0,\n"
                    "2014-06-16 15:10,16.9,\n"
                    "2014-06-16 15:20,17.8,\n"
                    "2014-06-16 15:30,18.7,\n"
                    "2014-06-16 15:40,19.6,\n"
                    "2014-06-16 15:50,20.5,\n"
                    "2014-06-16 16:00,21.4,\n"
                    "2014-06-16 16:10,22.3,\n"
                    )
        with open(self.filenames[1], 'w') as f:
            f.write("Location=24.56789 38.76543 4326\n"
                    "Time_step=10,0\n"
                    "Timestamp_rounding=0,0\n"
                    "Timestamp_offset=0,0\n"
                    "\n"
                    "2014-06-17 14:50,94.1,\n"
                    "2014-06-17 15:00,85.0,\n"
                    "2014-06-17 15:10,76.9,\n"
                    "2014-06-17 15:20,67.8,\n"
                    "2014-06-17 15:30,58.7,\n"
                    "2014-06-17 15:40,49.6,\n"
                    "2014-06-17 15:50,30.5,\n"
                    "2014-06-17 16:00,21.4,\n"
                    "2014-06-17 16:10,12.3,\n"
                    )

        # Prepare a configuration file (some tests override it)
        with open(self.config_file, 'w') as f:
            f.write(textwrap.dedent('''\
                [General]
                base_dir = {self.tempdir}
                target_step = 60, 0

                [timeseries1]
                source_file = ts1
                target_file = ts1a
                interval_type = sum

                [timeseries2]
                source_file = ts2
                target_file = ts2a
                interval_type = average
                ''').format(self=self))

    def tearDown(self):
        os.chdir(self.savedcwd)
        shutil.rmtree(self.tempdir)
        sys.argv = copy(self.saved_argv)

    def test_correct_configuration(self):
        application = AggregateApp()
        application.run(dry=True)

    def test_wrong_configuration(self):
        with open(self.config_file, 'w') as f:
            f.write(textwrap.dedent('''\
                [General]
                base_dir = mydir
                '''))
        application = AggregateApp()
        self.assertRaisesRegex(configparser.Error, 'target_step',
                               application.run)

        with open(self.config_file, 'w') as f:
            f.write(textwrap.dedent('''\
                [General]
                base_dir = mydir
                target_step = 60, 0
                nonexistent_option = irrelevant
                '''))
        application = AggregateApp()
        self.assertRaisesRegex(configparser.Error, 'nonexistent_option',
                               application.run)

        with open(self.config_file, 'w') as f:
            f.write(textwrap.dedent('''\
                [General]
                base_dir = mydir
                target_step = 60, 80
                '''))
        application = AggregateApp()
        self.assertRaisesRegex(WrongValueError, 'appropriate time step',
                               application.run)

    def test_execute(self):
        application = AggregateApp()
        application.read_command_line()
        application.read_configuration()

        # Verify the output files don't exist yet
        self.assertFalse(os.path.exists(self.output_filenames[0]))
        self.assertFalse(os.path.exists(self.output_filenames[1]))

        # Execute
        application.run()

        # Check that it has created two files
        self.assertTrue(os.path.exists(self.output_filenames[0]))
        self.assertTrue(os.path.exists(self.output_filenames[1]))

        # Check that the created time series are correct
        t = Timeseries()
        with open(self.output_filenames[0]) as f:
            t.read_file(f)
        self.assertEqual(t.timezone, 'EET (UTC+0200)')
        self.assertEqual(len(t), 1)
        self.assertAlmostEqual(t['2014-06-16 16:00'], 114.9, places=5)
        t = Timeseries()
        with open(self.output_filenames[1]) as f:
            t.read_file(f)
        self.assertEqual(t.timezone, '')
        self.assertEqual(len(t), 1)
        self.assertAlmostEqual(t['2014-06-17 16:00'], 50.8167, places=5)

    def test_execute_error_message(self):
        application = AggregateApp()
        application.read_command_line()
        application.read_configuration()

        # Create a file that doesn't have timestamp rounding
        with open(self.filenames[0], 'w') as f:
            f.write("Location=23.78743 37.97385 4326\n"
                    "Time_step=10,0\n"
                    "Timestamp_offset=0,0\n"
                    "\n"
                    "2014-06-16 14:50,14.1,\n"
                    )

        # Execute
        try:
            application.run()
            self.assertTrue(False)
        except Exception as e:
            # Make sure the file name is included in the message
            self.assertTrue(self.filenames[0] in str(e))
