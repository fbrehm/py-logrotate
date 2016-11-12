#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
@author: Frank Brehm
@contact: frank@brehm-online.com
@copyright: © 2010 - 2016 by Frank Brehm, Berlin
@license: GPL3
@summary: test script (and module) for unit tests on LogRotateScript objects
"""

import os
import sys
import logging
import locale
import glob
import tempfile
import textwrap

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

APPNAME = 'test_script'
LOG = logging.getLogger(APPNAME)


# =============================================================================
class ScriptTestCase(BaseTestCase):

    # -------------------------------------------------------------------------
    def setUp(self):

        super(ScriptTestCase, self).setUp()
        self.appname = APPNAME

    # -------------------------------------------------------------------------
    def test_import(self):

        LOG.info("Testing import of logrotate.script ...")
        import logrotate.script                                          # noqa

    # -------------------------------------------------------------------------
    def test_object(self):

        LOG.info("Testing creating a new LogRotateScript object ...")
        from logrotate.script import LogRotateScript

        sname = 'TestScript'
        cmd = 'ls -l --color=always'

        script = LogRotateScript(
            name=sname, simulate=True, commands=cmd,
            verbose=self.verbose, appname=self.appname)
        if self.verbose > 1:
            LOG.debug(
                "Created %s object as dict:\n%s",
                script.__class__.__name__, pp(script.as_dict()))
        self.assertEqual(script.name, sname)
        self.assertTrue(script.simulate)
        self.assertEqual(len(script), 1)
        self.assertEqual(script[0], cmd)

# =============================================================================

if __name__ == '__main__':

    verbose = get_arg_verbose()
    if verbose is None:
        verbose = 0
    init_root_logger(verbose)

    LOG.info("Starting tests ...")

    suite = unittest.TestSuite()

    suite.addTest(ScriptTestCase('test_import', verbose))
    suite.addTest(ScriptTestCase('test_object', verbose))

    runner = unittest.TextTestRunner(verbosity=verbose)

    result = runner.run(suite)


# =============================================================================

# vim: tabstop=4 expandtab shiftwidth=4 softtabstop=4
