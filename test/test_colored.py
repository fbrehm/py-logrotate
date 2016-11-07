#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
@author: Frank Brehm
@contact: frank@brehm-online.com
@copyright: © 2010 - 2016 by Frank Brehm, Berlin
@license: GPL3
@summary: test script (and module) for unit tests on color_log.py
"""

from __future__ import print_function

import os
import sys
import logging
import locale

try:
    import unittest2 as unittest
except ImportError:
    import unittest

import six

libdir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'lib'))
sys.path.insert(0, libdir)

from general import BaseTestCase, get_arg_verbose, init_root_logger

log = logging.getLogger('test_colored')


# =============================================================================
class TestCaseColored(BaseTestCase):

    # -------------------------------------------------------------------------
    def setUp(self):
        pass

    # -------------------------------------------------------------------------
    def test_import(self):

        log.info("Testing import of logrotate.color_log ...")
        import logrotate.color_log                                       # noqa

        from logrotate.color_log import Colorer

        print("\nAll available text colors:")
        for color in Colorer.valid_textcolors:
            print(" * %s" % (color))

        print("\nAll available background colors:")
        for color in Colorer.valid_bgcolors:
            print(" * %s" % (color))

        print("\nAll available color attributes:")
        for attr in Colorer.valid_attrs:
            print(" * %s" % (attr))

        print("\n")

    #--------------------------------------------------------------------------
    def test_colorcode(self):

        log.info("Testing colored output ...")

        from logrotate.color_log import Colorer

        msg = "Colored output"

        print("\nAll available text colors:")
        for color in Colorer.valid_textcolors:
            col = Colorer(color)
            print(" * %r: %s" % (color, col.coloring(msg)))

        print("\nAll available background colors:")
        for color in Colorer.valid_bgcolors:
            col = Colorer(bg_color=color)
            print(" * %r: %s" % (color, col.coloring(msg)))

        print("\nAll available color attributes:")
        for attr in Colorer.valid_attrs:
            col = Colorer(attrs=attr)
            print(" * %r: %s" % (attr, col.coloring(msg)))

        print("\n")

    #--------------------------------------------------------------------------
    def test_object(self):

        log.info("Testing init of a ColoredFormatter object ...")

        from logrotate.color_log import ColoredFormatter

        formatter = ColoredFormatter(
                '%(name)s: %(message)s (%(filename)s:%(lineno)d)')

        print("\nAll available level colorer:")
        for level in formatter.level_color:
            col = formatter.level_color[level]
            print(" * %r: %r" % (level, col))
        print("\nBold colorer: %r" % (formatter.bold))
        print("\n")

    # -------------------------------------------------------------------------
    def test_colored_logging(self):

        log.info("Testing logging with a ColoredFormatter object ...")

        from logrotate.color_log import ColoredFormatter

        fmt_str = '%(name)s: %(message)s (%(filename)s:%(lineno)d)'
        test_logger = logging.getLogger('test.colored_logging')

        orig_handlers = []
        for log_handler in test_logger.handlers:
            orig_handlers.append(log_handler)
            test_logger.removeHandler(log_handler)

        try:
            c_formatter = ColoredFormatter(fmt_str)
            lh_console = logging.StreamHandler(sys.stdout)
            lh_console.setLevel(logging.DEBUG)
            lh_console.setFormatter(c_formatter)
            test_logger.addHandler(lh_console)

            test_logger.debug('debug message')
            test_logger.info('info message')
            test_logger.warning('Warning message')
            test_logger.error('ERROR - something seriously happened.')
            test_logger.critical("CRITICAL!!! I'am dying!")

        finally:
            for log_handler in test_logger.handlers:
                test_logger.removeHandler(log_handler)
            for log_handler in orig_handlers:
                test_logger.addHandler(log_handler)

    # -------------------------------------------------------------------------
    def test_dark_colored_logging(self):

        log.info("Testing logging with a ColoredFormatter object with dark colors ...")

        from logrotate.color_log import ColoredFormatter

        fmt_str = '%(name)s: %(message)s (%(filename)s:%(lineno)d)'
        test_logger = logging.getLogger('test.colored_logging')

        orig_handlers = []
        for log_handler in test_logger.handlers:
            orig_handlers.append(log_handler)
            test_logger.removeHandler(log_handler)

        try:
            c_formatter = ColoredFormatter(fmt_str, dark=True)
            lh_console = logging.StreamHandler(sys.stdout)
            lh_console.setLevel(logging.DEBUG)
            lh_console.setFormatter(c_formatter)
            test_logger.addHandler(lh_console)

            test_logger.debug('debug message')
            test_logger.info('info message')
            test_logger.warning('Warning message')
            test_logger.error('ERROR - something seriously happened.')
            test_logger.critical("CRITICAL!!! I'am dying!")

        finally:
            for log_handler in test_logger.handlers:
                test_logger.removeHandler(log_handler)
            for log_handler in orig_handlers:
                test_logger.addHandler(log_handler)


# =============================================================================

if __name__ == '__main__':

    verbose = get_arg_verbose()
    if verbose is None:
        verbose = 0
    init_root_logger(verbose)

    log.info("Starting tests ...")

    suite = unittest.TestSuite()

    suite.addTest(TestCaseColored('test_import', verbose))
    suite.addTest(TestCaseColored('test_colorcode', verbose))
    suite.addTest(TestCaseColored('test_object', verbose))
    suite.addTest(TestCaseColored('test_colored_logging', verbose))
    suite.addTest(TestCaseColored('test_dark_colored_logging', verbose))

    runner = unittest.TextTestRunner(verbosity=verbose)

    result = runner.run(suite)

# =============================================================================

# vim: tabstop=4 expandtab shiftwidth=4 softtabstop=4
