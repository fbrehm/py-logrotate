#!/usr/bin/env python3
# -*- coding: utf-8 -*-
'''
@author: Frank Brehm
@contact: frank@brehm-online.com
@copyright: © 2010 - 2016 by Frank Brehm, Berlin
@license: GPL3
@summary: test script (and module) for unit tests
          on status file and status entry objects
'''

import os
import sys
import logging
import locale

try:
    import unittest2 as unittest
except ImportError:
    import unittest

import six

# Setting the user’s preferred locale settings
locale.setlocale(locale.LC_ALL, '')

libdir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'lib'))
sys.path.insert(0, libdir)

from logrotate.common import pp

from general import BaseTestCase, get_arg_verbose, init_root_logger

APPNAME = 'test_shadow'
LOG = logging.getLogger(APPNAME)


# =============================================================================
class StatusTestCase(BaseTestCase):

    # -------------------------------------------------------------------------
    def setUp(self):

        super(StatusTestCase, self).setUp()
        self.appname = APPNAME
        self.test_dir = os.path.join(self.base_dir, 'test')

    # -------------------------------------------------------------------------
    def test_import(self):

        LOG.info("Testing import of logrotate.status ...")
        import logrotate.status                                          # noqa

    # -------------------------------------------------------------------------
    def test_empty_entry(self):

        LOG.info("Testing an empty status entry ...")
        from logrotate.status import StatusFileEntry

        entry = StatusFileEntry(verbose=self.verbose, appname=self.appname)
        if self.verbose > 1:
            LOG.debug("Created status entry as dict:\n%s", pp(entry.as_dict()))
        entry_str = str(entry)
        LOG.debug("Created status entry as str: %r", entry_str)
        self.assertEqual(entry_str, '~ "~"')


# =============================================================================

if __name__ == '__main__':

    verbose = get_arg_verbose()
    if verbose is None:
        verbose = 0
    init_root_logger(verbose)

    LOG.info("Starting tests ...")

    suite = unittest.TestSuite()

    suite.addTest(StatusTestCase('test_import', verbose))
    suite.addTest(StatusTestCase('test_empty_entry', verbose))

    runner = unittest.TextTestRunner(verbosity=verbose)

    result = runner.run(suite)


# =============================================================================

# vim: tabstop=4 expandtab shiftwidth=4 softtabstop=4
