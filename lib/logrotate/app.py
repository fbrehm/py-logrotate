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
import argparse
from pathlib import Path

# Third party modules

# Own modules
from . import __version__ as GLOBAL_VERSION

# Own modules
from fb_tools.common import pp, to_str
from fb_tools.app import BaseApplication
from fb_tools.errors import FbAppError
from fb_tools.handler.lock import LockHandler

from . import DEFAULT_CONFIG_FILE, DEFAULT_STATUS_FILE, DEFAULT_PID_FILE
from .translate import __module_dir__ as __xlate_module_dir__
from .translate import __base_dir__ as __xlate_base_dir__
from .translate import __mo_file__ as __xlate_mo_file__
from .translate import XLATOR, LOCALE_DIR, DOMAIN

from .errors import LogrotateConfigurationError, LogrotateObjectError
from .errors import LogrotateCfgFatalError, LogrotateCfgNonFatalError
from .common import split_parts
from .cfg_reader import LogrotateConfigReader
from .filegroup import LogFileGroup
from .script import LogRotateScript
from .status import StatusFile

__version__ = '0.3.3'

_ = XLATOR.gettext
ngettext = XLATOR.ngettext

LOG = logging.getLogger(__name__)


# =============================================================================
class LogrotateAppError(FbAppError, LogrotateObjectError):
    """Base exception class for all exceptions in this application module."""
    pass


