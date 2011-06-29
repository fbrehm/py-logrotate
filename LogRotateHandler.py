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
import subprocess
from datetime import datetime, timedelta

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
__version__    = '0.3.0 ' + revision
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

        # create formatter
        formatter = logging.Formatter('[%(asctime)s]: %(name)s %(levelname)-8s'
                                        + ' - %(message)s')
        if verbose > 1:
            formatter = logging.Formatter('[%(asctime)s]: %(name)s %(levelname)-8s'
                                           + '%(funcName)s() - %(message)s')

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

        for definition in self.config:
            self._rotate_definition(definition)

        return

    #------------------------------------------------------------
    def _rotate_definition(self, definition):
        '''
        Rotation of a logfile definition from a configuration file.

        @param definition: definitions from configuration file
        @type definition:  dict

        @return: None
        '''

        _ = self.t.lgettext

        if self.verbose >= 4:
            pp = pprint.PrettyPrinter(indent=4)
            msg = _("Rotating of logfile definition:") + \
                    "\n" + pp.pformat(definition)
            self.logger.debug(msg)

        for logfile in definition['files']:
            if self.verbose > 1:
                msg = ( _("Performing logfile '%s' ...") % (logfile)) + "\n"
                self.logger.debug(msg)
            should_rotate = self._should_rotate(logfile, definition)
            if self.verbose > 1:
                if should_rotate:
                    msg = _("logfile '%s' WILL rotated.")
                else:
                    msg = _("logfile '%s' will NOT rotated.")
                self.logger.debug(msg % (logfile))
            if not should_rotate:
                continue
            self._rotate_file(logfile, definition)

        return

    #------------------------------------------------------------
    def _rotate_file(self, logfile, definition):
        '''
        Rotates a logfile with all with all necessary actions before
        and after rotation.

        Throughs an LogrotateHandlerError on error.

        @param logfile: the logfile to rotate
        @type logfile:  str
        @param definition: definitions from configuration file
        @type definition:  dict

        @return: None
        '''

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
            if not self.scripts[firstscript]['first']:
                msg = _("Executing firstaction script '%s' ...") % (firstscript)
                self.logger.info(msg)
                if not self.test:
                    cmd = '\n'.join(self.scripts[firstscript]['cmd'])
                    if not self._execute_command(cmd):
                        return
                self.scripts[firstscript]['first'] = True

        # Executing prerotate scripts ...
        # bla bla bla 

        if not self._create_olddir(logfile, definition):
            return

    #------------------------------------------------------------
    def _create_olddir(self, logfile, definition):
        '''
        Creating the olddir, if necessary.

        @param logfile: the logfile to rotate
        @type logfile:  str
        @param definition: definitions from configuration file (for olddir)
        @type definition:  dict

        @return: successful or not
        @rtype:  bool
        '''

        _ = self.t.lgettext

        uid = os.geteuid()
        gid = os.getegid()

        o = definition['olddir']
        if not o['dirname']:
            if self.verbose > 1:
                msg = _("No dirname directive for olddir given.")
                self.logger.debug(msg)
            return True
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
                    return True
                else:
                    msg = _("No write and execute access to olddir '%s'.") % (olddir)
                    raise LogrotateHandlerError(msg)
                    return False
            else:
                msg = _("Olddir '%s' exists, but is not a valid directory.") % (olddir)
                raise LogrotateHandlerError(msg)
                return False

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
                    return False
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
                    return False
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
                        return False

        return True

    #------------------------------------------------------------
    def _execute_command(self, command):
        '''
        Executes the given command as an OS command in a shell.

        @param command: the command to execute
        @type command:  str

        @return: Success of the comand (shell returncode == 0)
        @rtype:  bool
        '''

        _ = self.t.lgettext
        if self.verbose > 3:
            msg = _("Executing command: '%s'") % (command)
            self.logger.debug(msg)
        try:
            retcode = subprocess.call(command, shell=True)
            if self.verbose > 3:
                msg = _("Got returncode: '%s'") % (retcode)
                self.logger.debug(msg)
            if retcode < 0:
                msg = _("Child was terminated by signal %d") % (-retcode)
                self.logger.error(msg)
                return False
            if retcode > 0:
                return False
            return True
        except OSError, e:
            msg = _("Execution failed: %s") % (str(e))
            self.logger.error(msg)
            return False

        return False

    #------------------------------------------------------------
    def _should_rotate(self, logfile, definition):
        '''
        Determines, whether a logfile should rotated dependend on
        the informations in the definition.

        Throughs an LogrotateHandlerError on harder errors.

        @param logfile: the logfile to inspect
        @type logfile:  str
        @param definition: definitions from configuration file
        @type definition:  dict

        @return: to rotate or not
        @rtype:  bool
        '''

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
        pass

    #------------------------------------------------------------
    def compress(self):
        pass

#========================================================================

if __name__ == "__main__":
    pass


#========================================================================

# vim: fileencoding=utf-8 filetype=python ts=4 expandtab
