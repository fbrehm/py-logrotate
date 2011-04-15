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

class LogrotateOptParser(object):
    '''
    Class for parsing commandline options of Python logrotating.

    @author: Frank Brehm
    @contact: frank@brehm-online.com
    '''

    #-------------------------------------------------------
    def __init__( self, prog = '%prog',
                        version = None,
                        description = 'rotates and compresses system logs',
                        usage = 'Usage: %s [options]',
    ):
        '''
        Costructor.
        @param prog: The name of the calling process (e.g. sys.argv[0])
        @type prog: str
        @param version: The version string to use
        @type version: str
        @param description: The Description the process should use
        @type description: str
        @param usage: An usage string fro the help screen, must have a '%s' for the program name
        @type usage: str
        @return: None
        '''

        self.prog = prog
        '''
        @ivar: The name of the calling process
        @type: str
        '''

        self.version = __version__
        '''
        @ivar: The version string to use
        @type: str
        '''

        self.description = description
        '''
        @ivar: description of the program
        @type: str
        '''

        self.usage = usage %(prog)
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
                prog        = self.prog,
                version     = self.version,
                description = self.description,
                usage       = self.usage
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

#========================================================================

if __name__ == "__main__":
    main()


#========================================================================

# vim: fileencoding=utf-8 filetype=python ts=4 expandtab
