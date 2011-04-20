#!/usr/bin/env python
# -*- coding: utf-8 -*-

# $Id$
# $URL$

'''
@author: Frank Brehm
@contact: frank@brehm-online.com
@license: GPL3
@copyright: (c) 2010-2011 by Frank Brehm, Berlin
@version: 0.1.0
@summary: Application handler module for Python logrotating
'''

# Für Terminal-Dinge: http://code.activestate.com/recipes/475116/

import re
import sys
import gettext
import logging
import pprint

from LogRotateConfig import LogrotateConfigurationError
from LogRotateConfig import LogrotateConfigurationReader

revision = '$Revision$'
revision = re.sub( r'\$', '', revision )
revision = re.sub( r'Revision: ', r'r', revision )
revision = re.sub( r'\s*$', '', revision )

__author__    = 'Frank Brehm'
__copyright__ = '(C) 2011 by Frank Brehm, Berlin'
__contact__    = 'frank@brehm-online.com'
__version__    = '0.1.0 ' + revision
__license__    = 'GPL3'


#========================================================================

class LogrotateHandlerError(Exception):
    '''
    Base class for exceptions in this module.
    '''

#========================================================================

class LogrotateHandler(object):
    '''
    Class for application handler for Python logrotating

    @author: Frank Brehm
    @contact: frank@brehm-online.com
    '''

    #-------------------------------------------------------
    def __init__( self, config_file,
                        test       = False,
                        verbose    = 0,
                        force      = False,
                        state_file = None,
                        mail_cmd   = None,
                        local_dir  = None,
    ):
        '''
        Costructor.

        @param config_file: the configuration file to use
        @type config_file:  str
        @param prog:        testmode, no real actions are made
        @type prog:         bool
        @param verbose:     verbosity (debug) level
        @type verbose:      int
        @param force:       Force file rotation
        @type force:        bool
        @param state_file:  Path of state file (different to configuration)
        @type state_file:   str or None
        @param mail_cmd:    command to send mail (instead of using
                            the Phyton email package)
        @type mail_cmd:     str or None
        @param local_dir:   The directory, where the i18n-files (*.mo)
                            are located. If None, then system default
                            (/usr/share/locale) is used.
        @type local_dir:    str or None

        @return: None
        '''

        self.local_dir = local_dir
        '''
        @ivar: The directory, where the i18n-files (*.mo) are located.
        @type: str or None
        '''

        self.t = gettext.translation(
            'LogRotateHandler',
            local_dir,
            fallback = True
        )
        '''
        @ivar: a gettext translation object
        @type: gettext.translation
        '''

        _ = self.t.lgettext

        self.verbose = verbose
        '''
        @ivar: verbosity level (0 - 9)
        @type: int
        '''

        self.test = test
        '''
        @ivar: testmode, no real actions are made
        @type: bool
        '''

        self.force = force
        '''
        @ivar: Force file rotation
        @type: bool
        '''

        self.state_file = state_file
        '''
        @ivar: Path of state file (from commandline or from configuration)
        @type: str
        '''

        self.mail_cmd = mail_cmd
        '''
        @ivar: command to send mail (instead of using the Phyton email package)
        @type: str or None
        '''

        self.config_file = config_file
        '''
        @ivar: the initial configuration file to use
        @type: str
        '''

        self.config = {}
        '''
        @ivar: the configuration, how it was read from cofiguration file(s)
        @type: dict
        '''

        #################################################
        # Create a logger object
        self.logger = logging.getLogger('pylogrotate')
        '''
        @ivar: logger object
        @type: logging.getLogger
        '''

        self.logger.setLevel(logging.DEBUG)

        pp = pprint.PrettyPrinter(indent=4)
        # create console handler and set level to debug
        ch = logging.StreamHandler()
        #ch.setLevel(logging.DEBUG)
        if verbose:
            ch.setLevel(logging.DEBUG)
        else:
            ch.setLevel(logging.INFO)

        # create formatter
        formatter = logging.Formatter('[%(asctime)s]: %(name)s %(levelname)-8s'
                                        + ' - %(message)s')

        # add formatter to ch
        ch.setFormatter(formatter)

        # add ch to logger
        self.logger.addHandler(ch)

        self.logger.debug( _("Logrotating initialised") )

        if not self.read_configuration():
            self.logger.error( _('Could not read configuration') )
            sys.exit(1)

        self.logger.debug( _("Logrotating ready for work") )

    #------------------------------------------------------------
    def __str__(self):
        '''
        Typecasting function for translating object structure
        into a string

        @return: structure as string
        @rtype:  str
        '''

        pp = pprint.PrettyPrinter(indent=4)
        structure = {
            'config':      self.config,
            'config_file': self.config_file,
            'force':       self.force,
            'local_dir':   self.local_dir,
            'mail_cmd':    self.mail_cmd,
            'state_file':  self.state_file,
            'test':        self.test,
            'verbose':     self.verbose,
        }
        return pp.pformat(structure)

    #------------------------------------------------------------
    def read_configuration(self):
        '''
        Reads the configuration from self.config_file

        @return: Success of reading
        @rtype:  bool
        '''

        _ = self.t.lgettext

        config_reader = LogrotateConfigurationReader(
            config_file = self.config_file,
            verbose     = self.verbose,
            logger      = self.logger,
            local_dir   = self.local_dir,
        )

        if self.verbose > 2:
            self.logger.debug( _("Configuration reader object structure")
                            + ':\n' + str(config_reader) )

        try:
            self.config = config_reader.get_config()
        except LogrotateConfigurationError, e:
            self.logger.error( str(e) )
            sys.exit(10)

        return True

#========================================================================

if __name__ == "__main__":
    pass


#========================================================================

# vim: fileencoding=utf-8 filetype=python ts=4 expandtab
