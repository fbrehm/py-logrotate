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
    #suite.addTest(LogFileGroupTestCase('test_object', verbose))

    runner = unittest.TextTestRunner(verbosity=verbose)

    result = runner.run(suite)


# =============================================================================

# vim: tabstop=4 expandtab shiftwidth=4 softtabstop=4
