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
import logging
import copy

from collections import MutableSequence

from pathlib import Path

# Third party modules

# Own modules
from fb_tools.common import pp, to_str
from fb_tools.handling_obj import HandlingObject

from .errors import LogRotateScriptError, ExecutionError

from .translate import XLATOR

__version__ = '0.5.2'

_ = XLATOR.gettext
ngettext = XLATOR.ngettext

LOG = logging.getLogger(__name__)


# =============================================================================
class LogRotateScript(HandlingObject, MutableSequence):
    "Class for encapsulating a logrotate script (for pre- and postrotate actions)"

    # ------------------------------------------------------
    def __init__(
        self, name=None, commands=None, cfg_file=None, cfg_line=None,
            simulate=False, quiet=False, force=None, appname=None, verbose=0, base_dir=None):
        """
        Constructor.

        @param name: the name of the script as an identifier
        @type name: str
        @param simulate: test mode - no write actions are made
        @type simulate: bool

        @return: None
        """

        self._name = None
        self._post_files = 0
        self._last_files = 0
        self._done_firstrun = False
        self._done_prerun = False
        self._done_postrun = False
        self._done_lastrun = False
        self._do_post = False
        self._do_last = False

        self._cfg_file = None
        self._cfg_line = None

        if name is not None:
            self._name = to_str(name)

        self._commands = []
        '''
        @ivar: List of commands to execute
        @type: list
        '''

        super(LogRotateScript, self).__init__(
            appname=appname, verbose=verbose, version=__version__, base_dir=base_dir,
            simulate=simulate, quiet=quiet, force=force)

        self.cfg_file = cfg_file
        self.cfg_line = cfg_line

        if isinstance(commands, (list, tuple)):
            for cmd in commands:
                self.append(cmd)
        elif commands is None:
            pass
        elif isinstance(to_str(commands), str):
            self.append(commands)
        else:
            msg = _("Invalid type {t!r} of parameter {par}: {pat!r}.").format(
                t=commands.__class__.__name__, par='commands', pat=commands)
            raise TypeError(msg)

    # -----------------------------------------------------------
    # Defintion of some properties

    # -----------------------------------------------------------
    @property
    def name(self):
        "Name of the script as an identifier"
        return self._name

    # ------------------------------------------------------------
    @property
    def cfg_file(self):
        "Filename of the configuration file, where this script is defined."
        return self._cfg_file

    @cfg_file.setter
    def cfg_file(self, value):
        if value is None:
            self._cfg_file = None
            return
        self._cfg_file = Path(value)

    # ------------------------------------------------------------
    @property
    def cfg_line(self):
        """
        The number of the beginning line of the definition in the configuration file,
        where this script is defined.
        """
        return self._cfg_line

    @cfg_line.setter
    def cfg_line(self, value):
        if value is None:
            self._cfg_line = None
            return
        self._cfg_line = int(value)

    # -----------------------------------------------------------
    @property
    def post_files(self):
        "Number of logfiles referencing to this script as a postrotate script."
        return self._post_files

    @post_files.setter
    def post_files(self, value):
        if isinstance(value, int):
            self._post_files = value
            return
        msg = _("Invalid value for property {!r} given.").format('post_files')
        raise LogRotateScriptError(msg)

    # -----------------------------------------------------------
    @property
    def last_files(self):
        "Number of logfiles referencing to this script as a lastaction script."
        return self._last_files

    @last_files.setter
    def last_files(self, value):
        if isinstance(value, int):
            self._last_files = value
            return
        msg = _("Invalid value for property {!r} given.").format('last_files')
        raise LogRotateScriptError(msg)

    # -----------------------------------------------------------
    @property
    def done_firstrun(self):
        "Flag, whether the script was executed as a firstaction script."
        return self._done_firstrun

    @done_firstrun.setter
    def done_firstrun(self, value):
        self._done_firstrun = bool(value)

    # -----------------------------------------------------------
    @property
    def done_prerun(self):
        "Flag, whether the script was executed as a prerun script."
        return self._done_prerun

    @done_prerun.setter
    def done_prerun(self, value):
        self._done_prerun = bool(value)

    # -----------------------------------------------------------
    @property
    def done_postrun(self):
        "Flag, whether the script was executed as a postrun script."
        return self._done_postrun

    @done_postrun.setter
    def done_postrun(self, value):
        self._done_postrun = bool(value)

    # -----------------------------------------------------------
    @property
    def done_lastrun(self):
        "Flag, whether the script was executed as a lastaction script."
        return self._done_lastrun

    @done_lastrun.setter
    def done_lastrun(self, value):
        self._done_lastrun = bool(value)

    # -----------------------------------------------------------
    @property
    def do_post(self):
        "Flag, whether the script should be executed as a postrun script."
        return self._do_post

    @do_post.setter
    def _set_do_post(self, value):
        self._do_post = bool(value)

    # -----------------------------------------------------------
    @property
    def do_last(self):
        "Flag, whether the script should be executed as a lastaction script."
        return self._do_last

    @do_last.setter
    def do_last(self, value):
        self._do_last = bool(value)

    # -----------------------------------------------------------
    @property
    def command(self):
        "All commands as a single string, separated by newlines."

        if not self._commands:
            return None
        return '\n'.join(self._commands)

    # ------------------------------------------------------
    def __del__(self):
        '''
        Destructor.
        Checks, whether the script should even be run as
        a postrun or a lastaction script
        '''

        if self.verbose > 2:
            msg = _("Logrotate script object {!r} will be destroyed.").format(self.name)
            LOG.debug(msg)

        self.check_for_execute()

    # -----------------------------------------------------------
    def __str__(self):
        '''
        Typecasting function for translating object structure
        into a string
        '''

        return pp(self.as_dict())

    # ------------------------------------------------------
    def as_dict(self, short=True):
        '''
        Transforms the elements of the object into a dict

        @return: structure as dict
        @rtype:  dict
        '''

        res = super(LogRotateScript, self).as_dict(short=short)

        res['name'] = self.name
        res['post_files'] = self.post_files
        res['last_files'] = self.last_files
        res['done_firstrun'] = self.done_firstrun
        res['done_prerun'] = self.done_prerun
        res['done_postrun'] = self.done_postrun
        res['done_lastrun'] = self.done_lastrun
        res['do_post'] = self.do_post
        res['do_last'] = self.do_last
        res['cfg_file'] = self.cfg_file
        res['cfg_line'] = self.cfg_line

        res['command'] = self.command
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

        v = str(to_str(value))
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
        fields.append("cfg_file=%r" % (self.cfg_file))
        fields.append("cfg_line=%r" % (self.cfg_line))
        fields.append("simulate=%r" % (self.simulate))
        fields.append("appname=%r" % (self.appname))
        fields.append("verbose=%r" % (self.verbose))
        fields.append("version=%r" % (self.version))
        fields.append("base_dir=%r" % (self.base_dir))

        out += ", ".join(fields) + ")>"
        return out

    # -------------------------------------------------------------------------
    def __copy__(self):
        """Wrapper method for copy.copy() to create a complete copy
        of this script."""

        new_script = LogRotateScript(
            name=self.name, cfg_file=self.cfg_file, cfg_line=self.cfg_line,
            simulate=self.simulate, quiet=self.quiet, force=self.force,
            appname=self.appname, verbose=self.verbose, base_dir=self.base_dir,
        )

        new_script.post_files = self.post_files
        new_script.last_files = self.last_files
        new_script.done_firstrun = self.done_firstrun
        new_script.done_prerun = self.done_prerun
        new_script.done_postrun = self.done_postrun
        new_script.done_lastrun = self.done_lastrun
        new_script.do_post = self.do_post
        new_script.do_last = self.do_last

        for cmd in self:
            new_script.append(cmd)

        return new_script

    # -------------------------------------------------------------------------
    def index(self, value, *args):

        v = str(to_str(value))
        if len(args) > 2:
            msg = _("Call of {what} with a wrong number ({nr}) of arguments.").format(
                what='index()', nr=len(args))
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
            msg = "Command {!r} not found in command list.".format(str(v))
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
        v = str(to_str(cmd))
        self._commands.insert(i, v)

    # -------------------------------------------------------------------------
    def append(self, cmd):
        v = str(to_str(cmd))
        self._commands.append(v)

    # -----------------------------------------------------------
    def add_cmd(self, cmd):
        self.append(cmd)

    # -----------------------------------------------------------
    def __call__(self):
        """
        Wrapper for self.execute(force=False, expected_retcode=0)
        """
        return self.execute(force=False, expected_retcode=0)

    # -----------------------------------------------------------
    def execute(self, force=None, expected_retcode=0, raise_on_error=False):
        """
        Executes the command as an OS command in a shell.

        @param force: force executing command even if self.simulate == True
        @type force: bool
        @param expected_retcode: expected returncode of the command (should be 0)
        @type expected_retcode: int
        @param raise_on_error: don't raise an ExecutionError on a wrong return value
        @type raise_on_error: bool

        @raise ExecutionError: if the execution returns a wrong return value
                               (!= 0) and raise_on_error was set to True

        @return: Shell return value (Success == 0)
        @rtype: int
        """

        if not self.command:
            msg = _("No command to execute defined in script {!r}.").format(self.name)
            raise LogRotateScriptError(msg)

        if self.verbose > 2:
            msg = _("Executing script {!r} with command:").format(self.name)
            msg += '\n' + self.command.rstrip()
            LOG.debug(msg)
        if force is None:
            force = self.force
        if not force:
            if self.simulate:
                return True

        try:
            completed = self.run([self.command], shell=True)
            if self.verbose > 1:
                LOG.debug(_("Completed process:") + '\n' + pp(completed.__dict__))
            if completed.returncode != expected_retcode:
                ret_msg = _("Got returncode for script {s!r}: {ret!r}.").format(
                    s=self.name, ret=completed.returncode)
                if raise_on_error:
                    raise ExecutionError(ret_msg)
                else:
                    LOG.error(ret_msg)
            return completed.returncode
        except OSError as e:
            msg = _("Execution of script {s!r} failed: {e}").format(s=self.name, e=e)
            if raise_on_error:
                raise ExecutionError(msg)
            else:
                LOG.error(msg)
            return 999

        return 999

    # -----------------------------------------------------------
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

        msg = _("Checking, whether the script {!r} should be executed.").format(self.name)
        LOG.debug(msg)

        if self.do_post or self.do_last:
            result = self.execute(force=force, expected_retcode=expected_retcode)
            self.do_post = False
            self.do_last = False
            return result

        return True


# =======================================================================
if __name__ == "__main__":
    pass

# =======================================================================

# vim: fileencoding=utf-8 filetype=python ts=4 expandtab
