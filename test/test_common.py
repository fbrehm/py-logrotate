#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
@author: Frank Brehm
@contact: frank@brehm-online.com
@copyright: © 2010 - 2016 by Frank Brehm, Berlin
@license: GPL3
@summary: test script (and module) for unit tests on common.py
"""

import os
import sys
import logging
import locale

try:
    import unittest2 as unittest
except ImportError:
    import unittest

# Setting the user’s preferred locale settings
locale.setlocale(locale.LC_ALL, '')

libdir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'lib'))
sys.path.insert(0, libdir)

from general import BaseTestCase, get_arg_verbose, init_root_logger

log = logging.getLogger('test_common')

# =============================================================================
class TestCaseCommon(BaseTestCase):

    # -------------------------------------------------------------------------
    def setUp(self):
        pass

    # -------------------------------------------------------------------------
    def test_import(self):

        log.info("Testing import of logrotate.common ...")
        import logrotate.common                                         # noqa


# =============================================================================

if __name__ == '__main__':

    verbose = get_arg_verbose()
    if verbose is None:
        verbose = 0
    init_root_logger(verbose)

    log.info("Starting tests ...")

    suite = unittest.TestSuite()

    suite.addTest(TestCaseCommon('test_import', verbose))
    # suite.addTest(TestCaseCommon('test_to_unicode', verbose))
    # suite.addTest(TestCaseCommon('test_to_utf8', verbose))
    # suite.addTest(TestCaseCommon('test_to_str', verbose))
    # suite.addTest(TestCaseCommon('test_human2mbytes', verbose))
    # suite.addTest(TestCaseCommon('test_human2mbytes_l10n', verbose))
    # suite.addTest(TestCaseCommon('test_bytes2human', verbose))
    # suite.addTest(TestCaseCommon('test_to_bool', verbose))

    runner = unittest.TextTestRunner(verbosity=verbose)

    result = runner.run(suite)

# =============================================================================

# vim: tabstop=4 expandtab shiftwidth=4 softtabstop=4
