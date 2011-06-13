#!/usr/bin/env python
# -*- coding: utf-8 -*-

# $Id$
# $URL$

'''
@author: Frank Brehm
@contact: frank@brehm-online.com
@license: GPL3
@copyright: (c) 2010-2011 by Frank Brehm, Berlin
@version: 0.0.2
@summary: module for operations with the logrotate state file
'''

import re
import sys
import os
import os.path
import gettext
import logging

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

class LogrotateStatusFileError(Exception):
    '''
    Base class for exceptions in this module.
    '''

#========================================================================

class LogrotateStatusFile(object):
    '''
    Class for operations with the logrotate state file

    @author: Frank Brehm
    @contact: frank@brehm-online.com
    '''

    #-------------------------------------------------------
    def __init__( self, file_name,
                        local_dir  = None,
                        verbose    = 0,
                        test_mode  = False,
                        logger     = None,
    ):
        '''
        Costructor.

        @param config_file: the file name of the status file
        @type config_file:  str
        @param verbose:     verbosity (debug) level
        @type verbose:      int
        @param test_mode:   test mode - no write actions are made
        @type test_mode:    bool
        @param logger:      logger object to use for logging a.s.o.
        @type logger:       logging.getLogger or None
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
            'LogRotateStatusFile',
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

        self.file_name = file_name
        '''
        @ivar: the initial file name of the status file to use
        @type: str
        '''

        self.file_name_is_absolute = False
        '''
        @ivar: flag, that shows, that the file name is now an absolute path
        @type: bool
        '''

        self.fd = None
        '''
        @ivar: the file object of the opened status file, or None, if not opened
        @type: file or None
        '''

        self.status_version = None
        '''
        @ivar: the version of the status file (2 or 3)
        @type: int or None
        '''

        self.test_mode = test_mode
        '''
        @ivar: test mode - no write actions are made
        @type: bool
        '''

        self.logger = logger
        '''
        @ivar: logger object
        @type: logging.getLogger
        '''

        self.file_state = {}
        '''
        @ivar: the last rotation date of every particular log file
               keys are the asolute filenames (without globbing)
               and the values are datetime objects of the last rotation
               referencing to UTC
               If no rotation was made, value is datetime.min().
        @type: dict
        '''

        if not logger:

            #################################################
            # Create a logger object, if necessary
            self.logger = logging.getLogger('logrotate_state_file')

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
            formatter = logging.Formatter(
                '[%(asctime)s]: %(name)s %(levelname)-8s - %(message)s'
            )

            # add formatter to ch
            ch.setFormatter(formatter)

            # add ch to logger
            self.logger.addHandler(ch)

    #-------------------------------------------------------
    def _read(self, must_exists = True):
        '''
        Reads the status file and put the results in the dict self.file_state.
        Puts back the absolute path of the status file in self.file_name on success.

        Throws a LogrotateStatusFileError on a error.

        @param must_exists: throws an exception, if true and the status file
                            doesn't exists
        @type must_exists:  bool

        @return:    success of reading
        @rtype:     bool
        '''

        self.file_state = {}
        _ = self.t.lgettext

        # Check for existence of status file
        if not os.path.exists(self.file_name):
            msg = _("Status file '%s' doesn't exists.") % (self.file_name)
            if must_exists:
                raise LogrotateStatusFileError(msg)
            else:
                self.logger.info(msg)
            return False

        # makes the name of the status file an absolute path
        if not self.file_name_is_absolute:
            self.file_name = os.path.abspath(self.file_name)
            self.file_name_is_absolute = True
            if self.verbose > 2:
                msg = _("Absolute path of status file is now '%s'.") % (self.file_name)
                self.logger.debug(msg)

        # Checks, that the status file is a regular file
        if not os.path.isfile(self.file_name):
            msg = _("Status file '%s' is not a regular file.") % (self.file_name)
            raise LogrotateStatusFileError(msg)
            return False

        msg = _("Reading status file '%s' ...") % (self.file_name)
        self.logger.debug(msg)

        fd = None
        try:
            fd = open(self.file_name, 'Ur')
        except IOError, e:
            msg = _("Could not read status file '%s': ") % (configfile) + str(e)
            raise LogrotateStatusFileError(msg)
        self.fd = fd

        

        return True

#========================================================================

if __name__ == "__main__":
    pass


#========================================================================

# vim: fileencoding=utf-8 filetype=python ts=4 expandtab
