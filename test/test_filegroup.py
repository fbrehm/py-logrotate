#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
@author: Frank Brehm
@contact: frank@brehm-online.com
@copyright: © 2010 - 2016 by Frank Brehm, Berlin
@license: GPL3
@summary: test script (and module) for unit tests on LogFileGroupError objects
"""

import os
import sys
import logging
import locale
import glob
import tempfile
import textwrap
import inspect

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
from logrotate.common import pp

from general import BaseTestCase, get_arg_verbose, init_root_logger

APPNAME = 'test_filegroup'
LOG = logging.getLogger(APPNAME)


# =============================================================================
class LogFileGroupTestCase(BaseTestCase):

    # -------------------------------------------------------------------------
    def setUp(self):

        super(LogFileGroupTestCase, self).setUp()
        self.appname = APPNAME

    # -------------------------------------------------------------------------
    def test_import(self):

        LOG.info("Testing import of logrotate.filegroup ...")
        import logrotate.filegroup                                       # noqa

        from logrotate.filegroup import LogFileGroup                     # noqa

    # -------------------------------------------------------------------------
    def test_define_taboo_pattern(self):

        LOG.info("Testing initialisation and modifying of taboo patterns.")
        from logrotate.filegroup import LogFileGroup

        LogFileGroup.init_taboo_patterns()
        patterns = []
        for regex in LogFileGroup.taboo_patterns:
            patterns.append(regex.pattern)
        LOG.debug("Found initialised taboo patterns:\n%s", pp(patterns))
        test_patterns = (r',v$', r'~$', r'^\.', r'^CVS$')
        for pat in test_patterns:
            self.assertIn(pat, patterns)

    # -------------------------------------------------------------------------
    def test_object(self):

        LOG.info("Testing creating a new LogFileGroup object ...")
        from logrotate.filegroup import LogFileGroup

        group = LogFileGroup(
            simulate=True, verbose=self.verbose, appname=self.appname)

        if self.verbose > 1:
            LOG.debug(
                "Created %s object as dict:\n%s",
                group.__class__.__name__, pp(group.as_dict()))
        self.assertIsNone(group.config_file)
        self.assertIsNone(group.line_nr)
        self.assertTrue(group.simulate)
        self.assertEqual(len(group), 0)
        self.assertEqual(group.rotate_method, 'create')

        LOG.debug("Test setting rotation method to 'copy' ...")
        group.rotate_method = 'copy'
        self.assertEqual(group.rotate_method, 'copy')

        LOG.debug("Test setting rotation method to 'copytruncate' ...")
        group.rotate_method = 'CopyTruncate'
        self.assertEqual(group.rotate_method, 'copytruncate')

        LOG.debug("Test setting rotation method to an invalid method ...")
        with self.assertRaises(ValueError) as cm:
            group.rotate_method = 'bla'
        e = cm.exception
        LOG.debug("%s raised: %s", e.__class__.__name__, str(e))

    # -------------------------------------------------------------------------
    def test_pattern(self):

        LOG.info("Testing pattern handling of a LogFileGroup object ...")
        from logrotate.filegroup import LogFileGroup

        with self.assertRaises(TypeError) as cm:
            group = LogFileGroup(
                simulate=True, patterns=55, verbose=self.verbose, appname=self.appname)
        e = cm.exception
        LOG.debug("%s raised: %s", e.__class__.__name__, str(e))

        group = LogFileGroup(
            simulate=True, patterns="/var/log/a.log",
            verbose=self.verbose, appname=self.appname)

        group.add_pattern("/var/log/b.log")
        group.add_pattern("/var/log/a.log")
        group.add_pattern("/var/log/b.log")
        group.add_pattern("/var/log/c*.log")
        self.assertEqual(len(group.patterns), 3)
        if self.verbose > 2:
            LOG.debug("Injected logfile globbing pattern:\n%s", pp(group.patterns))

        wrong_pattern = (None, 12, False, object())

        for pattern in wrong_pattern:
            with self.assertRaises(ValueError) as cm:
                ret = group.add_pattern(pattern)
            e = cm.exception
            LOG.debug("%s raised: %s", e.__class__.__name__, str(e))

    # -------------------------------------------------------------------------
    def test_filelist(self):

        LOG.info("Testing manipulation of the file list of a LogFileGroup object ...")
        from logrotate.filegroup import LogFileGroup

        group = LogFileGroup(
            simulate=True, patterns="/var/log/a.log",
            verbose=self.verbose, appname=self.appname)

        group.append("/var/log/a.log")
        group.append("/var/log/b.log")
        self.assertEqual(len(group), 2)

        if "/var/log/c.log" not in group:
            group.append("/var/log/c.log")
        self.assertIn("/var/log/c.log", group)
        self.assertEqual(len(group), 3)

        del group[0]
        if self.verbose > 2:
            LOG.debug(
                "Created %s object as dict:\n%s",
                group.__class__.__name__, pp(group.as_dict()))
        for filename in group:
            LOG.debug("Group has file %r.", filename)
        self.assertEqual(group[0], "/var/log/b.log")
        self.assertEqual(group[1], "/var/log/c.log")
        self.assertEqual(len(group), 2)

# =============================================================================

if __name__ == '__main__':

    verbose = get_arg_verbose()
    if verbose is None:
        verbose = 0
    init_root_logger(verbose)

    LOG.info("Starting tests ...")

    suite = unittest.TestSuite()

    suite.addTest(LogFileGroupTestCase('test_import', verbose))
    suite.addTest(LogFileGroupTestCase('test_define_taboo_pattern', verbose))
    suite.addTest(LogFileGroupTestCase('test_object', verbose))
    suite.addTest(LogFileGroupTestCase('test_pattern', verbose))
    suite.addTest(LogFileGroupTestCase('test_filelist', verbose))

    runner = unittest.TextTestRunner(verbosity=verbose)

    result = runner.run(suite)


# =============================================================================

# vim: tabstop=4 expandtab shiftwidth=4 softtabstop=4
