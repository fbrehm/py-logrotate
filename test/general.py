#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
@author: Frank Brehm
@contact: frank@brehm-online.com
@copyright: © 2010 - 2016 by Frank Brehm, Berlin
@license: GPL3
@summary: general used functions an objects used for unit tests
"""

import os
import sys
import logging
import argparse
import tempfile
import shutil

from logging import Formatter

from pathlib import Path

try:
    import unittest2 as unittest
except ImportError:
    import unittest

# Own modules
HAS_COLORED_LOGGING = False
try:
    from fb_tools.colored import ColoredFormatter
    HAS_COLORED_LOGGING = True
except ImportError:
    pass

# =============================================================================

LOG = logging.getLogger(__name__)


# =============================================================================
def get_arg_verbose():

    arg_parser = argparse.ArgumentParser()

    arg_parser = argparse.ArgumentParser()
    arg_parser.add_argument(
        "-v", "--verbose", action="count",
        dest='verbose', help='Increase the verbosity level')
    args = arg_parser.parse_args()

    return args.verbose


# =============================================================================
def init_root_logger(verbose=0):

    root_log = logging.getLogger()
    root_log.setLevel(logging.WARNING)
    if verbose > 1:
        root_log.setLevel(logging.DEBUG)
    elif verbose:
        root_log.setLevel(logging.INFO)

    appname = os.path.basename(sys.argv[0])
    format_str = appname + ': '
    if verbose:
        if verbose > 1:
            format_str += '%(name)s(%(lineno)d) %(funcName)s() '
        else:
            format_str += '%(name)s '
    format_str += '%(levelname)s - %(message)s'
    formatter = None
    if HAS_COLORED_LOGGING:
        formatter = ColoredFormatter(format_str)
    else:
        formatter = Formatter(format_str)

    # create log handler for console output
    lh_console = logging.StreamHandler(sys.stderr)
    if verbose:
        lh_console.setLevel(logging.DEBUG)
    else:
        lh_console.setLevel(logging.INFO)
    lh_console.setFormatter(formatter)

    root_log.addHandler(lh_console)


# =============================================================================
class BaseTestCase(unittest.TestCase):

    # -------------------------------------------------------------------------
    def __init__(self, methodName='runTest', verbose=0):

        self._verbose = int(verbose)
        self._root_dir = None

        super(BaseTestCase, self).__init__(methodName)

    # -------------------------------------------------------------------------
    @property
    def verbose(self):
        """The verbosity level."""
        return getattr(self, '_verbose', 0)

    # -------------------------------------------------------------------------
    @property
    def root_dir(self):
        "A temporary root directory for chroot operations."
        return self._root_dir

    # -------------------------------------------------------------------------
    def create_root_dir(self):

        if self.root_dir and self.root_dir.exists():
            if self.root_dir.is_dir() and os.access(str(self.root_dir), os.W_OK):
                return
            msg = "Path {!r} exists, but is either not a directory or not writeable.".format(
                str(self.root_dir))
            raise RuntimeError(msg)

        self._root_dir = Path(tempfile.mkdtemp(prefix='chroot-'))
        LOG.debug("Created temporary directory {!r} for chroot operations.".format(
            str(self.root_dir)))

    # -------------------------------------------------------------------------
    def setUp(self):

        self.base_dir = Path(__file__).parent.parent.resolve()
        self.base_dir = self.base_dir.relative_to(Path.cwd())
        LOG.debug("Base directory is: {!r}".format(str(self.base_dir)))

        self.tmp_dir = self.base_dir.joinpath('tmp')
        LOG.debug("Tmp directory is: {!r}".format(str(self.tmp_dir)))

        self.test_dir = self.base_dir.joinpath('test')
        LOG.debug("Test directory is: {!r}".format(str(self.test_dir)))

    # -------------------------------------------------------------------------
    def tearDown(self):

        if self.root_dir:
            if not self.root_dir.exists():
                LOG.debug("Chroot directory {!r} seems not to be existing.".format(str(self.root_dir)))
            elif not self.root_dir.is_dir():
                LOG.error("Path {!r} exists, but is not a directory.".format(str(self.root_dir)))
            elif not os.access(str(self.root_dir), os.W_OK):
                LOG.error("No write access to chroot directory {!r} for removing.".format(str(self.root_dir)))
            else:
                LOG.debug("Removing chroot directory {!r} recursive.".format(str(self.root_dir)))
                shutil.rmtree(str(self.root_dir), ignore_errors=True)
            self._root_dir = None

# =============================================================================

if __name__ == '__main__':

    pass

# =============================================================================

# vim: tabstop=4 expandtab shiftwidth=4 softtabstop=4
