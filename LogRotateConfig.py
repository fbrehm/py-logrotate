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
@summary: module the configuration parsing object for Python logrotating
'''

import re
import sys
import gettext
import pprint
import os.path

revision = '$Revision$'
revision = re.sub( r'\$', '', revision )
revision = re.sub( r'Revision: ', r'r', revision )
revision = re.sub( r'\s*$', '', revision )

__author__    = 'Frank Brehm'
__copyright__ = '(C) 2011 by Frank Brehm, Berlin'
__contact__    = 'frank@brehm-online.com'
__version__    = '0.0.2 ' + revision
__license__    = 'GPL3'


#========================================================================
# Module variables

# @var: dict with all valid taboo pattern types as keys
#       and the resulting regex template for the filename as value
pattern_types = {
    'ext':    r'%s$',
    'file':   r'^%s$',
    'prefix': r'^%s',
}

#========================================================================

class LogrotateConfigurationError(Exception):
    '''
    Base class for exceptions in this module.
    '''

#========================================================================

class LogrotateConfigurationReader(object):
    '''
    Class for reading the configuration for Python logrotating

    @author: Frank Brehm
    @contact: frank@brehm-online.com
    '''

    #-------------------------------------------------------
    def __init__( self, config_file,
                        verbose    = 0,
                        logger     = None,
                        local_dir  = None,
    ):
        '''
        Costructor.

        @param config_file: the configuration file to use
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
            'LogRotateConfig',
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

        self.config_file = config_file
        '''
        @ivar: the initial configuration file to use
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
            self.logger = logging.getLogger('logrotate_cfg')

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

        #############################################
        # the rest of instance variables:

        self.default = {}
        '''
        @ivar: the dafault values for  directives
        @type: dict
        '''
        self.reset_defaults()

        self.taboo = []
        '''
        @ivar: taboo patterns for including files of whole directories
        @type: list
        '''
        self.add_taboo(r'\.rpmnew',        'ext');
        self.add_taboo(r'\.rpmorig',       'ext');
        self.add_taboo(r'\.rpmsave',       'ext');
        self.add_taboo(r',v',              'ext');
        self.add_taboo(r'\.swp',           'ext');
        self.add_taboo(r'~',               'ext');
        self.add_taboo(r'\.',              'prefix');
        self.add_taboo(r'\.bak',           'ext');
        self.add_taboo(r'\.old',           'ext');
        self.add_taboo(r'\.rej',           'ext');
        self.add_taboo(r'CVS',             'file');
        self.add_taboo(r'RCS',             'file');
        self.add_taboo(r'\.disabled',      'ext');
        self.add_taboo(r'\.dpkg-old',      'ext');
        self.add_taboo(r'\.dpkg-dist',     'ext');
        self.add_taboo(r'\.dpkg-new',      'ext');
        self.add_taboo(r'\.cfsaved',       'ext');
        self.add_taboo(r'\.ucf-old',       'ext');
        self.add_taboo(r'\.ucf-dist',      'ext');
        self.add_taboo(r'\.ucf-new',       'ext');
        self.add_taboo(r'\.cfsaved',       'ext');
        self.add_taboo(r'\.rhn-cfg-tmp-*', 'ext');

        self.config_files = {}
        '''
        @ivar: dict with all called and included configuration files
               to avoid double including
        @type: dict
        '''

        self.config_was_read = False
        '''
        @ivar: flag whether the configuration file was read.
        @type: bool
        '''

        self.config = {}
        '''
        @ivar: the configuration, how it was read from cofiguration file(s)
        @type: dict
        '''

        self.logger.debug( _("Logrotate config reader initialised") )

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
            'config':          self.config,
            'config_file':     self.config_file,
            'config_files':    self.config_files,
            'config_was_read': self.config_was_read,
            'default':         self.default,
            'local_dir':       self.local_dir,
            'taboo':           self.taboo,
            'verbose':         self.verbose,
        }
        return pp.pformat(structure)

    #------------------------------------------------------------
    def reset_defaults(self):
        '''
        Resetting self.default to the hard coded values
        '''

        _ = self.t.lgettext

        if self.verbose > 3:
            self.logger.debug( _("Resetting default values for directives "
                    + "to hard coded values") )

        self.default = {}

        self.default['compress']      = None
        self.default['copytruncate']  = None
        self.default['create']        = {
            'mode':  None,
            'owner': None,
            'group': None,
        },
        self.default['period']        = 7
        self.default['dateext']       = None
        self.default['datepattern']   = '%Y-%m-%d'
        self.default['delaycompress'] = None
        self.default['extension']     = ""
        self.default['ifempty']       = 1
        self.default['maxage']        = None
        self.default['missingok']     = None
        self.default['olddir']        = {
            'dirname':    '',
            'dateformat': None,
            'mode':       None,
            'owner':      None,
            'group':      None,
        },
        self.default['rotate']        = 4
        self.default['size']          = None

    #------------------------------------------------------------
    def add_taboo(self, pattern, pattern_type = 'file'):
        '''
        Add a pattern to the list of taboo patterns self.taboo
        Raises a general exception, if pattern_type is invalid

        @param pattern:      The patten to append to the taboo list
        @type pattern:       str
        @param pattern_type: The type of the taboo pattern
                            ('ext', 'file' or 'prefix')
        @type pattern_type:  str

        @return: None
        '''

        _ = self.t.lgettext

        if not pattern_type in pattern_types:
            raise Exception( _('Invalid pattern type "%s" given') % (pattern_type) )

        pattern = ( pattern_types[pattern_type] % pattern )
        if self.verbose > 3:
            self.logger.debug( _("New taboo pattern: '%s'.") % (pattern) )

        self.taboo.append(pattern)

    #------------------------------------------------------------
    def get_config(self):
        '''
        Returns the configuration, how it was read from configuration file(s)

        @return: configuration
        @rtype:  dict or None
        '''

        if not self.config_was_read:
            if not self._read():
                return None

        return self.config

    #------------------------------------------------------------
    def _read(self):
        '''
        Reads the configuration from configuration file and all
        included files
        '''

        _ = self.t.lgettext
        self.logger.debug( _("Try reading configuration from '%s' ...")
                            % (self.config_file) )

        if not os.path.exists(self.config_file):
            raise LogrotateConfigurationError(
                _("File '%s' doesn't exists.") % (self.config_file)
            )

        self.config_file = os.path.abspath(self.config_file)

        if not os.path.isfile(self.config_file):
            raise LogrotateConfigurationError(
                _("'%s' is not a regular file.") % (self.config_file)
            )

        self.config_files[self.config_file] = True

        self.logger.info( _("Reading configuration from '%s' ...")
                            % (self.config_file) )

        cfile = None
        try:
            cfile = open(self.config_file, 'Ur')
        except IOError, e:
            raise LogrotateConfigurationError(
                ( _("Could not read configuration file '%s'")
                    % (self.config_file) )
                + ': ' + str(e)
            )
        lines = cfile.readlines()
        cfile.close()

        return True

#========================================================================

if __name__ == "__main__":
    pass


#========================================================================

# vim: fileencoding=utf-8 filetype=python ts=4 expandtab
