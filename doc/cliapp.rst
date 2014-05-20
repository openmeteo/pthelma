.. _cliapp:

:mod:`cliapp` --- Framework for command-line applications
=========================================================

.. module:: cliapp
   :synopsis: Framework for command-line applications
.. moduleauthor:: Antonis Christofides <anthony@itia.ntua.gr>
.. sectionauthor:: Antonis Christofides <anthony@itia.ntua.gr>

.. class:: CliApp

   :class:`CliApp` is an abstract class that must be subclassed in
   order to create a command line application. It contains some
   functionality common in pthelma's command line applications. At a
   minimum, a subclass must define the :attr:`name` and
   :attr:`description` properties and the :meth:`execute()` method;
   usually it will also define the :attr:`config_file_options` and
   :attr:`cmdline_arguments` properties, and it may extend the
   :meth:`read_configuration()` and :meth:`check_configuration()`
   methods.

   A minimal example of a command line application is thus this::

      from pthelma.cliapp import CliApp


      class MyApp(CliApp):
          name = 'myapp'
          description = 'Do something extremely important'

          def execute(self):
              do_something()


      if __name__ == '__main__':
          myapp = MyApp()
          myapp.run()

   whereas a more complicated example would be roughly like this::

      from pthelma.cliapp import CliApp


      class MyApp(CliApp):
          name = 'myapp'
          description = 'Do something extremely important'
                                 # Section    Option    Default
          config_file_options = {'General': {'option1': None,
                                             'option2': 18,
                                             },
                                 'other':   {'option1': 'hello, world!',
                                             'option2': None,
                                             },
                                 }
          cmdline_arguments = {
              '--explode': {'action': 'store_true',
                            'help': 'Explode the system'},
              '--explode-delay': {'action': 'store',
                                  'help': 'Delay in seconds before exploding',
                                 },
          }

          def read_configuration(self):
              super(MyApp, self).read_configuration()
              self.do_some_more_things_with_the_configuration()

          def check_configuration(self):
              super(MyApp, self).check_configuration()
              self.check_more_things()


      if __name__ == '__main__':
          myapp = MyApp()
          myapp.run()

   .. attribute:: name
                  description

      These two class attributes are informational and will be used in
      error, log and help messages.

   .. attribute:: config_file_options

      A dictionary of configuration file options. Each key is a
      section, and each value is a dictionary of options and their
      defaults; :const:`None` as a default means that the option is
      compulsory. :samp:`config_file_options['other']` does not refer
      to a configuration file section "other", but to any
      configuration file section appart from those listed in
      :attr:`config_file_options`.

      :class:`CliApp` already contains some base configuration file
      options in section *General*: :confval:`logfile` (default empty
      string, meaning log to standard output), and :confval:`loglevel`
      (default warning).  In order to log messages to the logging
      system, use `self.logger`, which is a :class:`logging.Logger`
      object.

      In the :attr:`config_file_options` dictionary, a key's value can
      be the string :const:`'nocheck'` instead of a dictionary; this
      signals to not check the contents of that section for validity.

   .. attribute:: cmdline_arguments

      A dictionary the keys of which are command line arguments and the
      values are a dictionary of arguments to provide to
      :meth:`argparse.ArgumentParser.add_argument`.

   .. attribute:: config

      At the start of execution, we read the configuration file (which
      is in INI format), and we store the results in :attr:`config`,
      which is a dictionary similar to Python 3's
      :class:`configparser.ConfigParser`. This attribute is meant to be
      read-only.

   .. method:: read_configuration()

      Usually you won't need to override this method; however, if you
      want to transfer data from :attr:`config` to a data structure
      that is more convenient, you would do so here, after calling the
      inherited method.

   .. method:: check_configuration()

      Override this method; call the inherited (which checks for the
      existence of compulsory options and everything else it can
      check), then make checks to see if the values of the options
      specified are appropriate; raise :exc:`WrongValueError` when not.

   .. method:: execute()

      You must specify this method. This does all the work. It is
      called after the command line and configuration file are read and
      checked and after the logging system is setup and an
      informational message for program start is logged.

   .. method:: run(dry=False)

      You should not redefine this method, but call it in your main
      program.

      If the optional *dry* argument is :const:`True`, then
      :meth:`run()` does not run :meth:`execute()`; it only does
      everything else. (This is mainly useful in unit tests, to see if
      configuration reading and checking works properly).

.. exception:: InvalidOptionError
               WrongValueError

   These two exceptions derive from :class:`configparser.Error`.
   :exc:`InvalidOptionError` is raised whenever the configuration file
   contains an invalid option, and :exc:`WrongValueError` whenever an
   option contains an invalid value.
