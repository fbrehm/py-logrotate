#!/usr/bin/env python
# -*- coding: utf-8 -*-

# $Id$
# $URL$

'''
@author: Frank Brehm
@contact: frank@brehm-online.com
@license: GPL3
@copyright: (c) 2010-2011 by Frank Brehm, Berlin
@version: 0.4.0
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
import subprocess
import shutil
import glob
from datetime import datetime, timedelta
import time
import gzip
import bz2
import zipfile

from LogRotateConfig import LogrotateConfigurationError
from LogRotateConfig import LogrotateConfigurationReader

from LogRotateStatusFile import LogrotateStatusFileError
from LogRotateStatusFile import LogrotateStatusFile
from LogRotateStatusFile import utc

revision = '$Revision$'
revision = re.sub( r'\$', '', revision )
revision = re.sub( r'Revision: ', r'r', revision )
revision = re.sub( r'\s*$', '', revision )

__author__    = 'Frank Brehm'
__copyright__ = '(C) 2011 by Frank Brehm, Berlin'
__contact__    = 'frank@brehm-online.com'
__version__    = '0.4.0 ' + revision
__license__    = 'GPL3'


#========================================================================

class LogrotateHandlerError(Exception):
    '''
    Base class for exceptions in this module.
    '''

#========================================================================

class StdoutFilter(logging.Filter):
    '''
    Class, that filters all logrecords
    '''

    def filter(self, record):
        '''
        Filtering log records and let through messages
        except them with the level names 'WARNING', 'ERROR' or 'CRITICAL'.

        @param record: the record to filter
        @type record:  logging.LogRecord

        @return: pass the record or not
        '''
        if record.levelname == 'WARNING':
            return False
        if record.levelname == 'ERROR':
            return False
        if record.levelname == 'CRITICAL':
            return False
        return True

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
        Constructor.

        @param config_file:  the configuration file to use
        @type config_file:   str
        @param test:         testmode, no real actions are made
        @type test:          bool
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

        self.config = []
        '''
        @ivar: the configuration, how it was read from cofiguration file(s)
        @type: dict
        '''

        self.scripts = {}
        '''
        @ivar: list of LogRotateScript objects with all named scripts found in configuration
        @type: list
        '''

        self.template = {}
        '''
        @ivar: things to do in olddir stuff
        @type: dict
        '''
        self._prepare_templates()

        self.logfiles = []
        '''
        @ivar: list of all rotated logfiles. Each entry is a dict with
               three keys:
                - 'original': str with the name of the unrotated file
                - 'rotated':  str with the name of the rotated file
                - 'oldfiles:  list with all old rotated files of this file
                - 'desc_index': index of list self.config for appropriate
                                logfile definition
        @type: list
        '''

        self.files_delete = {}
        '''
        @ivar: dictionary with all files, they have to delete
        @type: dict
        '''

        self.files_compress = {}
        '''
        @ivar: dictionary with all files, they have to compress
               keys are the filenames, values are the index number
               of the list self.config (for compress options)
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

        # create formatter
        format_str = '[%(asctime)s]: %(levelname)-8s - %(message)s'
        if test:
            format_str = '%(levelname)-8s - %(message)s'
        if verbose:
            if verbose > 1:
                format_str = '[%(asctime)s]: %(name)s %(funcName)s() %(levelname)-8s - %(message)s'
                if test:
                    format_str = '%(name)s %(funcName)s() %(levelname)-8s - %(message)s'
            else:
                format_str = '[%(asctime)s]: %(name)s %(levelname)-8s - %(message)s'
                if test:
                    format_str = '%(name)s %(levelname)-8s - %(message)s'
        formatter = logging.Formatter(format_str)

        # create console handler for error messages
        console_stderr = logging.StreamHandler(sys.stderr)
        console_stderr.setLevel(logging.WARNING)
        console_stderr.setFormatter(formatter)
        self.logger.addHandler(console_stderr)

        # create console handler for other messages
        console_stdout = logging.StreamHandler(sys.stdout)
        if verbose:
            console_stdout.setLevel(logging.DEBUG)
        else:
            console_stdout.setLevel(logging.INFO)
        fltr = StdoutFilter()
        console_stdout.addFilter(fltr)
        console_stdout.setFormatter(formatter)
        self.logger.addHandler(console_stdout)

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
            'logfiles':        self.logfiles,
            'logger':          self.logger,
            'mail_cmd':        self.mail_cmd,
            'scripts':         {},
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

        for script_name in self.scripts.keys():
            res['scripts'][script_name] = self.scripts[script_name].as_dict()

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
            test_mode   = self.test,
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

        self.logger.debug( _("Writing PID file '%s' ...") % (self.pid_file) )

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
        '''
        Starting the underlying rotating.

        @return: None
        '''

        _ = self.t.lgettext

        if len(self.config) < 1:
            msg = _("No logfile definitions found.")
            self.logger.info(msg)
            return

        msg = _("Starting underlying rotation ...")
        self.logger.info(msg)

        cur_desc_index = 0
        for d in self.config:
            self._rotate_definition(cur_desc_index)
            cur_desc_index += 1

        # Check for left over scripts to execute
        for scriptname in self.scripts.keys():
            if self.verbose >= 4:
                msg = ( _("State of script '%s':") % (scriptname) ) \
                        + "\n" + str(self.scripts[scriptname])
                self.logger.debug(msg)
            del self.scripts[scriptname]

        return

    #------------------------------------------------------------
    def _rotate_definition(self, cur_desc_index):
        '''
        Rotation of a logfile definition from a configuration file.

        @param cur_desc_index: index of self.config for definition
                               of logfile from configuration file
        @type cur_desc_index:  int

        @return: None
        '''

        definition = self.config[cur_desc_index]

        _ = self.t.lgettext

        if self.verbose >= 4:
            pp = pprint.PrettyPrinter(indent=4)
            msg = _("Rotating of logfile definition:") + \
                    "\n" + pp.pformat(definition)
            self.logger.debug(msg)

        # re-reading of status file
        self.state_file.read()

        for logfile in definition['files']:
            if self.verbose > 1:
                msg = ( _("Performing logfile '%s' ...") % (logfile)) + "\n"
                self.logger.debug(msg)
            should_rotate = self._should_rotate(logfile, cur_desc_index)
            if self.verbose > 1:
                if should_rotate:
                    msg = _("logfile '%s' WILL rotated.")
                else:
                    msg = _("logfile '%s' will NOT rotated.")
                self.logger.debug(msg % (logfile))
            if not should_rotate:
                continue
            self._rotate_file(logfile, cur_desc_index)

        return

    #------------------------------------------------------------
    def _rotate_file(self, logfile, cur_desc_index):
        '''
        Rotates a logfile with all with all necessary actions before
        and after rotation.

        Throughs an LogrotateHandlerError on error.

        @param logfile: the logfile to rotate
        @type logfile:  str
        @param cur_desc_index: index of self.config for definition
                               of logfile from configuration file
        @type cur_desc_index:  int

        @return: None
        '''

        definition = self.config[cur_desc_index]

        _ = self.t.lgettext

        sharedscripts = definition['sharedscripts']
        firstscript   = definition['firstaction']
        prescript     = definition['prerotate']
        postscript    = definition['postrotate']
        lastscript    = definition['lastaction']

        # Executing of the firstaction script, if it wasn't executed
        if firstscript:
            if self.verbose > 2:
                msg = _("Looking, whether the firstaction script should be executed.")
                self.logger.debug(msg)
            if not self.scripts[firstscript].done_firstrun:
                msg = _("Executing firstaction script '%s' ...") % (firstscript)
                self.logger.info(msg)
                if not self.scripts[firstscript].execute():
                    return
                self.scripts[firstscript].done_firstrun = True

        # Executing prerotate scripts, if not sharedscripts or even not executed
        if prescript:
            if self.verbose > 2:
                msg = _("Looking, whether the prerun script should be executed.")
                self.logger.debug(msg)
            do_it = False
            if sharedscripts:
                if not self.scripts[prescript].done_prerun:
                    do_it = True
            else:
                do_it = True
            if do_it:
                msg = _("Executing prerun script '%s' ...") % (prescript)
                self.logger.info(msg)
                if not self.scripts[prescript].execute():
                    return
                self.scripts[prescript].done_prerun = True

        olddir = self._create_olddir(logfile, cur_desc_index)
        if olddir is None:
            return

        if not self._do_rotate_file(logfile, cur_desc_index, olddir):
            return

        # Looking for postrotate script in a similar way like for the prerotate
        if postscript:
            if self.verbose > 2:
                msg = _("Looking, whether the postrun script should be executed.")
                self.logger.debug(msg)
            do_it = False
            self.scripts[postscript].post_files -= 1
            self.scripts[postscript].do_post = True
            if sharedscripts:
                if self.scripts[postscript].post_files <= 0:
                    do_it = True
                    self.scripts[postscript].do_post = False
            else:
                do_it = True
            if do_it:
                msg = _("Executing postrun script '%s' ...") % (postscript)
                self.logger.info(msg)
                if not self.scripts[prescript].execute():
                    return
                self.scripts[postscript].done_postrun = True

        # Looking for lastaction script
        if lastscript:
            if self.verbose > 2:
                msg = _("Looking, whether the lastaction script should be executed.")
                self.logger.debug(msg)
            do_it = False
            self.scripts[lastscript].last_files -= 1
            self.scripts[lastscript].do_last = True
            if self.scripts[lastscript].done_lastrun:
                self.scripts[lastscript].do_last = False
            else:
                if self.scripts[lastscript].last_files <= 0:
                    do_it = True
                    self.scripts[lastscript].do_last = False
            if do_it:
                msg = _("Executing lastaction script '%s' ...") % (lastscript)
                self.logger.info(msg)
                if not self.scripts[lastscript].execute():
                    return
                self.scripts[lastscript].done_lastrun = True

    #------------------------------------------------------------
    def _do_rotate_file(self, logfile, cur_desc_index, olddir = None):
        '''
        The underlaying unconditionally rotation of a logfile.

        After the successful rotation 

        @param logfile: the logfile to rotate
        @type logfile:  str
        @param cur_desc_index: index of self.config for definition
                               of logfile from configuration file
        @type cur_desc_index:  int
        @param olddir: the directory of the rotated logfile
                       if "." or None, store the rotated logfile
                       in their original directory
        @type olddir: str or None

        @return: successful or not
        @rtype:  bool
        '''

        definition = self.config[cur_desc_index]

        if (olddir is not None) and (olddir == "."):
            olddir = None

        _ = self.t.lgettext

        uid = os.geteuid()
        gid = os.getegid()

        msg = _("Do rotate logfile '%s' ...") % (logfile)
        self.logger.debug(msg)

        target = self._get_rotation_target(logfile, cur_desc_index, olddir)
        rotations = self._get_rotations(logfile, target, cur_desc_index)

        extension = rotations['extension']
        compress_extension = rotations['compress_extension']

        # First move all cyclic stuff
        for pair in rotations['move']:
            file_from = pair['from']
            file_to = pair['to']
            if pair['compressed']:
                file_from += compress_extension
                file_to += compress_extension
            msg = _("Moving file '%(from)s' => '%(to)s'.") \
                    % {'from': file_from, 'to': file_to }
            self.logger.info(msg)
            if not self.test:
                try:
                    shutil.move(file_from, file_to)
                except OSError:
                    msg = _("Error on moving '%(from)s' => '%(to)s': %(err)s") \
                            % {'from': file_from, 'to': file_to, 'err': e.strerror}
                    self.logger.error(msg)
                    return False

        # Now the underlaying rotation
        file_from = rotations['rotate']['from']
        file_to = rotations['rotate']['to']

        if definition['copytruncate'] or definition['copy']:
            # Copying logfile to target
            msg = _("Copying file '%(from)s' => '%(to)s'.") \
                    % {'from': file_from, 'to': file_to }
            self.logger.info(msg)
            if not self.test:
                try:
                    shutil.copy2(file_from, file_to)
                except OSError:
                    msg = _("Error on copying '%(from)s' => '%(to)s': %(err)s") \
                            % {'from': file_from, 'to': file_to, 'err': e.strerror}
                    self.logger.error(msg)
                    return False
            if definition['copytruncate']: 
                msg = _("Truncating file '%s'.") % (file_from)
                self.logger.info(msg)
                if not self.test:
                    try:
                        fd = open(file_from, 'w')
                        fd.close()
                    except IOError, e:
                        msg = _("Error on truncing file '%(from)s': %(err)s") \
                                % {'from': file_from, 'err': str(e)}
                        self.logger.error(msg)
                        return False

        else:

            # Moving logfile to target
            msg = _("Moving file '%(from)s' => '%(to)s'.") \
                    % {'from': file_from, 'to': file_to }
            self.logger.info(msg)

            # get old permissions of logfile
            statinfo = os.stat(file_from)

            if not self.test:
                try:
                    shutil.move(file_from, file_to)
                except OSError:
                    msg = _("Error on moving '%(from)s' => '%(to)s': %(err)s") \
                            % {'from': file_from, 'to': file_to, 'err': e.strerror}
                    self.logger.error(msg)
                    return False
    
            if definition['create']['enabled']:

                # Recreate logfile
                msg = _("Recreating file '%s'.") % (file_from)
                self.logger.info(msg)
                if not self.test:
                    try:
                        fd = open(file_from, 'w')
                        fd.close()
                    except IOError, e:
                        msg = _("Error on creating file '%(from)s': %(err)s") \
                                % {'from': file_from, 'err': str(e)}
                        self.logger.error(msg)
                        return False

                # Setting permissions and ownership
                new_mode = statinfo.st_mode
                new_uid  = statinfo.st_uid
                new_gid  = statinfo.st_gid

                if not definition['create']['mode'] is None:
                    new_mode = definition['create']['mode']
                if not definition['create']['owner'] is None:
                    new_uid = definition['create']['owner']
                if not definition['create']['group'] is None:
                    new_gid = definition['create']['group']

                statinfo = os.stat(file_from)
                old_mode = statinfo.st_mode
                old_uid  = statinfo.st_uid
                old_gid  = statinfo.st_gid

                # Check and set permissions of new logfile
                if new_mode != old_mode:
                    msg = _("Setting permissions of '%(file)s' to %(mode)4o.") \
                            % {'file': file_from, 'mode': new_mode}
                    self.logger.info(msg)
                    if not self.test:
                        try:
                            os.chmod(file_from, new_mode)
                        except OSError, e:
                            msg = _("Error on chmod of '%(file)s': %(err)s") \
                                    % {'file': file_from, 'err': e.strerror}
                            self.logger.warning(msg)

                # Check and set ownership of new logfile
                if (new_uid != old_uid) or (new_gid != old_gid):
                    msg = _("Setting ownership of '%(file)s' to uid %(uid)d and gid %(gid)d.") \
                            % {'file': file_from, 'uid': new_uid, 'gid': new_gid}
                    self.logger.info(msg)
                    if not self.test:
                        try:
                            os.chown(file_from, new_uid, new_gid)
                        except OSError, e:
                            msg = _("Error on chown of '%(file)s': %(err)s") \
                                    % {'file': file_from, 'err': e.strerror}
                            self.logger.warning(msg)

        oldfiles = self._collect_old_logfiles(logfile, extension, compress_extension, cur_desc_index)

        # get files to delete and save them back in self.files_delete
        files_delete = self._collect_files_delete(oldfiles, cur_desc_index)
        if len(files_delete):
            for oldfile in files_delete:
                self.files_delete[oldfile] = True

        # get files to compress save them back in self.files_compress
        files_compress = self._collect_files_compress(oldfiles, compress_extension, cur_desc_index)
        if len(files_compress):
            for oldfile in files_compress:
                self.files_compress[oldfile] = cur_desc_index

        # write back date of rotation into state file
        self.state_file.set_rotation_date(logfile)
        self.state_file.write()

        return True

    #------------------------------------------------------------
    def _collect_files_compress(self, oldfiles, compress_extension, cur_desc_index):
        '''
        Collects a list with all old logfiles, they have to compress.

        @param oldfiles: a dict whith all found old logfiles as keys and
                        their modification time as values
        @type oldfiles:  dict
        @param compress_extension: file extension for rotated and
                                   compressed logfiles
        @type compress_extension:  str
        @param cur_desc_index: index of self.config for definition
                               of logfile from configuration file
        @type cur_desc_index:  int

        @return: all old (and compressed) logfiles to delete
        @rtype:  list
        '''

        definition = self.config[cur_desc_index]
        _ = self.t.lgettext

        if self.verbose > 2:
            msg = _("Retrieving logfiles to compress ...")
            self.logger.debug(msg)

        result = []

        if not definition['compress']:
            if self.verbose > 3:
                msg = _("No compression defined.")
                self.logger.debug(msg)
            return result

        if not oldfiles.keys():
            if self.verbose > 3:
                msg = _("No old logfiles available.")
                self.logger.debug(msg)
            return result

        no_compress = definition['delaycompress']
        if no_compress is None:
            no_compress = 0

        ce = re.escape(compress_extension)
        for oldfile in sorted(oldfiles.keys(), key=lambda x: oldfiles[x], reverse=True):

            match = re.search(ce + r'$', oldfile)
            if match:
                if self.verbose > 2:
                    msg = _("File '%s' seems to be compressed, skip it.") % (oldfile)
                    self.logger.debug(msg)
                continue

            if oldfile in self.files_delete:
                if self.verbose > 2:
                    msg = _("File '%s' will be deleted, compression unnecessary.") % (oldfile)
                    self.logger.debug(msg)
                continue

            if no_compress:
                if self.verbose > 2:
                    msg = _("Compression of file '%s' will be delayed.") % (oldfile)
                    self.logger.debug(msg)
                no_compress -= 1
                continue

            result.append(oldfile)

        if self.verbose > 3:
            if len(result):
                pp = pprint.PrettyPrinter(indent=4)
                msg = _("Found logfiles to compress:") + "\n" + pp.pformat(result)
                self.logger.debug(msg)
            else:
                msg = _("No old logfiles to compress found.")
                self.logger.debug(msg)
        return result

    #------------------------------------------------------------
    def _collect_files_delete(self, oldfiles, cur_desc_index):
        '''
        Collects a list with all old (and compressed) logfiles, they have to delete.

        @param oldfiles: a dict whith all found old logfiles as keys and
                        their modification time as values
        @type oldfiles:  dict
        @param cur_desc_index: index of self.config for definition
                               of logfile from configuration file
        @type cur_desc_index:  int

        @return: all old (and compressed) logfiles to delete
        @rtype:  list
        '''

        definition = self.config[cur_desc_index]
        _ = self.t.lgettext

        if self.verbose > 2:
            msg = _("Retrieving logfiles to delete ...")
            self.logger.debug(msg)

        result = []

        if not oldfiles.keys():
            if self.verbose > 3:
                msg = _("No old logfiles available.")
                self.logger.debug(msg)
            return result

        # Maxage in seconds or None
        maxage = definition['maxage']
        if maxage is None:
            if self.verbose >= 4:
                msg = _("No maxage given.")
                self.logger.debug(msg)
        else:
            maxage *= (24 * 60 * 60)
            if self.verbose >= 4:
                msg = _("Maxage: %d seconds") % (maxage)
                self.logger.debug(msg)

        # Number of rotations or Zero
        rotate = definition['rotate']
        if rotate is None:
            rotate = 0
        if self.verbose >= 4:
            msg = _("Max. count rotations: %d") % (rotate)
            self.logger.debug(msg)

        count = len(oldfiles.keys())
        for oldfile in sorted(oldfiles.keys(), key=lambda x: oldfiles[x]):
            count -= 1
            age = int(time.time() - oldfiles[oldfile])
            if self.verbose > 3:
                msg = _("Checking file '%s' for deleting ...") % (oldfile)
                self.logger.debug(msg)
            if self.verbose >= 4:
                msg = _("Current count: %(count)d, current age: %(age)d seconds") \
                        % {'count': count, 'age': age}
                self.logger.debug(msg)

            # Delete all files, their count is more than the rotate option
            if rotate:
                if count >= rotate:
                    if self.verbose >= 3:
                        msg = _("Deleting '%s' because of too much.") % (oldfile)
                        self.logger.debug(msg)
                    result.append(oldfile)
                    continue

            # Now checking for maximum age
            if maxage:
                if age >= maxage:
                    if self.verbose >= 3:
                        msg = _("Deleting '%s' because of too old.") % (oldfile)
                        self.logger.debug(msg)
                    result.append(oldfile)

        if self.verbose > 3:
            if len(result):
                pp = pprint.PrettyPrinter(indent=4)
                msg = _("Found logfiles to delete:") + "\n" + pp.pformat(result)
                self.logger.debug(msg)
            else:
                msg = _("No old logfiles to delete found.")
                self.logger.debug(msg)
        return result

    #------------------------------------------------------------
    def _collect_old_logfiles(self, logfile, extension, compress_extension, cur_desc_index):
        '''
        Collect all rotated versions of this logfile and gives back the
        information about.

        @param logfile: the logfile to rotate
        @type logfile:  str
        @param extension: additional fix file extension for rotated logfiles
        @type extension:  str
        @param compress_extension: file extension for rotated and
                                   compressed logfiles
        @type compress_extension:  str
        @param cur_desc_index: index of self.config for definition
                               of logfile from configuration file
        @type cur_desc_index:  int

        @return: all found old rotated logfiles as keys
                 and the last modification timestamp of these files as values
        @rtype:  dict
        '''

        definition = self.config[cur_desc_index]
        _ = self.t.lgettext

        if self.verbose > 2:
            msg = _("Retrieving all old logfiles for file '%s' ...") % (logfile)
            self.logger.debug(msg)

        result = {}

        basename = os.path.basename(logfile)
        dirname  = os.path.dirname(logfile)

        if definition['dateext']:
            basename += '.*'

        if definition['olddir']['dirname']:
            # Create a file pattern depending on olddir definition

            olddir = definition['olddir']['dirname']

            # Substitution of $dirname
            olddir = re.sub(r'(?:\${dirname}|\$dirname(?![a-zA-Z0-9_]))', dirname, olddir)

            # Substitution of $basename
            olddir = re.sub(r'(?:\${basename}|\$basename(?![a-zA-Z0-9_]))', basename, olddir)

            # Substitution of $nodename
            olddir = re.sub(r'(?:\${nodename}|\$nodename(?![a-zA-Z0-9_]))', self.template['nodename'], olddir)

            # Substitution of $domain
            olddir = re.sub(r'(?:\${domain}|\$domain(?![a-zA-Z0-9_]))', self.template['domain'], olddir)

            # Substitution of $machine
            olddir = re.sub(r'(?:\${machine}|\$machine(?![a-zA-Z0-9_]))', self.template['machine'], olddir)

            # Substitution of $release
            olddir = re.sub(r'(?:\${release}|\$release(?![a-zA-Z0-9_]))', self.template['release'], olddir)

            # Substitution of $sysname
            olddir = re.sub(r'(?:\${sysname}|\$sysname(?![a-zA-Z0-9_]))', self.template['sysname'], olddir)

            if not os.path.isabs(olddir):
                olddir = os.path.join(dirname, olddir)
            olddir = os.path.normpath(olddir)

            ####
            # Substituting all datetime.strftime() placeholders by shell pattern

            # weekday
            olddir = re.sub(r'%[aA]', '*', olddir)
            # name of month
            olddir = re.sub(r'%[bBh]', '*', olddir)
            # complete date
            olddir = re.sub(r'%c', '*', olddir)
            # century
            olddir = re.sub(r'%C', '[0-9][0-9]', olddir)
            # day of month
            olddir = re.sub(r'%d', '[0-9][0-9]', olddir)
            # date as %m/%d/%y
            olddir = re.sub(r'%[Dx]', '[0-9][0-9]/[0-9][0-9]/[0-9][0-9]', olddir)
            # Hour in 24-hours format
            olddir = re.sub(r'%H', '[012][0-9]', olddir)
            # Hour in 12-hours format
            olddir = re.sub(r'%J', '[01][0-9]', olddir)
            # number of month
            olddir = re.sub(r'%m', '[01][0-9]', olddir)
            # minute
            olddir = re.sub(r'%M', '[0-5][0-9]', olddir)
            # AM/PM
            olddir = re.sub(r'%p', '[AP]M', olddir)
            # complete time in 12-hours format with AM/PM
            olddir = re.sub(r'%r', '[01][0-9]:[0-5][0-9]:[0-5][0-9] [AP]M', olddir)
            # time in format %H:%M
            olddir = re.sub(r'%R', '[012][0-9]:[0-5][0-9]', olddir)
            # seconds
            olddir = re.sub(r'%S', '[0-5][0-9]', olddir)
            # complete time in 24-hours format
            olddir = re.sub(r'%[TX]', '[012][0-9]:[0-5][0-9]:[0-5][0-9]', olddir)
            # weekday as a number (0-7)
            olddir = re.sub(r'%[uw]', '[0-7]', olddir)
            # number of week in year (00-53)
            olddir = re.sub(r'%[UVW]', '[0-5][0-9]', olddir)
            # last two digits of the year
            olddir = re.sub(r'%y', '[0-9][0-9]', olddir)
            # year complete
            olddir = re.sub(r'%Y', '[12][0-9][0-9][0-9]', olddir)
            # time zone numeric
            olddir = re.sub(r'%z', '[-+][0-9][0-9][0-9][0-9]', olddir)
            # time zone name
            olddir = re.sub(r'%Z', '*', olddir)

            dirname = olddir

        # composing file pattern
        file_pattern = os.path.join(dirname, basename)
        pattern_list = []
        pattern_list.append(file_pattern + extension)
        pattern_list.append(file_pattern + '.[0-9]' + extension)
        pattern_list.append(file_pattern + '.[0-9][0-9]' + extension)
        pattern_list.append(file_pattern + '.[0-9][0-9][0-9]' + extension)
        pattern_list.append(file_pattern + '.[0-9][0-9][0-9][0-9]' + extension)
        pattern_list.append(file_pattern + '.[0-9][0-9][0-9][0-9][0-9]' + extension)

        if definition['compress']:
            ext = extension + compress_extension
            pattern_list.append(file_pattern + ext)
            pattern_list.append(file_pattern + '.[0-9]' + ext)
            pattern_list.append(file_pattern + '.[0-9][0-9]' + ext)
            pattern_list.append(file_pattern + '.[0-9][0-9][0-9]' + ext)
            pattern_list.append(file_pattern + '.[0-9][0-9][0-9][0-9]' + ext)
            pattern_list.append(file_pattern + '.[0-9][0-9][0-9][0-9][0-9]' + ext)

        for pattern in pattern_list:
            if self.verbose > 2:
                msg = _("Search for pattern '%s' ...") % (pattern)
                self.logger.debug(msg)
            found_files = glob.glob(pattern) 
            for oldfile in found_files:
                oldfile = os.path.abspath(oldfile)
                if oldfile == logfile:
                    continue
                statinfo = os.stat(oldfile)
                result[oldfile] = statinfo.st_mtime

        if self.verbose > 3:
            pp = pprint.PrettyPrinter(indent=4)
            msg = _("Found old logfiles:") + "\n" + pp.pformat(result)
            self.logger.debug(msg)
        return result

    #------------------------------------------------------------
    def _get_rotations(self, logfile, target, cur_desc_index):
        '''
        Retrieves all files to move and to rotate and gives them back
        as a dict.

        @param logfile: the logfile to rotate
        @type logfile:  str
        @param target:  name of the rotated logfile
        @type target:   str
        @param cur_desc_index: index of self.config for definition
                               of logfile from configuration file
        @type cur_desc_index:  int

        @return: dict in the form::
                    {
                        'compress_extension': '.gz',
                        'extension': '',
                        'rotate': {
                            'from': <file>,
                            'to': <target>
                        },
                        'move': [
                            ...
                            { 'from': <file2>, 'to': <file3>, 'compressed': True},
                            { 'from': <file1>, 'to': <file2>, 'compressed': True},
                            { 'from': <file0>, 'to': <file1>, 'compressed': False},
                        ],
                    }

                 the order in the list 'move' is the order, how the
                 files have to rename.
        @rtype: dict
        '''

        definition = self.config[cur_desc_index]
        _ = self.t.lgettext

        if self.verbose > 2:
            msg = _("Retrieving all movings and rotations for logfile '%(file)s' to target '%(target)s' ...") \
                    % {'file': logfile, 'target': target}
            self.logger.debug(msg)

        result = { 'rotate': {}, 'move': [] }

        # retrieve additional file extension of logfile after rotation
        # without compress extension
        extension = definition['extension']
        if extension is None:
            extension = ''
        match = re.search(r'^\s*$', extension)
        if match:
            extension = ''
        if extension != '':
            match = re.search(r'^\.', extension)
            if not match:
                extension = "." + extension
        result['extension'] = extension
        extension_wo_compress = extension

        # retrieve additional file extension of logfile after rotation
        # for compress extension
        compress_extension = ''
        if definition['compress']:
            compress_extension = definition['compressext']
            match = re.search(r'^\.', compress_extension)
            if not match:
                compress_extension = "." + compress_extension
        result['compress_extension'] = compress_extension

        # appending a trailing '.0', if there are no other differences
        # between logfile and target
        i = definition['start']
        if i is None:
            i = 0
        resulting_target = target + extension_wo_compress
        target_wo_number = resulting_target
        if resulting_target == logfile:
            resulting_target = resulting_target + "." + str(i)

        result['rotate']['from'] = logfile
        result['rotate']['to']   = resulting_target

        # resulting target exists, retrieve cyclic rotation
        if os.path.exists(resulting_target):
            if self.verbose > 3:
                msg = _("Resulting target '%s' exists, retrieve cyclic rotation ...") \
                        % (resulting_target)
                self.logger.debug(msg)
            target_wo_cext_old = target_wo_number + "." + str(i)
            target_with_cext_old = target_wo_cext_old + compress_extension
            while os.path.exists(target_wo_cext_old) or os.path.exists(target_with_cext_old):
                i += 1
                target_wo_cext_new = target_wo_number + "." + str(i)
                target_with_cext_new = target_wo_cext_new + compress_extension
                if self.verbose > 4:
                    msg = _("Cyclic rotation from '%(from)s' to '%(to)s'.") \
                            % {'from': target_wo_cext_old, 'to': target_wo_cext_new}
                    self.logger.debug(msg)
                pair = {
                    'from': target_wo_cext_old,
                    'to': target_wo_cext_new,
                    'compressed': False,
                }
                if definition['compress']:
                    if os.path.exists(target_with_cext_old):
                        pair['compressed'] = True
                result['move'].insert(0, pair)
                target_wo_cext_old = target_wo_cext_new
                target_with_cext_old = target_with_cext_new

        if self.verbose > 3:
            pp = pprint.PrettyPrinter(indent=4)
            msg = _("Found rotations:") + "\n" + pp.pformat(result)
            self.logger.debug(msg)
        return result

    #------------------------------------------------------------
    def _get_rotation_target(self, logfile, cur_desc_index, olddir = None):
        '''
        Retrieves the name of the rotated logfile and gives it back.

        @param logfile: the logfile to rotate
        @type logfile:  str
        @param cur_desc_index: index of self.config for definition
                               of logfile from configuration file
        @type cur_desc_index:  int
        @param olddir: the directory of the rotated logfile
                       if None, store the rotated logfile
                       in their original directory
        @type olddir: str or None

        @return: name of the rotated logfile
        @rtype:  str
        '''

        definition = self.config[cur_desc_index]

        _ = self.t.lgettext

        if self.verbose > 2:
            msg = _("Retrieving the name of the rotated file of '%s' ...") % (logfile)
            self.logger.debug(msg)

        target = logfile
        if olddir is not None:
            basename = os.path.basename(logfile)
            target = os.path.join(olddir, basename)

        if definition['dateext']:
            pattern = definition['datepattern']
            if pattern is None:
                pattern = '%Y-%m-%d'
            dateext = datetime.utcnow().strftime(pattern)
            if self.verbose > 3:
                msg = _("Using date extension '.%(ext)s' from pattern '%(pattern)s'.") \
                        % {'ext': dateext, 'pattern': pattern}
                self.logger.debug(msg)
            target += "." + dateext

        if self.verbose > 1:
            msg = _("Using '%(target)s' as target for rotation of logfile '%(logfile)s'.") \
                    % {'target': target, 'logfile': logfile}
            self.logger.debug(msg)
        return target

    #------------------------------------------------------------
    def _create_olddir(self, logfile, cur_desc_index):
        '''
        Creating the olddir, if necessary.

        @param logfile: the logfile to rotate
        @type logfile:  str
        @param cur_desc_index: index of self.config for definition
                               of logfile from configuration file
        @type cur_desc_index:  int

        @return: Name of the retrieved olddir, ".", if storing
                 the rotated logfiles in their original directory or
                 None in case of some minor errors (olddir couldn't
                 created a.s.o.)
        @rtype:  str or None
        '''

        definition = self.config[cur_desc_index]

        _ = self.t.lgettext

        uid = os.geteuid()
        gid = os.getegid()

        o = definition['olddir']
        if not o['dirname']:
            if self.verbose > 1:
                msg = _("No dirname directive for olddir given.")
                self.logger.debug(msg)
            return "."
        olddir = o['dirname']

        mode = o['mode']
        if mode is None:
            mode = int('0755', 8)
        owner = o['owner']
        if not owner:
            owner = uid
        group = o['group']
        if not group:
            group = gid

        basename = os.path.basename(logfile)
        dirname  = os.path.dirname(logfile)

        match = re.search(r'%', olddir)
        if match:
            o['dateformat'] = True
            olddir = datetime.utcnow().strftime(olddir)

        # Substitution of $dirname
        olddir = re.sub(r'(?:\${dirname}|\$dirname(?![a-zA-Z0-9_]))', dirname, olddir)

        # Substitution of $basename
        olddir = re.sub(r'(?:\${basename}|\$basename(?![a-zA-Z0-9_]))', basename, olddir)

        # Substitution of $nodename
        olddir = re.sub(r'(?:\${nodename}|\$nodename(?![a-zA-Z0-9_]))', self.template['nodename'], olddir)

        # Substitution of $domain
        olddir = re.sub(r'(?:\${domain}|\$domain(?![a-zA-Z0-9_]))', self.template['domain'], olddir)

        # Substitution of $machine
        olddir = re.sub(r'(?:\${machine}|\$machine(?![a-zA-Z0-9_]))', self.template['machine'], olddir)

        # Substitution of $release
        olddir = re.sub(r'(?:\${release}|\$release(?![a-zA-Z0-9_]))', self.template['release'], olddir)

        # Substitution of $sysname
        olddir = re.sub(r'(?:\${sysname}|\$sysname(?![a-zA-Z0-9_]))', self.template['sysname'], olddir)

        if not os.path.isabs(olddir):
            olddir = os.path.join(dirname, olddir)
        olddir = os.path.normpath(olddir)

        if self.verbose > 1:
            msg = _("Olddir name is now '%s'") % (olddir)
            self.logger.debug(msg)

        # Check for Existence and Consistence
        if os.path.exists(olddir):
            if os.path.isdir(olddir):
                if os.access(olddir, (os.W_OK | os.X_OK)):
                    if self.verbose > 2:
                        msg = _("Olddir '%s' allready exists, not created.") % (olddir)
                        self.logger.debug(msg)
                    olddir = os.path.realpath(olddir)
                    return olddir
                else:
                    msg = _("No write and execute access to olddir '%s'.") % (olddir)
                    if self.test:
                        self.logger.warning(msg)
                        return olddir
                    raise LogrotateHandlerError(msg)
                    return None
            else:
                msg = _("Olddir '%s' exists, but is not a valid directory.") % (olddir)
                raise LogrotateHandlerError(msg)
                return None

        dirs = []
        dir_head = olddir
        while dir_head != os.sep:
            (dir_head, dir_tail) = os.path.split(dir_head)
            dirs.insert(0, dir_tail)
        if self.verbose > 2:
            msg = _("Directory chain to create: '%s'") % (str(dirs))
            self.logger.debug(msg)

        # Create olddir recursive, if necessary
        msg = _("Creating olddir '%s' recursive ...") % (olddir)
        self.logger.info(msg)
        create_dir = None
        parent_statinfo = os.stat(os.sep)
        parent_mode = parent_statinfo.st_mode
        parent_uid  = parent_statinfo.st_uid
        parent_gid  = parent_statinfo.st_gid
        while len(dirs):
            dir_head = dirs.pop(0)
            if create_dir:
                create_dir = os.path.join(create_dir, dir_head)
            else:
                create_dir = os.sep + dir_head
            if self.verbose > 3:
                msg = _("Try to create directory '%s' ...") % (create_dir)
                self.logger.debug(msg)
            if os.path.exists(create_dir):
                if os.path.isdir(create_dir):
                    if self.verbose > 3:
                        msg = _("Directory '%s' allready exists, not created.") % (create_dir)
                        self.logger.debug(msg)
                    parent_statinfo = os.stat(create_dir)
                    parent_mode = parent_statinfo.st_mode
                    parent_uid  = parent_statinfo.st_uid
                    parent_gid  = parent_statinfo.st_gid
                    continue
                else:
                    msg = _("Directory '%s' exists, but is not a valid directory.") % (create_dir)
                    self.logger.error(msg)
                    return None
            msg = _("Creating directory '%s' ...") % (create_dir)
            self.logger.debug(msg)
            create_mode = parent_mode
            if o['mode'] is not None:
                create_mode = o['mode']
            create_uid = parent_uid
            if o['owner'] is not None:
                create_uid = o['owner']
            create_gid = parent_gid
            if o['group'] is not None:
                create_gid = o['group']
            if self.verbose > 1:
                msg = _("Create permissions: %(mode)4o, Owner-UID: %(uid)d, Group-GID: %(gid)d") \
                        % {'mode': create_mode, 'uid': create_uid, 'gid': create_gid}
                self.logger.debug(msg)
            if not self.test:
                if self.verbose > 2:
                    msg = "os.mkdir('%s', %4o)" % (create_dir, create_mode)
                    self.logger.debug(msg)
                try:
                    os.mkdir(create_dir, create_mode)
                except OSError, e:
                    msg = _("Error on creating directory '%(dir)s': %(err)s") \
                            % {'dir': create_dir, 'err': e.strerror}
                    self.logger.error(msg)
                    return None
                if (create_uid != uid) or (create_gid != gid):
                    if self.verbose > 2:
                        msg = "os.chown('%s', %d, %d)" % (create_dir, create_uid, create_gid)
                        self.logger.debug(msg)
                    try:
                        os.chown(create_dir, create_uid, create_gid)
                    except OSError, e:
                        msg = _("Error on chowning directory '%(dir)s': %(err)s") \
                                % {'dir': create_dir, 'err': e.strerror}
                        self.logger.error(msg)
                        return None

        olddir = os.path.realpath(olddir)
        return olddir

    #------------------------------------------------------------
    def _execute_command(self, command, force=False, expected_retcode=0):
        '''
        Executes the given command as an OS command in a shell.

        @param command: the command to execute
        @type command:  str
        @param force:   force executing command even if self.test == True
        @type force:    bool
        @param expected_retcode: expected returncode of the command
                                 (should be 0)
        @type expected_retcode:  int

        @return: Success of the comand (shell returncode == 0)
        @rtype:  bool
        '''

        _ = self.t.lgettext
        if self.verbose > 3:
            msg = _("Executing command: '%s'") % (command)
            self.logger.debug(msg)
        if not force:
            if self.test:
                return True
        try:
            retcode = subprocess.call(command, shell=True)
            if self.verbose > 3:
                msg = _("Got returncode: '%s'") % (retcode)
                self.logger.debug(msg)
            if retcode < 0:
                msg = _("Child was terminated by signal %d") % (-retcode)
                self.logger.error(msg)
                return False
            if retcode != expected_retcode:
                return False
            return True
        except OSError, e:
            msg = _("Execution failed: %s") % (str(e))
            self.logger.error(msg)
            return False

        return False

    #------------------------------------------------------------
    def _should_rotate(self, logfile, cur_desc_index):
        '''
        Determines, whether a logfile should rotated dependend on
        the informations in the definition.

        Throughs an LogrotateHandlerError on harder errors.

        @param logfile: the logfile to inspect
        @type logfile:  str
        @param cur_desc_index: index of self.config for definition
                               of logfile from configuration file
        @type cur_desc_index:  int

        @return: to rotate or not
        @rtype:  bool
        '''

        definition = self.config[cur_desc_index]

        _ = self.t.lgettext

        if self.verbose > 2:
            msg = _("Check, whether logfile '%s' should rotated.") % (logfile)
            self.logger.debug(msg)

        if not os.path.exists(logfile):
            msg = _("logfile '%s' doesn't exists, not rotated") % (logfile)
            if not definition['missingok']:
                self.logger.error(msg)
            else:
                if self.verbose > 1:
                    self.logger.debug(msg)
            return False

        if not os.path.isfile(logfile):
            msg = _("logfile '%s' is not a regular file, not rotated") % (logfile)
            self.logger.warning(msg)
            return False

        filesize = os.path.getsize(logfile)
        if self.verbose > 2:
            msg = _("Filesize of '%(file)s': %(size)d") % {'file': logfile, 'size': filesize}
            self.logger.debug(msg)

        if not filesize:
            if not definition['ifempty']:
                if self.verbose > 1:
                    msg = _("Logfile '%s' has a filesize of Zero, not rotated") % (logfile)
                    self.logger.debug(msg)
                return False

        if self.force:
            if self.verbose > 1:
                msg = _("Rotating of '%s' because of force mode.") % (logfile)
                self.logger.debug(msg)
            return True

        maxsize = definition['size']
        if maxsize is None:
            maxsize = 0

        last_rotated = self.state_file.get_rotation_date(logfile)
        if self.verbose > 2:
            msg = _("Date of last rotation: %s") %(last_rotated.isoformat(' '))
            self.logger.debug(msg)
        next_rotation = last_rotated + timedelta(days = definition['period'])
        if self.verbose > 2:
            msg = _("Date of next rotation: %s") %(next_rotation.isoformat(' '))
            self.logger.debug(msg)

        if filesize < maxsize:
            if self.verbose > 1:
                msg = _("Filesize %(filesize)d is less than %(maxsize)d, rotation not necessary.") \
                        % {'filesize': filesize, 'maxsize': maxsize}
                self.logger.debug(msg)
            return False

        curdate = datetime.utcnow().replace(tzinfo = utc)
        if next_rotation > curdate:
            if self.verbose > 1:
                msg = _("Date of next rotation '%(next)s' is in future, rotation not necessary.") \
                        % {'next': next_rotation.isoformat(' ')}
                self.logger.debug(msg)
            return False

        return True

    #------------------------------------------------------------
    def delete_oldfiles(self):
        '''
        Deleting of all logfiles in self.files_delete

        @return: None
        '''

        _ = self.t.lgettext

        msg = _("Deletion of all superfluid logfiles ...")
        self.logger.debug(msg)

        if not len(self.files_delete.keys()):
            msg = _("No logfiles to delete found.")
            self.logger.info(msg)

        for logfile in sorted(self.files_delete.keys(), key=str.lower):
            msg = _("Deleting file '%s' ...") % (logfile)
            self.logger.info(msg)
            if not self.test:
                try:
                    os.remove(logfile)
                except OSError, e:
                    msg = _("Error on removing file '%(file)s': %(err)s") \
                            % {'file': logfile, 'err': e.strerror}
                    self.logger.error(msg)

        return

    #------------------------------------------------------------
    def compress(self):
        '''
        Compressing all logfiles in self.files_compress

        @return: None
        '''

        _ = self.t.lgettext

        msg = _("Compression of all uncompressed logfiles ...")
        self.logger.debug(msg)

        if not len(self.files_compress.keys()):
            msg = _("No logfiles to compress found.")
            self.logger.info(msg)

        for logfile in sorted(self.files_compress.keys(), key=str.lower):

            cur_desc_index = self.files_compress[logfile]
            definition = self.config[cur_desc_index]
            command = definition['compresscmd']
            compress_extension = definition['compressext']
            compress_opts = definition['compressoptions']

            match = re.search(r'^\.', compress_extension)
            if not match:
                compress_extension = "." + compress_extension
            target = logfile + compress_extension

            # Check existence source logfile
            if not os.path.exists(logfile):
                msg = _("Source file '%s' for compression doesn't exists.") % (logfile)
                raise LogrotateHandlerError(msg)
                return

            # Check existence target (compressed file)
            if os.path.exists(target):
                if os.path.samefile(logfile, target):
                    msg = _("Source file '%(source)s' and target file '%(target)s' are the same file.") \
                            % {'source': logfile, 'target': target}
                    raise LogrotateHandlerError(msg)
                    return
                msg = _("Target file '%s' for compression allready exists.") %(target)
                self.logger.warning(msg)

            # Check for filesize Zero => not compressed
            filesize = os.path.getsize(logfile)
            if filesize <= 0:
                msg = _("File '%s' has a size of 0, skip compressing.") % (logfile)
                self.logger.info(msg)
                continue

            # Execute compressing ...
            msg = _("Compressing file '%(file)s' to '%(target)s' with '%(cmd)s' ...") \
                    % {'file': logfile, 'target': target, 'cmd': command}
            self.logger.info(msg)

            if command == 'internal_gzip':
                self._compress_internal_gzip(logfile, target)
            elif command == 'internal_bzip2':
                self._compress_internal_bzip2(logfile, target)
            elif command == 'internal_zip':
                self._compress_internal_zip(logfile, target)
            else:
                self._compress_external(logfile, target, command, compress_opts)

        return

    #------------------------------------------------------------
    def _compress_external(self, source, target, command, options):
        '''
        Compression of the given source file to the target file
        with an external command.

        It raises a LogrotateHandlerError on uncoverable errors.

        @param source: the source file to compress
        @type source:  str
        @param target: the filename of the compressed file.
        @type target:  str
        @param command: the OS command to use to compress
        @type command:  str
        @param options: additional options to the compress command
                        possible placeholders inside the options:
                            - {}: placeholder for sourcefile
                            - []: placeholder for targetfile
        @type options:  str

        @return: success or not
        @rtype:  bool
        '''

        _ = self.t.lgettext

        test_mode = self.test
        test_mode = False

        if self.verbose > 1:
            msg = _("Compressing source '%(source)s' to target'%(target)s' with command '%(cmd)s'.") \
                    % {'source': source, 'target': target, 'cmd': command}
            self.logger.debug(msg)

        if options is None:
            options = ''

        # substituting [] in compressoptions with qouted target file name
        match = re.search(r'\[\]', options)
        if match:
            if self.verbose > 3:
                msg = _("Substituting '[]' in compressoptions with '%s'.") % ('"' + target + '"')
                self.logger.debug(msg)
            options = re.sub(r'\[\]', '"' + target + '"', options)

        # substituting or trailing command with quoted source file name
        match = re.search(r'\{\}', options)
        if match:
            if self.verbose > 3:
                msg = _("Substituting '{}' in compressoptions with '%s'.") % ('"' + source + '"')
                self.logger.debug(msg)
            options = re.sub(r'\{\}', '"' + source + '"', options)
        else:
            options += ' "' + source + '"'

        if self.verbose > 2:
            msg = _("Compress options: '%s'.") % (options)
            self.logger.debug(msg)

        cmd = command + ' ' + options

        src_statinfo = os.stat(source)

        if not self._execute_command(cmd):
            return False

        if not self.test:
            if not os.path.exists(target):
                msg = _("Target '%s' of compression doesn't exists after executing compression command.") \
                        % (target)
                self.logger.error(msg)
                return False

        if os.path.exists(source):

            self._copy_file_metadata(source=source, target=target)

            # And last, but not least, delete uncompressed file
            if self.verbose > 1:
                msg = _("Deleting uncompressed file '%s' ...") % (source)
                self.logger.debug(msg)

            if not self.test:
                try:
                    os.remove(source)
                except OSError, e:
                    msg = _("Error removing uncompressed file '%(file)s': %(msg)") \
                            % {'file': source, 'msg': str(e) }
                    self.logger.error(msg)
                    return False

        else:

            self._copy_file_metadata(target=target, statinfo=src_statinfo)

        return True
    #------------------------------------------------------------
    def _copy_file_metadata(self, target, source=None, statinfo=None):
        '''
        Copy all metadata (owner, permissions, timestamps a.s.o) from
        a source file onto a target file.
        The target file must be exists.
        Either an existing source file (parameter 'source') or the
        statinfo of a former existing file (parameter 'statinfo') must
        be given.

        It raises a LogrotateHandlerError on uncoverable errors.

        @param target: filename of an existing target file or directory
        @type target:  str
        @param source: filename of an existing source file or directory
                       or None, if statinfo was given,
                       has precedence before a given statinfo
        @type source:  str or None
        @param statinfo: stat object from os.stat() or None, if source was given
        @type statinfo:  stat-object or None

        @return: success or not
        @rtype:  bool
        '''

        _ = self.t.lgettext

        if source is None and statinfo is None:
            msg = _("Neither 'target' nor 'statinfo' was given on calling _copy_file_metadata().")
            raise LogrotateHandlerError(msg)
            return False

        if not os.path.exists(target):
            msg = _("File or directory '%s' doesn't exists.") % (target)
            if self.test:
                self.logger.info(msg)
                return True
            self.logger.error(msg)
            return False

        new_statinfo = statinfo
        old_statinfo = os.stat(target)

        msg = _("Copying all file metadata to target '%s' ...") % (target)
        self.logger.info(msg)

        if source is not None:

            # a source object was given

            if not os.path.exists(source):
                msg = _("File or directory '%s' doesn't exists.") % (source)
                self.logger.error(msg)
                return False

            new_statinfo = os.stat(source)

            # Copying permissions and timestamps from source to target
            if self.verbose > 1:
                msg = _("Copying permissions and timestamps from source '%(src)s' to target '%(target)s'.") \
                        % {'src': source, 'target': target}
                self.logger.debug(msg)
            if not self.test:
                shutil.copystat(source, target)

        else:

            # a source statinfo was given

            atime = new_statinfo.st_atime
            mtime = new_statinfo.st_mtime
            mode  = new_statinfo.st_mode

            # Setting atime and mtime
            if self.verbose > 1:
                msg = _("Setting atime and mtime of target '%s'.") % (target)
                self.logger.debug(msg)
            if not self.test:
                try:
                    os.utime(target, (atime, mtime))
                except OSError, e:
                    msg = _("Error on setting times on target file '%(target)s': %(err)s") \
                            % {'target': target, 'err': e.strerror}
                    self.logger.warning(msg)
                    return False

            # Setting permissions
            old_mode = old_statinfo.st_mode
            if mode != old_mode:
                if self.verbose > 1:
                    msg = _("Setting permissions of '%(target)s' to %(mode)4o.") \
                            % {'target': target, 'mode': new_mode}
                    self.logger.info(msg)
                if not self.test:
                    try:
                        os.chmod(target, mode)
                    except OSError, e:
                        msg = _("Error on chmod of '%(target)s': %(err)s") \
                                % {'target': target, 'err': e.strerror}
                        self.logger.warning(msg)
                        return False

        # Copying ownership from source to target
        new_uid = new_statinfo.st_uid
        new_gid = new_statinfo.st_gid
        old_uid = old_statinfo.st_uid
        old_gid = old_statinfo.st_gid

        if (old_uid != new_uid) or (old_gid != new_gid):
            if self.verbose > 1:
                msg = _("Copying ownership from source to target.")
                self.logger.debug(msg)
            myuid = os.geteuid()
            if myuid != 0:
                msg = _("Only root may execute chown().")
                if self.test:
                    self.logger.info(msg)
                    return True
                else:
                    self.logger.warning(msg)
                    return False
            if not self.test:
                try:
                    os.chown(target, old_uid, old_gid)
                except OSError, e:
                    msg = _("Error on chown of '%(file)s': %(err)s") \
                            % {'file': target, 'err': e.strerror}
                    self.logger.warning(msg)
                    return False

        return True

    #------------------------------------------------------------
    def _compress_internal_zip(self, source, target):
        '''
        Compression of the given source file to the target file
        with the Python module zipfile.

        It raises a LogrotateHandlerError on some errors.

        @param source: the source file to compress
        @type source:  str
        @param target: the filename of the compressed file.
        @type target:  str

        @return: success or not
        @rtype:  bool
        '''

        _ = self.t.lgettext

        if self.verbose > 1:
            msg = _("Compressing source '%(source)s' to target'%(target)s' with module zipfile.") \
                    % {'source': source, 'target': target}
            self.logger.debug(msg)

        if not self.test:

            # open target for writing
            f_out = None
            try:
                f_out = zipfile.ZipFile(
                            file=target,
                            mode='w',
                            compression=zipfile.ZIP_DEFLATED
                )
            except IOError, e:
                msg = _("Error on open file '%(file)s' on writing: %(err)s") \
                        % {'file': target, 'err': str(e)}
                self.logger.error(msg)
                return False

            basename = os.path.basename(source)
            f_out.write(source, basename)
            f_out.close()

        self._copy_file_metadata(source=source, target=target)

        # And last, but not least, delete uncompressed file
        if self.verbose > 1:
            msg = _("Deleting uncompressed file '%s' ...") % (source)
            self.logger.debug(msg)

        if not self.test:
            try:
                os.remove(source)
            except OSError, e:
                msg = _("Error removing uncompressed file '%(file)s': %(msg)") \
                        % {'file': source, 'msg': str(e) }
                self.logger.error(msg)
                return False

        return True

    #------------------------------------------------------------
    def _compress_internal_gzip(self, source, target):
        '''
        Compression of the given source file to the target file
        with the Python module gzip.
        As compression level is allways used 9 (highest compression).

        It raises a LogrotateHandlerError on some errors.

        @param source: the source file to compress
        @type source:  str
        @param target: the filename of the compressed file.
        @type target:  str

        @return: success or not
        @rtype:  bool
        '''

        _ = self.t.lgettext

        test_mode = self.test

        if self.verbose > 1:
            msg = _("Compressing source '%(source)s' to target'%(target)s' with module gzip.") \
                    % {'source': source, 'target': target}
            self.logger.debug(msg)

        if not test_mode:
            # open source for reading
            f_in = None
            try:
                f_in = open(source, 'rb')
            except IOError, e:
                msg = _("Error on open file '%(file)s' on reading: %(err)s") \
                        % {'file': source, 'err': str(e)}
                self.logger.error(msg)
                return False

            # open target for writing
            f_out = None
            try:
                f_out = gzip.open(target, 'wb')
            except IOError, e:
                msg = _("Error on open file '%(file)s' on writing: %(err)s") \
                        % {'file': target, 'err': str(e)}
                self.logger.error(msg)
                f_in.close()
                return False

            # compress and write target
            f_out.writelines(f_in)
            # close both files
            f_out.close()
            f_in.close()

        self._copy_file_metadata(source=source, target=target)

        # And last, but not least, delete uncompressed file
        if self.verbose > 1:
            msg = _("Deleting uncompressed file '%s' ...") % (source)
            self.logger.debug(msg)

        if not self.test:
            try:
                os.remove(source)
            except OSError, e:
                msg = _("Error removing uncompressed file '%(file)s': %(msg)") \
                        % {'file': source, 'msg': str(e) }
                self.logger.error(msg)
                return False

        return True

    #------------------------------------------------------------
    def _compress_internal_bzip2(self, source, target):
        '''
        Compression of the given source file to the target file
        with the Python module bz2.
        As compression level is allways used 9 (highest compression).

        It raises a LogrotateHandlerError on some errors.

        @param source: the source file to compress
        @type source:  str
        @param target: the filename of the compressed file.
        @type target:  str

        @return: success or not
        @rtype:  bool
        '''

        _ = self.t.lgettext

        test_mode = self.test

        if self.verbose > 1:
            msg = _("Compressing source '%(source)s' to target'%(target)s' with module bz2.") \
                    % {'source': source, 'target': target}
            self.logger.debug(msg)

        if not test_mode:
            # open source for reading
            f_in = None
            try:
                f_in = open(source, 'rb')
            except IOError, e:
                msg = _("Error on open file '%(file)s' on reading: %(err)s") \
                        % {'file': source, 'err': str(e)}
                self.logger.error(msg)
                return False

            # open target for writing
            f_out = None
            try:
                f_out = bz2.BZ2File(target, 'w')
            except IOError, e:
                msg = _("Error on open file '%(file)s' on writing: %(err)s") \
                        % {'file': target, 'err': str(e)}
                self.logger.error(msg)
                f_in.close()
                return False

            # compress and write target
            f_out.writelines(f_in)
            # close both files
            f_out.close()
            f_in.close()

        self._copy_file_metadata(source=source, target=target)

        # And last, but not least, delete uncompressed file
        if self.verbose > 1:
            msg = _("Deleting uncompressed file '%s' ...") % (source)
            self.logger.debug(msg)

        if not self.test:
            try:
                os.remove(source)
            except OSError, e:
                msg = _("Error removing uncompressed file '%(file)s': %(msg)") \
                        % {'file': source, 'msg': str(e) }
                self.logger.error(msg)
                return False

        return True

#========================================================================

if __name__ == "__main__":
    pass


#========================================================================

# vim: fileencoding=utf-8 filetype=python ts=4 expandtab
