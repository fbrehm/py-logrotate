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
                        description = '',
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
        self.version = version
        self.description = description
        self.usage = usage %(prog)

        self.options = None
        self.args = None
        self.__options_set = False
        self.__action_set = None
        self.parsed = False

        self.parser = OptionParser(
                prog        = self.prog,
                version     = self.version,
                description = self.description,
                usage       = self.usage
        )



#========================================================================

if __name__ == "__main__":
    main()


#========================================================================

# vim: fileencoding=utf-8 filetype=python ts=4 expandtab
