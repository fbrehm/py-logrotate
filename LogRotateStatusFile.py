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
                        logger     = None,
    ):
        '''
        Costructor.

        @param config_file: the file name of the status file
        @type config_file:  str
        @param verbose:     verbosity (debug) level
        @type verbose:      int
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

        self.logger = logger
        '''
        @ivar: logger object
        @type: logging.getLogger
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


#========================================================================

if __name__ == "__main__":
    pass


#========================================================================

# vim: fileencoding=utf-8 filetype=python ts=4 expandtab
