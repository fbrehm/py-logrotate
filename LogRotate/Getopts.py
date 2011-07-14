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
import os.path
import gettext

from optparse import OptionError
from optparse import OptionParser
from optparse import OptionGroup
from optparse import OptionConflictError

try:
    import LogRotate.Common
except ImportError:
    sys.path.append(os.path.abspath(os.path.join(sys.path[0], '..')))
    import LogRotate.Common

from LogRotate.Common import to_unicode_or_bust

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
                        local_dir = None,
    ):
        '''
        Constructor.

        @param prog:      The name of the calling process (e.g. sys.argv[0])
        @type prog:       str
        @param version:   The version string to use
        @type version:    str
        @param local_dir: The directory, where the i18n-files (*.mo)
                          are located. If None, then system default
                          (/usr/share/locale) is used.
        @type local_dir:  str or None

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

        self.local_dir = local_dir
        '''
        @ivar: The directory, where the i18n-files (*.mo) are located.
        @type: str or None
        '''

        self.t = gettext.translation(
            'pylogrotate',
            local_dir,
            fallback = True
        )
        '''
        @ivar: a gettext translation object
        @type: gettext.translation
        '''

        _ = self.t.lgettext

        self.description = _('Rotates, compresses and mails system logs.')
        '''
        @ivar: description of the program
        @type: str
        '''

        msg = _("%s [options] <configfile>")
        self.usage = msg % (prog)
        '''
        @ivar: the usage string in getopt help output
        @type: str
        '''
        self.usage += ( '       %s [-h|-?|--help]\n' %(prog) )
        self.usage += ( '       %s --usage\n' %(prog) )
        self.usage += ( '       %s --version' %(prog) )

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

        #print ""
        #print "Default system encoding:     »%s«." % (sys.getdefaultencoding())
        #print "Default filesystem encoding: »%s«." % (sys.getfilesystemencoding())
        #print ""

        _ = self.t.lgettext

        if self.parser.has_option('--help'):
            self.parser.remove_option('--help')

        if self.parser.has_option('--version'):
            self.parser.remove_option('--version')

        msg = _('Set this do simulate commands')
        self.parser.add_option(
            '--simulate',
            '--test',
            '-T',
            default = False,
            action  = 'store_true',
            dest    = 'test',
            help    = to_unicode_or_bust(msg),
        )

        msg = _('Set the verbosity level')
        self.parser.add_option(
            '--verbose',
            '-v',
            default = False,
            action  = 'count',
            dest    = 'verbose',
            help    = to_unicode_or_bust(msg),
        )

        msg = _("Don't do anything, just test (implies -v and -T)")
        self.parser.add_option(
            '--debug',
            '-d',
            default = False,
            action  = 'store_true',
            dest    = 'debug',
            help    = to_unicode_or_bust(msg),
        )

        msg = _("Force file rotation")
        self.parser.add_option(
            '--force',
            '-f',
            default = False,
            action  = 'store_true',
            dest    = 'force',
            help    = to_unicode_or_bust(msg),
        )

        msg = _("Checks only the given configuration file and does nothing. Conflicts with -f.")
        self.parser.add_option(
            '--config-check',
            '-c',
            default = False,
            action  = 'store_true',
            dest    = 'configcheck',
            help    = to_unicode_or_bust(msg),
        )

        msg = _('Path of state file (different to configuration)')
        self.parser.add_option(
            '--state',
            '-s',
            dest    = "statefile",
            metavar = 'FILE',
            help    = to_unicode_or_bust(msg),
        )

        msg = _('Path of PID file (different to configuration)')
        self.parser.add_option(
            '--pid-file',
            '-P',
            dest    = "pidfile",
            metavar = 'FILE',
            help    = to_unicode_or_bust(msg),
        )

        msg = _('Command to send mail (instead of using SMTP or the predefined sendmail command).')
        self.parser.add_option(
            '--mail',
            '-m',
            dest    = "mailcmd",
            metavar = 'CMD',
            help    = to_unicode_or_bust(msg),
        )

        ######
        # Option group for common options

        group = OptionGroup(self.parser, _("Common options"))

        msg = _('Shows a help message and exit.')
        group.add_option(
            '-h',
            '-?',
            '--help',
            default = False,
            action  = 'help',
            dest    = 'help',
            help    = to_unicode_or_bust(msg),
        )

        msg = _('Display brief usage message and exit.')
        group.add_option(
            '--usage',
            default = False,
            action  = 'store_true',
            dest    = 'usage',
            help    = to_unicode_or_bust(msg),
        )

        msg = _('Shows the version number of the program and exit.')
        group.add_option(
            '-V',
            '--version',
            default = False,
            action  = 'version',
            dest    = 'version',
            help    = to_unicode_or_bust(msg),
        )

        self.parser.add_option_group(group)

    #----------------------------------------------------------------------
    def getOpts(self):
        '''
        Wrapper function to OptionParser.parse_args().
        Sets self.options and self.args with the appropriate values.
        @return: None
        '''

        _ = self.t.lgettext

        if not self.parsed:
            self.options, self.args = self.parser.parse_args()
            self.parsed = True

        if self.options.usage:
            self.parser.print_usage()
            sys.exit(0)

        if self.options.force and self.options.configcheck:
            msg = _('Invalid usage of --force and --config-check.')
            raise LogrotateOptParserError(msg)

        if self.args is None or len(self.args) < 1:
            msg = _('No configuration file given.')
            raise LogrotateOptParserError(msg)

        if len(self.args) != 1:
            msg = _('Only one configuration file is allowed.')
            raise LogrotateOptParserError(msg)

#========================================================================

if __name__ == "__main__":
    pass


#========================================================================

# vim: fileencoding=utf-8 filetype=python ts=4 expandtab
