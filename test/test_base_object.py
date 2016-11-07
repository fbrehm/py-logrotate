#!/usr/bin/env python3
# -*- coding: utf-8 -*-
'''
@author: Frank Brehm
@contact: frank@brehm-online.com
@copyright: © 2010 - 2016 by Frank Brehm, Berlin
@license: GPL3
@summary: test script (and module) for unit tests on base object
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

from general import BaseTestCase, get_arg_verbose, init_root_logger

log = logging.getLogger('test_base_object')


# =============================================================================
class TestBaseObject(BaseTestCase):

    # -------------------------------------------------------------------------
    def setUp(self):
        pass

    # -------------------------------------------------------------------------
    def test_import(self):

        log.info("Testing import of logrotate.base ...")
        import logrotate.base                                           # noqa

    # -------------------------------------------------------------------------
    def test_object(self):

        log.info("Testing init of a simple object.")

        from logrotate.base import BaseObject

        obj = BaseObject(
            appname='test_base_object',
            verbose=self.verbose,
        )
        log.debug("PbBaseObject %%r: %r", obj)
        log.debug("PbBaseObject %%s: %s", str(obj))

    # -------------------------------------------------------------------------
    def test_verbose1(self):

        log.info("Testing wrong verbose values #1.")

        from logrotate.base import BaseObject

        v = 'hh'
        obj = None

        with self.assertRaises(ValueError) as cm:
            obj = BaseObject(appname='test_base_object', verbose=v)   # noqa
        e = cm.exception
        log.debug("ValueError raised on verbose = %r: %s", v, str(e))

    # -------------------------------------------------------------------------
    def test_verbose2(self):

        log.info("Testing wrong verbose values #2.")

        from logrotate.base import BaseObject

        v = -2
        obj = None

        with self.assertRaises(ValueError) as cm:
            obj = BaseObject(appname='test_base_object', verbose=v)   # noqa
        e = cm.exception
        log.debug("ValueError raised on verbose = %r: %s", v, str(e))

    # -------------------------------------------------------------------------
    def test_basedir1(self):

        bd = '/blablub'
        log.info("Testing #1 wrong basedir: %r", bd)

        from logrotate.base import BaseObject

        obj = BaseObject(appname='test_base_object', base_dir=bd)     # noqa

    # -------------------------------------------------------------------------
    def test_basedir2(self):

        bd = '/etc/passwd'
        log.info("Testing #2 wrong basedir: %r", bd)

        from logrotate.base import BaseObject

        obj = BaseObject(appname='test_base_object', base_dir=bd)     # noqa

    # -------------------------------------------------------------------------
    def test_as_dict1(self):

        log.info("Testing obj.as_dict() #1 - simple")

        from logrotate.base import BaseObject

        obj = BaseObject(appname='test_base_object', verbose=1)

        di = obj.as_dict()
        log.debug("Got BaseObject.as_dict(): %r", di)
        self.assertIsInstance(di, dict)

    # -------------------------------------------------------------------------
    def test_as_dict2(self):

        log.info("Testing obj.as_dict() #2 - stacked")

        from logrotate.base import BaseObject

        obj = BaseObject(appname='test_base_object', verbose=1)
        obj.obj2 = BaseObject(appname='test_base_object2', verbose=1)

        di = obj.as_dict()
        log.debug("Got BaseObject.as_dict(): %r", di)
        self.assertIsInstance(di, dict)
        self.assertIsInstance(obj.obj2.as_dict(), dict)

    # -------------------------------------------------------------------------
    def test_as_dict3(self):

        log.info("Testing obj.as_dict() #3 - typecasting to str")

        from logrotate.base import BaseObject

        obj = BaseObject(appname='test_base_object', verbose=1)
        obj.obj2 = BaseObject(appname='test_base_object2', verbose=1)

        out = str(obj)
        self.assertIsInstance(out, str)
        log.debug("Got str(BaseObject): %s", out)

# =============================================================================

if __name__ == '__main__':

    verbose = get_arg_verbose()
    if verbose is None:
        verbose = 0
    init_root_logger(verbose)

    log.info("Starting tests ...")

    suite = unittest.TestSuite()

    suite.addTest(TestBaseObject('test_import', verbose))
    suite.addTest(TestBaseObject('test_object', verbose))
    suite.addTest(TestBaseObject('test_verbose1', verbose))
    suite.addTest(TestBaseObject('test_verbose2', verbose))
    suite.addTest(TestBaseObject('test_basedir1', verbose))
    suite.addTest(TestBaseObject('test_basedir2', verbose))
    suite.addTest(TestBaseObject('test_as_dict1', verbose))
    suite.addTest(TestBaseObject('test_as_dict2', verbose))
    suite.addTest(TestBaseObject('test_as_dict3', verbose))

    runner = unittest.TextTestRunner(verbosity=verbose)

    result = runner.run(suite)


# =============================================================================

# vim: tabstop=4 expandtab shiftwidth=4 softtabstop=4
