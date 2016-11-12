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
import copy

from collections import MutableSequence

# Third party modules
import pytz
import six

# Own modules
from logrotate.common import split_parts, pp
from logrotate.common import logrotate_gettext, logrotate_ngettext
from logrotate.common import to_str_or_bust as to_str

from logrotate.base import BaseObjectError, BaseObject

__version__ = '0.3.2'

_ = logrotate_gettext
__ = logrotate_ngettext

LOG = logging.getLogger(__name__)


# =============================================================================
class LogRotateScriptError(BaseObjectError):
    """
    Base class for exceptions in this module.
    """


# =============================================================================
class LogRotateScript(BaseObject, MutableSequence):
    "Class for encapsulating a logrotate script (for pre- and postrotate actions)"

    #-------------------------------------------------------
    def __init__(
        self, name=None, simulate=False, commands=None,
            appname=None, verbose=0, base_dir=None):
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

        if name is not None:
            self._name = to_str(name, force=True)

        self._commands = []
        '''
        @ivar: List of commands to execute
        @type: list
        '''

        super(LogRotateScript, self).__init__(
            appname=appname, verbose=verbose, version=__version__, base_dir=base_dir)

        if isinstance(commands, (list, tuple)):
            for cmd in commands:
                self.append(cmd)
        elif commands is None:
            pass
        elif isinstance(to_str(commands), str):
            self.append(commands)
        else:
            msg = _("Invalide type %(t)r of parameter commands %(c)r.") % {
                't': commands.__class__.__name__, 'c': commands}
            raise TypeError(msg)

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

        res['commands'] = copy.copy(self._commands)

        return res

    # -------------------------------------------------------------------------
    def __len__(self):
        return len(self._commands)

    # -------------------------------------------------------------------------
    def __getitem__(self, key):
        return self._commands[key]

    # -------------------------------------------------------------------------
    def __setitem__(self, key, value):

        v = to_str(value, force=True)
        self._commands[key] = v

    # -------------------------------------------------------------------------
    def __delitem__(self, key):

        del self._commands[key]

    # -------------------------------------------------------------------------
    def __repr__(self):
        """Typecasting into a string for reproduction."""

        out = "<%s(" % (self.__class__.__name__)

        fields = []
        fields.append("name=%r" % (self.name))
        fields.append("simulate=%r" % (self.simulate))
        fields.append("appname=%r" % (self.appname))
        fields.append("verbose=%r" % (self.verbose))
        fields.append("version=%r" % (self.version))
        fields.append("base_dir=%r" % (self.base_dir))

        out += ", ".join(fields) + ")>"
        return out

    # -------------------------------------------------------------------------
    def index(self, value, *args):

        v = to_str(value, force=True)
        if len(args) > 2:
            msg = "Call of index() with a wrong number (%d) of arguments." % (len(args))
            raise AttributeError(msg)

        i = 0
        j = None
        if len(args) >= 1:
            i = int(args[0])
        if len(args) >= 2:
            j = int(args[1])
        found = False
        idx = i
        if len(self._commands) and i < len(self._commands):
            for cmd in self._commands[i:]:
                if cmd == v:
                    found = True
                    break
                idx += 1
                if j is not None and idx >= j:
                    break

        if not found:
            msg = "Command %r not found in command list." % (str(v))
            raise ValueError(msg)
        return idx

    # -------------------------------------------------------------------------
    def __contains__(self, cmd):
        try:
            self.index(cmd)
        except ValueError:
            return False

        return True

    # -------------------------------------------------------------------------
    def insert(self, i, cmd):
        v = to_str(cmd, force=True)
        self._commands.insert(i, v)

    # -------------------------------------------------------------------------
    def append(self, cmd):
        v = to_str(cmd, force=True)
        self._commands.append(v)

    #------------------------------------------------------------
    def add_cmd(self, cmd):
        self.append(cmd)

    #------------------------------------------------------------
    def __call__(self):
        """
        Wrapper for self.execute(force=False, expected_retcode=0)
        """
        return self.execute(force=False, expected_retcode=0)

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

        if not self._commands:
            msg = _("No command to execute defined in script %r.") % (self.name)
            raise LogRotateScriptError(msg)

        command = '\n'.join(self._commands)

        if self.verbose > 3:
            msg = _("Executing script %(name)r with command:\n%(cmd)s") % {
                'name': self.name, 'cmd': command.rstrip()}
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
        except OSError as e:
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

        msg = _("Checking, whether the script %r should be executed.") % (self.name)
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
