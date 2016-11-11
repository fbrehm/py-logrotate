#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
@author: Frank Brehm
@contact: frank@brehm-online.com
@license: GPL3
@copyright: © 2010 - 2016 by Frank Brehm, Berlin
@summary: module for a logrotate script object (for pre- and postrotate actions)
"""

# Standard modules
import re
import logging
import subprocess
import pprint
import gettext

# Third party modules
import pytz
import six

# Own modules
from logrotate.common import split_parts, pp
from logrotate.common import logrotate_gettext, logrotate_ngettext

from logrotate.base import BaseObjectError, BaseObject

__version__ = '0.2.1'

_ = logrotate_gettext
__ = logrotate_ngettext

LOG = logging.getLogger(__name__)


# =============================================================================
class LogRotateScriptError(BaseObjectError):
    """
    Base class for exceptions in this module.
    """


# =============================================================================
class LogRotateScript(BaseObject):
    "Class for encapsulating a logrotate script (for pre- and postrotate actions)"

    #-------------------------------------------------------
    def __init__(self, name=None, simulate=False, appname=None, verbose=0, base_dir=None):
        """
        Constructor.

        @param name: the name of the script as an identifier
        @type name: str
        @param simulate: test mode - no write actions are made
        @type simulate: bool

        @return: None
        """

        self._name = None
        self._simulate = bool(simulate)
        self._post_files = 0
        self._last_files = 0
        self._done_firstrun = False
        self._done_prerun = False
        self._done_postrun = False
        self._done_lastrun = False
        self._do_post = False
        self._do_last = False

        self.cmd = []
        '''
        @ivar: List of commands to execute
        @type: list
        '''

        super(LogRotateScript, self).__init__(
            appname=appname, verbose=verbose, version=__version__, base_dir=base_dir)

    #------------------------------------------------------------
    # Defintion of some properties

    #------------------------------------------------------------
    @property
    def name(self):
        "Name of the script as an identifier"
        return self._name

    #------------------------------------------------------------
    @property
    def simulate(self):
        "Number of logfiles referencing to this script as a postrotate script."
        return self._simulate

    @simulate.setter
    def simulate(self, value):
        self._simulate = bool(value)

    #------------------------------------------------------------
    @property
    def post_files(self):
        "Number of logfiles referencing to this script as a postrotate script."
        return self._post_files

    @post_files.setter
    def post_files(self, value):
        if isinstance(value, int):
            self._post_files = value
            return
        msg = _("Invalid value for property %r given.") % ('post_files')
        raise LogRotateScriptError(msg)

    #------------------------------------------------------------
    @property
    def last_files(self):
        "Number of logfiles referencing to this script as a lastaction script."
        return self._last_files

    @last_files.setter
    def last_files(self, value):
        if isinstance(value, int):
            self._last_files = value
            return
        msg = _("Invalid value for property '%s' given.") % ('last_files')
        raise LogRotateScriptError(msg)

    #------------------------------------------------------------
    @property
    def done_firstrun(self):
        "Flag, whether the script was executed as a firstaction script."
        return self._done_firstrun

    @done_firstrun.setter
    def done_firstrun(self, value):
        self._done_firstrun = bool(value)

    #------------------------------------------------------------
    @property
    def done_prerun(self):
        "Flag, whether the script was executed as a prerun script."
        return self._done_prerun

    @done_prerun.setter
    def done_prerun(self, value):
        self._done_prerun = bool(value)

    #------------------------------------------------------------
    @property
    def done_postrun(self):
        "Flag, whether the script was executed as a postrun script."
        return self._done_postrun

    @done_postrun.setter
    def done_postrun(self, value):
        self._done_postrun = bool(value)

    #------------------------------------------------------------
    @property
    def done_lastrun(self):
        "Flag, whether the script was executed as a lastaction script."
        return self._done_lastrun

    @done_lastrun.setter
    def done_lastrun(self, value):
        self._done_lastrun = bool(value)

    #------------------------------------------------------------
    @property
    def do_post(self):
        "Flag, whether the script should be executed as a postrun script."
        return self._do_post

    @do_post.setter
    def _set_do_post(self, value):
        self._do_post = bool(value)

    #------------------------------------------------------------
    @property
    def do_last(self):
        "Flag, whether the script should be executed as a lastaction script."
        return self._do_last

    @do_last.setter
    def do_last(self, value):
        self._do_last = bool(value)

    #-------------------------------------------------------
    def __del__(self):
        '''
        Destructor.
        Checks, whether the script should even be run as
        a postrun or a lastaction script
        '''

        if self.verbose > 2:
            msg = _("Logrotate script object '%s' will destroyed.") % (self.name)
            LOG.debug(msg)

        self.check_for_execute()

    #------------------------------------------------------------
    def __str__(self):
        '''
        Typecasting function for translating object structure
        into a string
        '''

        return pp(self.as_dict())

    #-------------------------------------------------------
    def as_dict(self):
        '''
        Transforms the elements of the object into a dict

        @return: structure as dict
        @rtype:  dict
        '''

        res = super(LogRotateScript, self).as_dict()

        res['name'] = self.name
        res['simulate'] = self.simulate
        res['post_files'] = self.post_files
        res['last_files'] = self.last_files
        res['done_firstrun'] = self.done_firstrun
        res['done_prerun'] = self.done_prerun
        res['done_postrun'] = self.done_postrun
        res['done_lastrun'] = self.done_lastrun
        res['do_post'] = self.do_post
        res['do_last'] = self.do_last

        return res

    #------------------------------------------------------------
    def add_cmd(self, cmd):
        '''
        Adding a command to the list self._cmd

        @param cmd: the command to add to self._cmd
        @type cmd:  str

        @return: None
        '''
        self.cmd.append(cmd)

    #------------------------------------------------------------
    def execute(self, force=False, expected_retcode=0):
        '''
        Executes the command as an OS command in a shell.

        @param force: force executing command even
                      if self.simulate == True
        @type force:    bool
        @param expected_retcode: expected returncode of the command
                                 (should be 0)
        @type expected_retcode:  int

        @return: Success of the comand (shell returncode == 0)
        @rtype:  bool
        '''

        cmd = self.cmd
        if cmd is None:
            msg = _("No command to execute defined in script %r.") % (self.name)
            raise LogRotateScriptError(msg)
        if self.verbose > 3:
            msg = _("Executing script %(name)r with command: '%(cmd)s'") % {
                'name': self.name, 'cmd': cmd}
            LOG.debug(msg)
        if not force:
            if self.simulate:
                return True
        try:
            retcode = subprocess.call(command, shell=True)
            if self.verbose > 3:
                msg = _("Got returncode for script %(name)r: %(retcode)r") % {
                    'name': self.name, 'retcode': retcode}
                LOG.debug(msg)
            if retcode < 0:
                msg = _("Child in script %(name)r was terminated by signal %(retcode)r.") % {
                    'name': self.name, 'retcode': -retcode}
                LOG.error(msg)
                return False
            if retcode != expected_retcode:
                return False
            return True
        except OSError, e:
            msg = _("Execution of script %(name)r failed: %(error)s") % {
                'name': self.name, 'error': e}
            LOG.error(msg)
            return False

        return False

    #------------------------------------------------------------
    def check_for_execute(self, force=False, expected_retcode=0):
        '''
        Checks, whether the script should executed.

        @param force: force executing command even
                      if self.simulate == True
        @type force:    bool
        @param expected_retcode: expected returncode of the command
                                 (should be 0)
        @type expected_retcode:  int

        @return: Success of execution
        @rtype:  bool
        '''

        msg = _("Checking, whether the script %r should be executed.") % (self.name))
        LOG.debug(msg)

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
