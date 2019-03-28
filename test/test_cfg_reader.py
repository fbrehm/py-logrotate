#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
@author: Frank Brehm
@contact: frank@brehm-online.com
@copyright: © 2010 - 2016 by Frank Brehm, Berlin
@license: GPL3
@summary: test script (and module) for unit tests on LogrotateConfigReader objects
"""

import os
import sys
import logging
import locale
import glob
import tempfile
import textwrap
import inspect

from pathlib import Path

try:
    import unittest2 as unittest
except ImportError:
    import unittest

# Third party modules
import six
import pytz


# Setting the user’s preferred locale settings
locale.setlocale(locale.LC_ALL, '')

libdir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'lib'))
sys.path.insert(0, libdir)

# Own modules
from fb_tools.common import pp, to_bytes, to_bool

from general import BaseTestCase, get_arg_verbose, init_root_logger

APPNAME = 'test_cfg_reader'
LOG = logging.getLogger(APPNAME)

# =============================================================================
class LogrotCfgReaderTestCase(BaseTestCase):

    # -------------------------------------------------------------------------
    def setUp(self):

        super(LogrotCfgReaderTestCase, self).setUp()
        self.appname = APPNAME

    # -------------------------------------------------------------------------
    def test_import(self):

        LOG.info("Testing import of logrotate.cfg_reader ...")
        import logrotate.cfg_reader                                      # noqa

        from logrotate.cfg_reader import LogrotateConfigReader           # noqa

    # -------------------------------------------------------------------------
    def test_object(self):

        LOG.info("Testing init of a config reader object ...")

        from logrotate.cfg_reader import LogrotateConfigReader
        from logrotate.filegroup import LogFileGroup

        reader = LogrotateConfigReader(
            appname=APPNAME,
            verbose=self.verbose)

        LOG.debug("{c} object %r:\n{o!r}".format(
            c=reader.__class__.__name__, o=reader))
        LOG.debug("{c} object %s:\n{o}".format(
            c=reader.__class__.__name__, o=reader))

        self.assertIsInstance(reader.config_file, Path)
        self.assertIsInstance(reader.default_group, LogFileGroup)
        self.assertTrue(reader.default_group.is_default)

    # -------------------------------------------------------------------------
    def test_read_simple(self):

        LOG.info("Testing reading of a config ...")

        from logrotate.cfg_reader import LogrotateConfigReader

        cft_stems = ('apache2', 'rsyslog')
        for stem in cft_stems:

            cfg_file = self.test_dir / stem

            reader = LogrotateConfigReader(
                appname=APPNAME, verbose=self.verbose,
                config_file=cfg_file)
            if self.verbose > 2:
                LOG.debug("{c} object %s:\n{o}".format(
                    c=reader.__class__.__name__, o=reader))

        reader.read()


# =============================================================================

if __name__ == '__main__':

    verbose = get_arg_verbose()
    if verbose is None:
        verbose = 0
    init_root_logger(verbose)

    LOG.info("Starting tests ...")

    suite = unittest.TestSuite()

    suite.addTest(LogrotCfgReaderTestCase('test_import', verbose))
    suite.addTest(LogrotCfgReaderTestCase('test_object', verbose))
    suite.addTest(LogrotCfgReaderTestCase('test_read_simple', verbose))

    runner = unittest.TextTestRunner(verbosity=verbose)

    result = runner.run(suite)


# =============================================================================

# vim: tabstop=4 expandtab shiftwidth=4 softtabstop=4
