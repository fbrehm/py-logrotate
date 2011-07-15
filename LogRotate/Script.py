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
@summary: module for a logrotate script object
	  (for pre- and postrotate actions)
'''

# Standard modules
import re
import logging
import subprocess
import pprint
import gettext

# Third party modules

# Own modules

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

class LogRotateScriptError(Exception):
    '''
    Base class for exceptions in this module.
    '''

#========================================================================

class LogRotateScript(object):
    '''
    Class for encapsulating a logrotate script
    (for pre- and postrotate actions)

    @author: Frank Brehm
    @contact: frank@brehm-online.com
    '''

    #-------------------------------------------------------
    def __init__( self, name,
                        local_dir = None,
                        verbose   = 0,
                        test_mode = False,
    ):
        '''
        Constructor.

        @param name:      the name of the script as an identifier
        @type name:       str
        @param local_dir: The directory, where the i18n-files (*.mo)
                          are located. If None, then system default
                          (/usr/share/locale) is used.
        @type local_dir:  str or None
        @param verbose:   verbosity (debug) level
        @type verbose:    int
        @param test_mode: test mode - no write actions are made
        @type test_mode:  bool

        @return: None
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

        self.verbose = verbose
        '''
        @ivar: verbosity level (0 - 9)
        @type: int
        '''

        self._name = name
        '''
        @ivar: the name of the script as an identifier
        @type: str
        '''

        self.test_mode = test_mode
        '''
        @ivar: test mode - no write actions are made
        @type: bool
        '''

        self.logger = logging.getLogger('pylogrotate.script')
        '''
        @ivar: logger object
        @type: logging.getLogger
        '''

        self._cmd = []
        '''
        @ivar: List of commands to execute
        @type: list
        '''

        self._post_files = 0
        '''
        @ivar: Number of logfiles referencing to this script
               as a postrotate script
        @type: int
        '''

        self._last_files = 0
        '''
        @ivar: Number of logfiles referencing to this script
               as a lastaction script
        @type: int
        '''

        self._done_firstrun = False
        '''
        @ivar: Flag, whether the script was executed as
               a firstaction script
        @type: bool
        '''

        self._done_prerun = False
        '''
        @ivar: Flag, whether the script was executed as
               a prerun script
        @type: bool
        '''

        self._done_postrun = False
        '''
        @ivar: Flag, whether the script was executed as
               a postrun script
        @type: bool
        '''

        self._done_lastrun = False
        '''
        @ivar: Flag, whether the script was executed as
               a lastaction script
        @type: bool
        '''

        self._do_post = False
        '''
        Runtime flag, that the script should be executed
        as an postrun script
        '''

        self._do_last = False
        '''
        Runtime flag, that the script should be executed
        as an lastaction script
        '''

    #------------------------------------------------------------
    # Defintion of some properties

    #------------------------------------------------------------
    # Property 'name'
    def _get_name(self):
        '''
        Getter method for property 'name'
        '''
        return self._name

    name = property(_get_name, None, None, "Name of the script as an identifier")

    #------------------------------------------------------------
    # Property 'cmd'
    def _get_cmd(self):
        '''
        Getter method for property 'cmd'
        '''
        if len(self._cmd):
            return "\n".join(self._cmd)
        else:
            return None

    def _set_cmd(self, value):
        '''
        Setter method for property 'cmd'
        '''
        if value:
            if isinstance(value, list):
                self._cmd = value[:]
            else:
                self._cmd = [value]
        else:
            self._cmd = []

    def _del_cmd(self):
        '''
        Deleter method for property 'cmd'
        '''
        self._cmd = []

    cmd = property(_get_cmd, _set_cmd, _del_cmd, "the commands to execute")

    #------------------------------------------------------------
    # Property 'post_files'
    def _get_post_files(self):
        '''
        Getter method for property 'post_files'
        '''
        return self._post_files

    def _set_post_files(self, value):
        '''
        Setter method for property 'post_files'
        '''
        _ = self.t.lgettext
        if isinstance(value, int):
            self._post_files = value
        else:
            msg = _("Invalid value for property '%s' given.") % ('post_files')
            raise LogRotateScriptError(msg)

    post_files = property(
                    _get_post_files,
                    _set_post_files,
                    None,
                    "Number of logfiles referencing to this script as a postrotate script."
    )

    #------------------------------------------------------------
    # Property 'last_files'
    def _get_last_files(self):
        '''
        Getter method for property 'last_files'
        '''
        return self._last_files

    def _set_last_files(self, value):
        '''
        Setter method for property 'last_files'
        '''
        _ = self.t.lgettext
        if isinstance(value, int):
            self._last_files = value
        else:
            msg = _("Invalid value for property '%s' given.") % ('last_files')
            raise LogRotateScriptError(msg)

    last_files = property(
                    _get_last_files,
                    _set_last_files,
                    None,
                    "Number of logfiles referencing to this script as a lastaction script."
    )

    #------------------------------------------------------------
    # Property 'done_firstrun'
    def _get_done_firstrun(self):
        '''
        Getter method for property 'done_firstrun'
        '''
        return self._done_firstrun

    def _set_done_firstrun(self, value):
        '''
        Setter method for property 'done_firstrun'
        '''
        self._done_firstrun = bool(value)

    done_firstrun = property(
                    _get_done_firstrun,
                    _set_done_firstrun,
                    None,
                    "Flag, whether the script was executed as a firstaction script."
    )

    #------------------------------------------------------------
    # Property 'done_prerun'
    def _get_done_prerun(self):
        '''
        Getter method for property 'done_prerun'
        '''
        return self._done_prerun

    def _set_done_prerun(self, value):
        '''
        Setter method for property 'done_prerun'
        '''
        self._done_prerun = bool(value)

    done_prerun = property(
                    _get_done_prerun,
                    _set_done_prerun,
                    None,
                    "Flag, whether the script was executed as a prerun script."
    )

    #------------------------------------------------------------
    # Property 'done_postrun'
    def _get_done_postrun(self):
        '''
        Getter method for property 'done_postrun'
        '''
        return self._done_postrun

    def _set_done_postrun(self, value):
        '''
        Setter method for property 'done_postrun'
        '''
        self._done_postrun = bool(value)

    done_postrun = property(
                    _get_done_postrun,
                    _set_done_postrun,
                    None,
                    "Flag, whether the script was executed as a postrun script."
    )

    #------------------------------------------------------------
    # Property 'done_lastrun'
    def _get_done_lastrun(self):
        '''
        Getter method for property 'done_lastrun'
        '''
        return self._done_lastrun

    def _set_done_lastrun(self, value):
        '''
        Setter method for property 'done_lastrun'
        '''
        self._done_lastrun = bool(value)

    done_lastrun = property(
                    _get_done_lastrun,
                    _set_done_lastrun,
                    None,
                    "Flag, whether the script was executed as a lastaction script."
    )

    #------------------------------------------------------------
    # Property 'do_post'
    def _get_do_post(self):
        '''
        Getter method for property 'do_post'
        '''
        return self._do_post

    def _set_do_post(self, value):
        '''
        Setter method for property 'do_post'
        '''
        self._do_post = bool(value)

    do_post = property(
                    _get_do_post,
                    _set_do_post,
                    None,
                    "Flag, whether the script should be executed as a postrun script."
    )

    #------------------------------------------------------------
    # Property 'do_last'
    def _get_do_last(self):
        '''
        Getter method for property 'do_last'
        '''
        return self._do_last

    def _set_do_last(self, value):
        '''
        Setter method for property 'do_last'
        '''
        self._do_last = bool(value)

    do_last = property(
                    _get_do_last,
                    _set_do_last,
                    None,
                    "Flag, whether the script should be executed as a lastaction script."
    )

    #------------------------------------------------------------
    # Other Methods

    #-------------------------------------------------------
    def __del__(self):
        '''
        Destructor.
        Checks, whether the script should even be run as
        a postrun or a lastaction script
        '''

        _ = self.t.lgettext
        if self.verbose > 2:
            msg = _("Logrotate script object '%s' will destroyed.") % (self.name)
            self.logger.debug(msg)

        self.check_for_execute()

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

        res = {}
        res['t']             = self.t
        res['verbose']       = self.verbose
        res['name']          = self.name
        res['test_mode']     = self.test_mode
        res['logger']        = self.logger
        res['cmd']           = self._cmd[:]
        res['post_files']    = self.post_files
        res['last_files']    = self.last_files
        res['done_firstrun'] = self.done_firstrun
        res['done_prerun']   = self.done_prerun
        res['done_postrun']  = self.done_postrun
        res['done_lastrun']  = self.done_lastrun
        res['do_post']       = self.do_post
        res['do_last']       = self.do_last

        return res

    #------------------------------------------------------------
    def add_cmd(self, cmd):
        '''
        Adding a command to the list self._cmd

        @param cmd: the command to add to self._cmd
        @type cmd:  str

        @return: None
        '''
        self._cmd.append(cmd)

    #------------------------------------------------------------
    def execute(self, force=False, expected_retcode=0):
        '''
        Executes the command as an OS command in a shell.

        @param force: force executing command even
                      if self.test_mode == True
        @type force:    bool
        @param expected_retcode: expected returncode of the command
                                 (should be 0)
        @type expected_retcode:  int

        @return: Success of the comand (shell returncode == 0)
        @rtype:  bool
        '''

        _ = self.t.lgettext
        cmd = self.cmd
        if cmd is None:
            msg = _("No command to execute defined in script '%s'.") % (self.name)
            raise LogRotateScriptError(msg)
            return False
        if self.verbose > 3:
            msg = _("Executing script '%(name)s' with command: '%(cmd)s'") \
                    % {'name': self.name, 'cmd': cmd}
            self.logger.debug(msg)
        if not force:
            if self.test_mode:
                return True
        try:
            retcode = subprocess.call(command, shell=True)
            if self.verbose > 3:
                msg = _("Got returncode for script '%(name)s': '%(retcode)s'") \
                        % {'name': self.name, 'retcode': retcode}
                self.logger.debug(msg)
            if retcode < 0:
                msg = _("Child in script '%(name)s' was terminated by signal %(retcode)d.") \
                        % {'name': self.name, 'retcode': -retcode}
                self.logger.error(msg)
                return False
            if retcode != expected_retcode:
                return False
            return True
        except OSError, e:
            msg = _("Execution of script '%(name)s' failed: %(error)s") \
                    % {'name': self.name, 'error': str(e)}
            self.logger.error(msg)
            return False

        return False

    #------------------------------------------------------------
    def check_for_execute(self, force=False, expected_retcode=0):
        '''
        Checks, whether the script should executed.

        @param force: force executing command even
                      if self.test_mode == True
        @type force:    bool
        @param expected_retcode: expected returncode of the command
                                 (should be 0)
        @type expected_retcode:  int

        @return: Success of execution
        @rtype:  bool
        '''

        _ = self.t.lgettext
        msg = _("Checking, whether the script '%s' should be executed.") % (self.name)
        self.logger.debug(msg)

        if self.do_post or self.do_last:
            result = self.execute(force=force, expected_retcode=expected_retcode)
            self.do_post = False
            self.do_last = False
            return result

        return True

#========================================================================

if __name__ == "__main__":
    pass


#========================================================================

# vim: fileencoding=utf-8 filetype=python ts=4 expandtab
