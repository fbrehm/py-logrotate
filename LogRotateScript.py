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
import re
import logging
import subprocess
import pprint
import gettext

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
            'LogRotateScript',
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
    @property
    def name(self):
        '''
        Property 'name' as the name of the script as an identifier

        readonly
        '''
        return self._name

    #------------------------------------------------------------
    @property
    def cmd(self):
        '''
        Property 'cmd' as the commands to execute
        '''
        if len(self._cmd):
            return "\n".join(self._cmd)
        else:
            return None

    #---------------
    @cmd.setter
    def cmd(self, value):
        '''
        Setter of property 'cmd'

        @param value: the command to set to self._cmd
        @type value:  str

        @return: None
        '''
        if value:
            if isinstance(value, list):
                self._cmd = value[:]
            else:
                self._cmd = [value]
        else:
            self._cmd = []

    #---------------
    @cmd.deleter
    def cmd(self):
        '''
        Deleter of property 'cmd'
        '''
        self._cmd = []

    #------------------------------------------------------------
    @property
    def post_files(self):
        '''
        Property 'post_files' as the number of logfiles
        referencing to this script as a postrotate script
        '''
        return self._post_files

    #---------------
    @post_files.setter
    def post_files(self, value):
        '''
        Setter of property 'post_files'
        '''

        _ = self.t.lgettext
        if isinstance(value, int):
            self._post_files = value
        else:
            msg = _("Invalid value for property '%s' given.") % ('post_files')
            raise LogRotateScriptError(msg)

    #------------------------------------------------------------
    @property
    def last_files(self):
        '''
        Property 'last_files' as the number of logfiles
        referencing to this script as a lastaction script
        '''
        return self._last_files

    #---------------
    @last_files.setter
    def last_files(self, value):
        '''
        Setter of property 'last_files'
        '''

        _ = self.t.lgettext
        if isinstance(value, int):
            self._last_files = value
        else:
            msg = _("Invalid value for property '%s' given.") % ('last_files')
            raise LogRotateScriptError(msg)

    #------------------------------------------------------------
    @property
    def done_firstrun(self):
        '''
        Property 'done_firstrun' as a flag, whether the script
        was executed as a firstaction script
        '''
        return self._done_firstrun

    #---------------
    @done_firstrun.setter
    def done_firstrun(self, value):
        '''
        Setter of property 'done_firstrun'
        '''
        self._done_firstrun = bool(value)

    #------------------------------------------------------------
    @property
    def done_prerun(self):
        '''
        Property 'done_prerun' as a flag, whether the script
        was executed as a prerun script
        '''
        return self._done_prerun

    #---------------
    @done_prerun.setter
    def done_prerun(self, value):
        '''
        Setter of property 'done_prerun'
        '''
        self._done_prerun = bool(value)

    #------------------------------------------------------------
    @property
    def done_postrun(self):
        '''
        Property 'done_postrun' as a flag, whether the script
        was executed as a postrun script
        '''
        return self._done_postrun

    #---------------
    @done_postrun.setter
    def done_postrun(self, value):
        '''
        Setter of property 'done_postrun'
        '''
        self._done_postrun = bool(value)

    #------------------------------------------------------------
    @property
    def done_lastrun(self):
        '''
        Property 'done_lastrun' as a flag, whether the script
        was executed as a lastaction script
        '''
        return self._done_lastrun

    #---------------
    @done_lastrun.setter
    def done_lastrun(self, value):
        '''
        Setter of property 'done_lastrun'
        '''
        self._done_lastrun = bool(value)

    #------------------------------------------------------------
    @property
    def do_post(self):
        '''
        Property 'do_post' as a flag, whether the script
        should be executed as a postrun script
        '''
        return self._do_post

    #---------------
    @do_post.setter
    def do_post(self, value):
        '''
        Setter of property 'do_post'
        '''
        self._do_post = bool(value)

    #------------------------------------------------------------
    @property
    def do_last(self):
        '''
        Property 'do_last' as a flag, whether the script
        should be executed as a lastaction script
        '''
        return self._do_last

    #---------------
    @do_last.setter
    def do_last(self, value):
        '''
        Setter of property 'do_last'
        '''
        self._do_last = bool(value)

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
                msg = _("Child in script '%(name)s' was terminated by signal %(retcode)d") \
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
