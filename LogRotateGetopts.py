#!/usr/bin/env python
# -*- coding: utf-8 -*-

# $Id$
# $URL$

'''
@author: Frank Brehm
@contact: frank@brehm-online.com
@license: GPL3
@copyright: (c) 2010-2011 by Frank Brehm, Berlin
@version: 0.0.1
@summary: Option parser for Python logrotating
'''

import re
import sys

from optparse import OptionError
from optparse import OptionParser
from optparse import OptionGroup
from optparse import OptionConflictError


revision = '$Revision$'
revision = re.sub( r'\$', '', revision )
revision = re.sub( r'Revision: ', r'r', revision )
revision = re.sub( r'\s*$', '', revision )

__author__    = 'Frank Brehm'
__copyright__ = '(C) 2011 by Frank Brehm, Berlin'
__contact__    = 'frank@brehm-online.com'
__version__    = '0.0.1 ' + revision
__license__    = 'GPL3'


#========================================================================

class LogrotateOptParserError(Exception):
    '''
    Class for exceptions in this module, escpacially
    due to false commandline options.
    '''

#========================================================================

class LogrotateOptParser(object):
    '''
    Class for parsing commandline options of Python logrotating.

    @author: Frank Brehm
    @contact: frank@brehm-online.com
    '''

    #-------------------------------------------------------
    def __init__( self, prog = '%prog',
                        version = None,
    ):
        '''
        Costructor.
        @param prog: The name of the calling process (e.g. sys.argv[0])
        @type prog: str
        @param version: The version string to use
        @type version: str
        @return: None
        '''

        self.prog = prog
        '''
        @ivar: The name of the calling process
        @type: str
        '''

        self.version = version
        '''
        @ivar: The version string to use
        @type: str
        '''

        self.description = 'Rotates and compresses system logs.'
        '''
        @ivar: description of the program
        @type: str
        '''

        self.usage = "Usage: %s [options] <configfile>" %(prog)
        '''
        @ivar: the usage string in getopt help output
        @type: str
        '''

        self.options = None
        '''
        @ivar: a dict with all given commandline options
               after calling getOpts()
        @type: dict or None
        '''

        self.args = None
        '''
        @ivar: a list with all commandline parameters, what are not options
        @type: list or None
        '''

        self.parsed = False
        '''
        @ivar: flag, whether the parsing was done
        @type: bool
        '''

        if version:
            self.version = version

        self.parser = OptionParser(
                prog             = self.prog,
                version          = self.version,
                description      = self.description,
                usage            = self.usage,
                conflict_handler = "resolve",
        )
        '''
        @ivar: the working OptionParser Object
        @type: optparse.OptionParser
        '''

        self._add_options()

    #-------------------------------------------------------
    def _add_options(self):
        '''
        Private function to add all necessary options
        to the OptionParser object
        '''

        if self.parser.has_option('--help'):
            self.parser.remove_option('--help')

        if self.parser.has_option('--version'):
            self.parser.remove_option('--version')

        self.parser.add_option(
            '--simulate',
            '--test',
            '-T',
            default = False,
            action  = 'store_true',
            dest    = 'test',
            help    = 'set this do simulate commands'
        )

        self.parser.add_option(
            '--verbose',
            '-v',
            default = False,
            action  = 'count',
            dest    = 'verbose',
            help    = 'set the verbosity level'
        )

        self.parser.add_option(
            '--debug',
            '-d',
            default = False,
            action  = 'store_true',
            dest    = 'debug',
            help    = "Don't do anything, just test (implies -v and -T)"
        )

        self.parser.add_option(
            '--force',
            '-f',
            default = False,
            action  = 'store_true',
            dest    = 'force',
            help    = "Force file rotation"
        )

        self.parser.add_option(
            '--config-check',
            '-c',
            default = False,
            action  = 'store_true',
            dest    = 'configcheck',
            help    = "Checks only the given configuration file and does "
                      + "nothing. Conflicts with -f",
        )

        self.parser.add_option(
            '--state',
            '-s',
            dest    = "statefile",
            metavar = 'FILE',
            help    = 'Path of state file (different to configuration)',
        )

        ######
        # Deprecated options for compatibilty to logrotate
        group = OptionGroup(self.parser, "Deprecated options")

        group.add_option(
            '--mail',
            '-m',
            dest    = "mailcmd",
            metavar = 'CMD',
            help    = ( ( 'Should tell %s which command to use '
                        + 'when mailing logs - not used.' )
                        %(str(self.prog)) ),
        )

        self.parser.add_option_group(group)

        ######
        # Option group for common options

        group = OptionGroup(self.parser, "Common options")

        group.add_option(
            '-h',
            '-?',
            '--help',
            '--usage',
            default = False,
            action  = 'help',
            dest    = 'help',
            help    = 'shows a help message and exit'
        )

        group.add_option(
            '-V',
            '--version',
            default = False,
            action  = 'version',
            dest    = 'version',
            help    = 'shows the version number of the program and exit',
        )

        self.parser.add_option_group(group)

    #----------------------------------------------------------------------
    def getOpts(self):
        '''
        Wrapper function to OptionParser.parse_args().
        Sets self.options and self.args with the appropriate values.
        @return: None
        '''

        if not self.parsed:
            self.options, self.args = self.parser.parse_args()
            self.parsed = True

        if self.options.force and self.options.configcheck:
            raise LogrotateOptParserError('Invalid usage of --force and '
                + '--config-check.')

        if self.args is None:
            raise LogrotateOptParserError('No configuration file given.')

        if len(self.args) != 1:
            raise LogrotateOptParserError('Only one configuration file is allowed.')

        if self.options.mailcmd:
            sys.stderr.write('Usage of --mail is deprecated '
                + 'in this version.\n\n')

#========================================================================

if __name__ == "__main__":
    main()


#========================================================================

# vim: fileencoding=utf-8 filetype=python ts=4 expandtab
