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

from datetime import tzinfo, timedelta, datetime, date, time

try:
    import unittest2 as unittest
except ImportError:
    import unittest

# Third party modules
import six

# Setting the user’s preferred locale settings
locale.setlocale(locale.LC_ALL, '')

libdir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'lib'))
sys.path.insert(0, libdir)

# Own modules
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
        self.assertEqual(entry_str, '~ ~')

        entry_str = entry.get_line(10)
        LOG.debug("Status entry as str: %r", entry_str)
        self.assertEqual(entry_str, '~          ~')

    # -------------------------------------------------------------------------
    def test_initialized_entry(self):

        LOG.info("Testing status entries with values ...")
        from logrotate.status import StatusFileEntry

        fn = '/a.log'
        fn_normal = '/var/log/messages'
        fn_ws = '/var/log/strange whatever.log'
        fn_utf8 = '/var/log/strange-»äöüÄÖÜß€ß«.log'
        fn_squot = "/var/log/'bla.log"
        fn_dquot = '/var/log/"blub.log'

        ts_d = date(2016, 1, 1)
        ts_dt = datetime(2016, 2, 2, 3, 14, 25)
        ts_d_str = '2015-1-3'
        ts_dt_str1 = '2014-04-05 03:44:11'
        ts_dt_str2 = '2014-04-05_03-44-22'
        ts_dt_str3 = '2014-04-05-03-44-33'
        ts_d_wrong1 = '2015-2-30'
        ts_d_wrong2 = 'bla'
        ts_dt_wrong1 = '2011-2-30 03:44:11'
        ts_dt_wrong2 = '2011-2-30 03:44:22'
        ts_dt_wrong3 = '2011-2-28 33:44:33'

        class TestDateOut(object):

            def __init__(self, text):
                self.text = text

            def __str__(self):
                return self.text

            def __repr__(self):
                return  "<%s(text=%r)>" % (self.__class__.__name__, self.text)

        ts_obj_d = TestDateOut('2014-4-1')
        ts_obj_dt = TestDateOut('2014-04-03 03:44:11')

        valid_test_data = (
            (fn, ts_d, '/a.log 2016-01-01_00:00:00'),
            (fn_normal, ts_d, '/var/log/messages 2016-01-01_00:00:00'),
            (fn_ws, ts_d, '\'/var/log/strange whatever.log\' 2016-01-01_00:00:00'),
            (fn_utf8, ts_d, '\'/var/log/strange-»äöüÄÖÜß€ß«.log\' 2016-01-01_00:00:00'),
            (fn_squot, ts_d, '\'/var/log/\'"\'"\'bla.log\' 2016-01-01_00:00:00'),
            (fn_dquot, ts_d, '\'/var/log/"blub.log\' 2016-01-01_00:00:00'),
            (fn, ts_dt, '/a.log 2016-02-02_03:14:25'),
            (fn, ts_d_str, '/a.log 2015-01-03_00:00:00'),
            (fn, ts_dt_str1, '/a.log 2014-04-05_03:44:11'),
            (fn, ts_dt_str2, '/a.log 2014-04-05_03:44:22'),
            (fn, ts_dt_str3, '/a.log 2014-04-05_03:44:33'),
            (fn, ts_obj_d, '/a.log 2014-04-01_00:00:00'),
            (fn, ts_obj_dt, '/a.log 2014-04-03_03:44:11'),
        )

        LOG.debug("Testing valid initialisation data ...")
        for data in valid_test_data:
            exp_val = data[2]
            if self.verbose > 1:
                LOG.debug(
                    "Testing StatusFileEntry(filename=%r,  ts=%r) ...",
                    data[0], data[1])
                LOG.debug("Expected result: %r", exp_val)
            entry = StatusFileEntry(
                filename=data[0], ts=data[1],
                verbose=self.verbose, appname=self.appname)
            entry_str = str(entry)
            if self.verbose > 2:
                LOG.debug("Created status entry as dict:\n%s", pp(entry.as_dict()))
            if self.verbose > 1:
                LOG.debug("String of status entry: %r", entry_str)
            self.assertEqual(entry_str, exp_val)

        invalid_test_data = (
            (fn, ts_d_wrong1),
            (fn, ts_d_wrong2),
            (fn, ts_dt_wrong1),
            (fn, ts_dt_wrong2),
            (fn, ts_dt_wrong3),
        )
        LOG.debug("Testing invalid initialisation data ...")
        for data in invalid_test_data:
            if self.verbose > 1:
                LOG.debug(
                    "Testing StatusFileEntry(filename=%r,  ts=%r) ...",
                    data[0], data[1])
            with self.assertRaises(ValueError) as cm:
                entry = StatusFileEntry(
                    filename=data[0], ts=data[1],
                    verbose=self.verbose, appname=self.appname)
            e = cm.exception
            LOG.debug("%s raised: %s", e.__class__.__name__, str(e))


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
    suite.addTest(StatusTestCase('test_initialized_entry', verbose))

    runner = unittest.TextTestRunner(verbosity=verbose)

    result = runner.run(suite)


# =============================================================================

# vim: tabstop=4 expandtab shiftwidth=4 softtabstop=4
