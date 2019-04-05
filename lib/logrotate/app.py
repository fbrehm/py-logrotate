#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
@author: Frank Brehm
@contact: frank.brehm@pixelpark.com
@copyright: © 2019 by Frank Brehm, Berlin
@summary: The module for the plogrotate application object.
"""
from __future__ import absolute_import, print_function

# Standard modules
import logging

# Third party modules

# Own modules
from . import __version__ as GLOBAL_VERSION

# Own modules
from fb_tools.common import pp, to_str
from fb_tools.app import BaseApplication
from fb_tools.errors import FbAppError

from . import DEFAULT_CONFIG_FILE, DEFAULT_STATUS_FILE, DEFAULT_PID_FILE
from .translate import XLATOR

from .errors import LogrotateConfigurationError, LogrotateObjectError
from .errors import LogrotateCfgFatalError, LogrotateCfgNonFatalError
from .common import split_parts
from .filegroup import LogFileGroup
from .script import LogRotateScript

__version__ = '0.1.1'

_ = XLATOR.gettext
ngettext = XLATOR.ngettext

LOG = logging.getLogger(__name__)


# =============================================================================
class LogrotateAppError(FbAppError, LogrotateObjectError):
    """Base exception class for all exceptions in this application module."""
    pass


# =============================================================================
class LogrotateApplication(BaseApplication):
    """Class for the application object."""

    # -------------------------------------------------------------------------
    def __init__(self, appname=None, verbose=0, version=__version__, base_dir=None):

        desc = _(
            "It is designed to ease administration of systems that generate large numbers "
            "of log files. It allows automatic rotation, compression and removal of log files. "
            "Each log file may be handled hourly, daily, weekly, monthly, "
            "or when it grows too large.")

        self._cfg_file = None
        self.cfg_reader = None
        self._statusfile = None
        self._pidfile = None

        self.file_groups = []
        self.scripts = {}

        super(LogrotateApplication, self).__init__(
            appname=appname, verbose=verbose, version=version, base_dir=base_dir,
            description=desc, initialized=False,
        )

        self.initialized = True

    # -------------------------------------------------------------------------
    @property
    def cfg_file(self):
        """Configuration file."""
        return self._cfg_file

    # -------------------------------------------------------------------------
    def as_dict(self, short=True):
        """
        Transforms the elements of the object into a dict

        @param short: don't include local properties in resulting dict.
        @type short: bool

        @return: structure as dict
        @rtype:  dict
        """

        res = super(LogrotateApplication, self).as_dict(short=short)
        res['cfg_file'] = self.cfg_file

        return res

    # -------------------------------------------------------------------------
    def post_init(self):
        """
        Method to execute before calling run(). Here could be done some
        finishing actions after reading in commandline parameters,
        configuration a.s.o.

        This method could be overwritten by descendant classes, these
        methhods should allways include a call to post_init() of the
        parent class.

        """

        self.initialized = False

        self.init_logging()
        self.perform_arg_parser()


        self.initialized = True

    # -------------------------------------------------------------------------
    def _run(self):

        LOG.debug(_("Starting {a!r}, version {v!r} ...").format(
            a=self.appname, v=self.version))


# =============================================================================
if __name__ == "__main__":

    pass

# =============================================================================

# vim: tabstop=4 expandtab shiftwidth=4 softtabstop=4 list