# =============================================================================
class CfgFileOptionAction(argparse.Action):

    # -------------------------------------------------------------------------
    def __init__(self, option_strings, must_exists, *args, **kwargs):

        super(CfgFileOptionAction, self).__init__(
            option_strings=option_strings, *args, **kwargs)
        self.must_exists = bool(must_exists)

    # -------------------------------------------------------------------------
    def __call__(self, parser, namespace, filename, option_string=None):

        if filename is None:
            setattr(namespace, self.dest, None)
            return

        path = Path(filename)
        if self.must_exists and not path.exists():
            msg = _("File {!r} does not exists.").format(filename)
            raise argparse.ArgumentError(self, msg)
        if path.exists() and not path.is_file():
            msg = _("File {!r} is not a regular file.").format(filename)
            raise argparse.ArgumentError(self, msg)

        setattr(namespace, self.dest, path.resolve())


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
        self.statusfile = None
        self._statusfilename = None
        self._pidfile = None
        self.locker = None

        self.file_groups = []
        self.scripts = {}

        super(LogrotateApplication, self).__init__(
            appname=appname, verbose=verbose, version=GLOBAL_VERSION, base_dir=base_dir,
            description=desc, initialized=False,
        )

        self.initialized = True

    # -------------------------------------------------------------------------
    @property
    def cfg_file(self):
        """Configuration file."""
        return self._cfg_file

    # -------------------------------------------------------------------------
    @property
    def statusfilename(self):
        """Status file."""
        return self._statusfilename

    # -------------------------------------------------------------------------
    @property
    def pidfile(self):
        """PID file."""
        return self._pidfile

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
        res['statusfilename'] = self.statusfilename
        res['pidfile'] = self.pidfile

        if 'xlate' not in res:
            res['xlate'] = {}
        res['xlate'][DOMAIN] = {
            '__module_dir__': __xlate_module_dir__,
            '__base_dir__': __xlate_base_dir__,
            'LOCALE_DIR': LOCALE_DIR,
            'DOMAIN': DOMAIN,
            '__mo_file__': __xlate_mo_file__,
        }

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

        self.init_objects()
        self.cfg_reader.read()
        self.perform_arg_parser_after_cfg()
        self.statusfile.filename = self.statusfilename
        self.statusfile.initialized = True

        self.locker = LockHandler(
            appname=self.appname, verbose=self.verbose, base_dir=self.base_dir,
            simulate=self.simulate, sudo=False, quiet=self.quiet,
            lockretry_delay_start=1, lockretry_delay_increase=1,
            lockretry_max_delay=1800, max_lockfile_age=3600, locking_use_pid=True,
            lockdir=self.pidfile.parent)
        self.locker.initialized = True

        self.initialized = True

    # -------------------------------------------------------------------------
    def init_arg_parser(self):
        """
        Public available method to initiate the argument parser.
        """

        super(LogrotateApplication, self).init_arg_parser()

        lr_group = self.arg_parser.add_argument_group(_('Logrotate Options'))

        lr_group.add_argument(
            '-S', '--state', dest='status_file', metavar=_('FILE'),
            action=CfgFileOptionAction, must_exists=False,
            help=_("Path of state file (default: {!r}).").format(str(DEFAULT_STATUS_FILE))
        )

        lr_group.add_argument(
            '-P', '--pidfile', dest='pidfile', metavar=_('FILE'),
            action=CfgFileOptionAction, must_exists=False,
            help=_("Path of PID file (default: {!r}).").format(str(DEFAULT_PID_FILE))
        )

        self.arg_parser.add_argument(
            'cfg_file', metavar=_('CONFIG_FILE'), nargs='?',
            action=CfgFileOptionAction, must_exists=True, default=DEFAULT_CONFIG_FILE,
            help=_("Path of the configuration file (default: {!r}).").format(
                str(DEFAULT_CONFIG_FILE))
        )

    # -------------------------------------------------------------------------
    def perform_arg_parser(self):

        if self.args.cfg_file:
            self._cfg_file = self.args.cfg_file
        else:
            self._cfg_file = DEFAULT_CONFIG_FILE

    # -------------------------------------------------------------------------
    def perform_arg_parser_after_cfg(self):

        if self.args.status_file:
            self._statusfilename = self.args.status_file
        elif self.cfg_reader.statusfile:
            self._statusfilename = self.cfg_reader.statusfile
        else:
            self._statusfilename = DEFAULT_STATUS_FILE

        if not self.statusfilename.is_absolute():
            self._statusfilename = (self.base_dir / self.statusfilename)

        if self.args.pidfile:
            self._pidfile = self.args.pidfile
        elif self.cfg_reader.pidfile:
            self._pidfile = self.cfg_reader.pidfile
        else:
            self._pidfile = DEFAULT_PID_FILE

        if not self.pidfile.is_absolute():
            self._pidfile = (self.base_dir / self.pidfile)

    # -------------------------------------------------------------------------
    def init_objects(self):

        LOG.debug(_("Initializing necessary objects ..."))

        self.cfg_reader = LogrotateConfigReader(
            config_file=self.cfg_file, simulate=self.simulate, quiet=self.quiet, force=self.force,
            appname=self.appname, verbose=self.verbose, base_dir=self.base_dir)
        self.cfg_reader.initialized = True

        sfile = DEFAULT_STATUS_FILE
        if self.statusfilename:
            sfile = self.statusfilename
        self.statusfile = StatusFile(
            sfile, simulate=self.simulate, auto_read=False,
            appname=self.appname, verbose=self.verbose, base_dir=self.base_dir)

    # -------------------------------------------------------------------------
    def pre_run(self):

        LOG.debug(_("Executing {!r} ...").format('pre_run()'))

        self.cfg_reader.resolve_globbings()
        nr_files = len(self.cfg_reader.all_logfiles.keys())
        if not nr_files:
            LOG.info(_("Found no existing logfiles to rotate."))
            self.exit(0)
        msg = ngettext(
            "Found one existing logfile to rotate.",
            "Found {nr} existing logfiles to rotate.", nr_files).format(nr=nr_files)
        LOG.debug(msg)

    # -------------------------------------------------------------------------
    def _run(self):

        LOG.info(_("Starting {a!r}, version {v!r} ...").format(
            a=self.appname, v=self.version))

        LOG.info(_("Trying to create PID-file {fn!r} ...").format(fn=str(self.pidfile)))
        lock = self.locker.create_lockfile(self.pidfile)
        lock.autoremove = True

        try:

            self.cfg_reader.check_for_rotation()
            nr_files = len(self.cfg_reader.logfiles_rotate.keys())
            if not nr_files:
                LOG.info(_("Found no logfiles to rotate."))
                self.exit(0)
            msg = ngettext(
                "Found one logfile to rotate.",
                "Found {nr} logfiles to rotate.", nr_files).format(nr=nr_files)
            LOG.debug(msg)

        finally:
            lock = None


# =============================================================================
if __name__ == "__main__":

    pass

# =============================================================================

# vim: tabstop=4 expandtab shiftwidth=4 softtabstop=4 list
