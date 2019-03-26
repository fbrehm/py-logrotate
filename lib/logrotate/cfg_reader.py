#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
@author: Frank Brehm
@contact: frank@brehm-online.com
@license: GPL3
@copyright: © 2010 - 2019 by Frank Brehm, Berlin
@summary: module the configuration parsing object for Python logrotating
"""
from __future__ import absolute_import, print_function

# Standard modules
import re
import logging
import subprocess
import pprint
import gettext
import copy
import errno
import os

from pathlib import Path

# Third party modules
import six

# Own modules
from fb_tools.common import pp, to_str
from fb_tools.obj import FbBaseObjectError, FbBaseObject
from fb_tools.handling_obj import HandlingObject

from . import DEFAULT_CONFIG_FILE
from .translate import XLATOR
from .errors import LogrotateConfigurationError
from .errors import LogrotateCfgFatalError, LogrotateCfgNonFatalError
from .common import split_parts
from .filegroup import LogFileGroup

__version__ = '0.2.1'

_ = XLATOR.gettext
ngettext = XLATOR.ngettext

LOG = logging.getLogger(__name__)


# =============================================================================
class LogrotateCfgFileNotExistsError(LogrotateCfgFatalError, IOError):

    # -------------------------------------------------------------------------
    def __init__(self, filename):

        msg = _("File does not exists")
        super(LogrotateCfgFileNotExistsError, self).__init__(
            errno.ENOENT, msg, str(filename))


# =============================================================================
class LogrotateCfgFileIsDirError(LogrotateCfgFatalError, IOError):

    # -------------------------------------------------------------------------
    def __init__(self, filename):

        msg = _("Path is a directory")
        super(LogrotateCfgFileIsDirError, self).__init__(
            errno.EISDIR, msg, str(filename))


# =============================================================================
class LogrotateCfgFileNoAccessError(LogrotateCfgFatalError, IOError):

    # -------------------------------------------------------------------------
    def __init__(self, filename):

        msg = _("File is not readable")
        super(LogrotateCfgFileNoAccessError, self).__init__(
            errno.EACCES, msg, str(filename))


# =============================================================================
class LogrotateCfgFileAlreadyRead(LogrotateCfgNonFatalError):

    # -------------------------------------------------------------------------
    def __init__(self, filename):

        self.filename = str(filename)

    # -------------------------------------------------------------------------
    def __str__(self):

        msg = _("Config file {!r} was already read.").format(self.filename)
        return msg


# =============================================================================
class LogrotateConfigReader(HandlingObject):
    '''Class for reading the configuration for Python logrotating'''

    #-------------------------------------------------------
    def __init__(
        self, config_file=DEFAULT_CONFIG_FILE, name=None, simulate=False, quiet=False,
            force=None, appname=None, verbose=0, base_dir=None):
        """
        Constructor.

        @param name: the name of the script as an identifier
        @type name: str
        @param simulate: test mode - no write actions are made
        @type simulate: bool

        @return: None
        """

        self._config_file = None
        self.default_group = None
        self._has_read = False
        self.file_groups = {}
        self.scripts = []

        super(LogrotateConfigReader, self).__init__(
            appname=appname, verbose=verbose, version=__version__, base_dir=base_dir,
            simulate=simulate, quiet=quiet, force=force)

        self.config_file = config_file

        self._init_default_group()

        self.initialized = True

    # -----------------------------------------------------------------------
    @property
    def config_file(self):
        "The file name of the config file to evaluate."
        return self._config_file

    @config_file.setter
    def config_file(self, value):
        if value is None:
            msg = _("The filename of the config file may not be None.")
            raise LogrotateConfigurationError(msg)
        self._config_file = Path(value)

    # ------------------------------------------------------------
    @property
    def has_read(self):
        "Flag, that the given config file was read."
        return self._has_read

    @has_read.setter
    def has_read(self, value):
        self._has_read = bool(value)

    # -----------------------------------------------------------------------
    def _init_default_group(self):

        LOG.debug(_("Initializing default file group ..."))

        self.default_group = LogFileGroup(
            appname=self.appname, verbose=self.verbose, base_dir=self.base_dir,
            simulate=self.simulate, is_default=True,
        )

    # -----------------------------------------------------------------------
    def _init_all_objects(self):

        self._init_default_group()
        self.file_groups = {}
        self.scripts = []

    # -------------------------------------------------------------------------
    def as_dict(self, short=True):
        """
        Transforms the elements of the object into a dict

        @return: structure as dict
        @rtype:  dict
        """

        res = super(LogrotateConfigReader, self).as_dict(short=short)

        res['config_file'] = self.config_file
        res['has_read'] = self.has_read

        return res

    # -------------------------------------------------------------------------
    def read(self):
        """
        Reads the main configuration file (self.config_file).
        Default entries are stored in object self.default_group.
        Found logfile statements are stored in self.file_groups.
        """

        if self.has_read:
            return

        if not self.config_file.exists():
            raise LogrotateCfgFileNotExistsError(self.config_file)

        self._init_all_objects()
        cfg_file = self.config_file.resolve()
        if not self._read(cfg_file):
            return False

        if self.verbose > 2:
            LOG.debug(_("All read config files:") + '\n' + pp(self.file_groups))

        self.has_read = True
        return True

    # -------------------------------------------------------------------------
    def _read(self, cfg_file):

        if not cfg_file.exists():
            raise LogrotateCfgFileNotExistsError(cfg_file)

        if cfg_file.is_dir():
            raise LogrotateCfgFileIsDirError(cfg_file)

        if not os.access(str(cfg_file), os.R_OK):
            raise LogrotateCfgFileNoAccessError(cfg_file)

        cfg_file = cfg_file.resolve()
        if cfg_file in self.file_groups:
            e = LogrotateCfgFileAlreadyRead(cfg_file)
            LOG.error(str(e))
            return True

        LOG.info(_("Reading configuration from {!r} ...").format(str(cfg_file)))

        self.file_groups[cfg_file] = None
        return True

#========================================================================

if __name__ == "__main__":
    pass

#========================================================================

# vim: fileencoding=utf-8 filetype=python ts=4 expandtab
