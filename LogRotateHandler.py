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
import os
import os.path
import errno
import socket

from LogRotateConfig import LogrotateConfigurationError
from LogRotateConfig import LogrotateConfigurationReader

from LogRotateStatusFile import LogrotateStatusFileError
from LogRotateStatusFile import LogrotateStatusFile

revision = '$Revision$'
revision = re.sub( r'\$', '', revision )
revision = re.sub( r'Revision: ', r'r', revision )
revision = re.sub( r'\s*$', '', revision )

__author__    = 'Frank Brehm'
__copyright__ = '(C) 2011 by Frank Brehm, Berlin'
__contact__    = 'frank@brehm-online.com'
__version__    = '0.3.0 ' + revision
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
                        test         = False,
                        verbose      = 0,
                        force        = False,
                        config_check = False,
                        state_file   = None,
                        pid_file     = None,
                        mail_cmd     = None,
                        local_dir    = None,
    ):
        '''
        Costructor.

        @param config_file:  the configuration file to use
        @type config_file:   str
        @param prog:         testmode, no real actions are made
        @type prog:          bool
        @param verbose:      verbosity (debug) level
        @type verbose:       int
        @param force:        Force file rotation
        @type force:         bool
        @param config_check: Checks only the configuration and does nothing
        @type config_check:  bool
        @param state_file:   Path of state file (different to configuration)
        @type state_file:    str or None
        @param pid_file:     Path of PID file (different to configuration)
        @type pid_file:      str or None
        @param mail_cmd:     command to send mail (instead of using
                             the Phyton email package)
        @type mail_cmd:      str or None
        @param local_dir:    The directory, where the i18n-files (*.mo)
                             are located. If None, then system default
                             (/usr/share/locale) is used.
        @type local_dir:     str or None

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

        self.state_file = None
        '''
        @ivar: the state file object after his initialisation
        @type: LogRotateStateFile or None
        '''

        self.state_file_name = state_file
        '''
        @ivar: Path of state file (from commandline or from configuration)
        @type: str
        '''

        self.pid_file = pid_file
        '''
        @ivar: Path of PID file (from commandline or from configuration)
        @type: str
        '''

        self.pidfile_created = False
        '''
        @ivar: Is a PID file created by this instance and should removed
               on destroying this object.
        @type: bool
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

        self.scripts = {}
        '''
        @ivar: list of all named scripts found in configuration
        @type: list
        '''

        self.template = {}
        '''
        @ivar: things to do in olddir stuff
        @type: dict
        '''
        self._prepare_templates()

        self.files_delete = {}
        '''
        @ivar: dictionary with all files, they have to delete
        @type: dict
        '''

        self.files_compress = {}
        '''
        @ivar: dictionary with all files, they have to compress
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

        if config_check:
            return

        if not self._check_pidfile():
            sys.exit(3)

        if not self._write_pidfile():
            sys.exit(3)

        self.logger.debug( _("Logrotating ready for work") )

        # Create status file object
        self.state_file = LogrotateStatusFile(
            file_name = self.state_file_name,
            local_dir = self.local_dir,
            verbose   = self.verbose,
            test_mode = self.test,
            logger    = self.logger,
        )

    #------------------------------------------------------------
    def __str__(self):
        '''
        Typecasting function for translating object structure
        into a string

        @return: structure as string
        @rtype:  str
        '''

        pp = pprint.PrettyPrinter(indent=4)
        structure = self.as_dict()
        return pp.pformat(structure)

    #-------------------------------------------------------
    def as_dict(self):
        '''
        Transforms the elements of the object into a dict

        @return: structure as dict
        @rtype:  dict
        '''

        res = {
            'config':          self.config,
            'config_file':     self.config_file,
            'files_delete':    self.files_delete,
            'files_compress':  self.files_compress,
            'force':           self.force,
            'local_dir':       self.local_dir,
            'logger':          self.logger,
            'mail_cmd':        self.mail_cmd,
            'scripts':         self.scripts,
            'state_file':      None,
            'state_file_name': self.state_file_name,
            'pid_file':        self.pid_file,
            'pidfile_created': self.pidfile_created,
            't':               self.t,
            'test':            self.test,
            'template':        self.template,
            'verbose':         self.verbose,
        }
        if self.state_file:
            res['state_file'] = self.state_file.as_dict()

        return res

    #------------------------------------------------------------
    def __del__(self):
        '''
        Destructor.
        No parameters, no return value.
        '''

        _ = self.t.lgettext

        if self.pidfile_created:
            if os.path.exists(self.pid_file):
                self.logger.debug( _("Removing PID file '%s' ...") % (self.pid_file) )
                try:
                    os.remove(self.pid_file)
                except OSError, e:
                    self.logger.error( _("Error removing PID file '%(file)s': %(msg)")
                        % { 'file': self.pid_file, 'msg': str(e) }
                    )

    #------------------------------------------------------------
    def _prepare_templates(self):
        '''
        Preparing self.template with values for placeholders
        in olddir stuff.
        '''

        self.template = {}

        hostname = socket.getfqdn()
        self.template['nodename'] = hostname
        self.template['domain'] = ''

        match = re.search(r'^([^\.]+)\.(.*)', hostname)
        if match:
            self.template['nodename'] = match.group(1)
            self.template['domain'] = match.group(2)

        uname = os.uname()
        self.template['sysname'] = uname[0]
        self.template['release'] = uname[2]
        self.template['version'] = uname[3]
        self.template['machine'] = uname[4]

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
            self.config  = config_reader.get_config()
            self.scripts = config_reader.get_scripts()
        except LogrotateConfigurationError, e:
            self.logger.error( str(e) )
            sys.exit(10)

        if self.state_file_name is None:
            if 'statusfile' in config_reader.global_option and \
                    config_reader.global_option['statusfile'] is not None:
                self.state_file_name = config_reader.global_option['statusfile']
            else:
                self.state_file_name = os.sep + os.path.join('var', 'lib', 'py-logrotate.status')
        self.logger.debug( _("Name of state file: '%s'") % (self.state_file_name) )

        if self.pid_file is None:
            if 'pidfile' in config_reader.global_option and \
                    config_reader.global_option['pidfile'] is not None:
                self.pid_file = config_reader.global_option['pidfile']
            else:
                self.pid_file = os.sep + os.path.join('var', 'run', 'py-logrotate.pid')
        self.logger.debug( _("PID file: '%s'") % (self.pid_file) )

        return True

    #------------------------------------------------------------
    def _check_pidfile(self):
        '''
        Checks the existence and consistence of self.pid_file.

        Exit, if there is a running process with a PID from this file.
        Doesn't exit in test mode.

        Writes on success (no other process) this PID file.

        @return: Success
        @rtype:  bool
        '''

        _ = self.t.lgettext

        if not os.path.exists(self.pid_file):
            if self.verbose > 1:
                self.logger.debug( _("PID file '%s' doesn't exists.") % (self.pid_file) )
            return True

        if self.test:
            self.logger.info( _("Testmode, skip test of PID file '%s'.") % (self.pid_file) )
            return True

        self.logger.debug( _("Reading PID file '%s' ...") % (self.pid_file) )
        f = None
        try:
            f = open(self.pid_file, 'r')
        except IOError, e:
            raise LogrotateHandlerError(
                _("Couldn't open PID file '%(file)s' for reading: %(msg)s")
                % { 'file': self.pid_file, 'msg': str(e) }
            )

        line = f.readline()
        f.close()

        pid = None
        line = line.strip()
        match = re.search(r'^\s*(\d+)\s*$', line)
        if match:
            pid = int(match.group(1))
        else:
            self.logger.warn( _("No useful information found in PID file '%(file)s': '%(line)s'")
                % { 'file': self.pid_file, 'line': line }
            )
            return False

        if self.verbose > 1:
            self.logger.debug( _("Trying check for process with PID %d ...") % (pid) )
        try:
            os.kill(pid, 0)
        except OSError, err:
            if err.errno == errno.ESRCH:
                self.logger.info( _("Process with PID %d anonymous died.") % (pid) )
                return True
            elif err.errno == errno.EPERM:
                self.logger.warn( _("No permission to signal the process %d ...") % (pid) )
                return True
            else:
                self.logger.warn( _("Unknown error: '%s'") % (str(err)) )
                return False
        else:
            self.logger.error( _("Process with PID %d is allready running.") % (pid) )
            return False

        return False

    #------------------------------------------------------------
    def _write_pidfile(self):
        '''
        Writes the PID of the current process in self.pid_file.

        Exit with an error, if it's not possible to write.
        Doesn't exit in test mode.

        Writes on success (no other process) this PID file.

        @return: Success
        @rtype:  bool
        '''

        _ = self.t.lgettext

        if self.test:
            self.logger.info( _("Testmode, skip writing of PID file '%s'.") % (self.pid_file) )
            return True

        self.logger.info( _("Writing PID file '%s' ...") % (self.pid_file) )

        f = None
        try:
            f = open(self.pid_file, 'w')
            f.write(str(os.getppid()) + "\n")
            f.close()
        except IOError, e:
            raise LogrotateHandlerError(
                _("Couldn't open PID file '%(file)s' for writing: %(msg)s")
                % { 'file': self.pid_file, 'msg': str(e) }
            )

        self.pidfile_created = True

        return True

    #------------------------------------------------------------
    def rotate(self):
        pass

    #------------------------------------------------------------
    def delete_oldfiles(self):
        pass

    #------------------------------------------------------------
    def compress(self):
        pass

#========================================================================

if __name__ == "__main__":
    pass


#========================================================================

# vim: fileencoding=utf-8 filetype=python ts=4 expandtab
