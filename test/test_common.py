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

import six

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

    # -------------------------------------------------------------------------
    def test_to_unicode(self):

        log.info("Testing to_unicode_or_bust() ...")

        from logrotate.common import to_unicode_or_bust

        data = []
        data.append((None, None))
        data.append((1, 1))

        if six.PY2:
            data.append((u'a', u'a'))
            data.append(('a', u'a'))
        else:
            data.append(('a', 'a'))
            data.append((b'a', 'a'))

        for pair in data:

            src = pair[0]
            tgt = pair[1]
            result = to_unicode_or_bust(src)
            log.debug(
                "Testing to_unicode_or_bust(%r) => %r, result %r",
                src, tgt, result)

            if six.PY2:
                if isinstance(src, (str, unicode)):
                    self.assertIsInstance(result, unicode)
                else:
                    self.assertNotIsInstance(result, (str, unicode))
            else:
                if isinstance(src, (str, bytes)):
                    self.assertIsInstance(result, str)
                else:
                    self.assertNotIsInstance(result, (str, bytes))

            self.assertEqual(tgt, result)

    # -------------------------------------------------------------------------
    def test_to_utf8(self):

        log.info("Testing to_utf8_or_bust() ...")

        from logrotate.common import to_utf8_or_bust

        data = []
        data.append((None, None))
        data.append((1, 1))

        if six.PY2:
            data.append((u'a', 'a'))
            data.append(('a', 'a'))
        else:
            data.append(('a', b'a'))
            data.append((b'a', b'a'))

        for pair in data:

            src = pair[0]
            tgt = pair[1]
            result = to_utf8_or_bust(src)
            log.debug(
                "Testing to_utf8_or_bust(%r) => %r, result %r",
                src, tgt, result)

            if six.PY2:
                if isinstance(src, (str, unicode)):
                    self.assertIsInstance(result, str)
                else:
                    self.assertNotIsInstance(result, (str, unicode))
            else:
                if isinstance(src, (str, bytes)):
                    self.assertIsInstance(result, bytes)
                else:
                    self.assertNotIsInstance(result, (str, bytes))

            self.assertEqual(tgt, result)

    # -------------------------------------------------------------------------
    def test_to_str(self):

        log.info("Testing to_str_or_bust() ...")

        from logrotate.common import to_str_or_bust

        data = []
        data.append((None, None))
        data.append((1, 1))

        if six.PY2:
            data.append((u'a', 'a'))
            data.append(('a', 'a'))
        else:
            data.append(('a', 'a'))
            data.append((b'a', 'a'))

        for pair in data:

            src = pair[0]
            tgt = pair[1]
            result = to_str_or_bust(src)
            log.debug(
                "Testing to_str_or_bust(%r) => %r, result %r",
                src, tgt, result)

            if six.PY2:
                if isinstance(src, (str, unicode)):
                    self.assertIsInstance(result, str)
                else:
                    self.assertNotIsInstance(result, (str, unicode))
            else:
                if isinstance(src, (str, bytes)):
                    self.assertIsInstance(result, str)
                else:
                    self.assertNotIsInstance(result, (str, bytes))

            self.assertEqual(tgt, result)

    # -------------------------------------------------------------------------
    def test_split_parts(self):

        log.info("Testing split_parts() ...")

        from logrotate.common import split_parts
        from logrotate.common import UnbalancedQuotesError

        log.debug("Testing simple splitting ...")
        test_pairs = [
            ['', []],
            ['single_word', ['single_word']],
            ['two words', ['two', 'words']],
            ['some utf-8 characters: äöü ÄÖÜ »ß€€«', ['some', 'utf-8', 'characters:', 'äöü', 'ÄÖÜ', '»ß€€«']],
            [' two\twords ', ['two', 'words']],
            ['	three words \nthere\n', ['three', 'words', 'there']],
            ['"bla" \'blub\'', ['bla', 'blub']],
            ['"bla\'s blub" \'He says "Hello!"\'', ["bla's blub", 'He says "Hello!"']],
        ]

        for pair in test_pairs:
            text = pair[0]
            expected = pair[1]
            if self.verbose > 1:
                log.debug("Testing split_parts(%r) => %s", text, expected)
            result = split_parts(text)
            if self.verbose > 1:
                log.debug("Got result: %s", result)
            self.assertIsInstance(result, list)
            self.assertEqual(expected, result)

        log.debug("Testing splitting with keeping quoting characters ...")
        test_pairs = [
            ['Hello "bla" \'blub\'', ['Hello', '"bla"', "'blub'"]],
            ['"bla\'s blub" cries \'He says "Hello!"\'', ['"bla\'s blub"', 'cries', '\'He says "Hello!"\'']],
        ]

        for pair in test_pairs:
            text = pair[0]
            expected = pair[1]
            if self.verbose > 1:
                log.debug("Testing split_parts(%r) => %s", text, expected)
            result = split_parts(text, keep_quotes=True)
            if self.verbose > 1:
                log.debug("Got result: %s", result)
            self.assertIsInstance(result, list)
            self.assertEqual(expected, result)

        log.debug("Testing unbalanced quoting ...")
        text = "Hey bro's!"
        expected = ['Hey', "bro's!"]

        if self.verbose > 1:
            log.debug("Testing split_parts(%r) => %s", text, expected)
        result = split_parts(text, raise_on_unbalanced=False)
        if self.verbose > 1:
            log.debug("Got result: %s", result)
        self.assertIsInstance(result, list)
        self.assertEqual(expected, result)

        if self.verbose > 1:
            log.debug("Testing raising an exception on unbalanced quotings by %r", text)
        with self.assertRaises(UnbalancedQuotesError) as cm:
            result = split_parts(text)
        e = cm.exception
        log.debug("%s raised: %s", e.__class__.__name__, e)

    # -------------------------------------------------------------------------
    def test_email_valid(self):

        log.info("Testing email_valid() ...")

        from logrotate.common import email_valid

        test_pairs = [
            [None, False],
            ['', False],
            ['  ', False],
            [' uhu ', False],
            ['1@2.d', False],
            ['1@2.33', False],
            ['1@2.de', True],
            ['1@2.defghijklmnopqrst', False],
            ['@2.de', False],
        ]

        for pair in test_pairs:
            address = pair[0]
            expected = pair[1]
            if self.verbose > 1:
                log.debug("Testing email_valid(%r) => %s", address, expected)
            result = email_valid(address)
            if self.verbose > 1:
                log.debug("Got result: %s", result)
            self.assertIsInstance(result, bool)
            self.assertEqual(expected, result)

# =============================================================================

if __name__ == '__main__':

    verbose = get_arg_verbose()
    if verbose is None:
        verbose = 0
    init_root_logger(verbose)

    log.info("Starting tests ...")

    suite = unittest.TestSuite()

    suite.addTest(TestCaseCommon('test_import', verbose))
    suite.addTest(TestCaseCommon('test_to_unicode', verbose))
    suite.addTest(TestCaseCommon('test_to_utf8', verbose))
    suite.addTest(TestCaseCommon('test_to_str', verbose))
    suite.addTest(TestCaseCommon('test_split_parts', verbose))
    suite.addTest(TestCaseCommon('test_email_valid', verbose))
    # suite.addTest(TestCaseCommon('test_human2mbytes', verbose))
    # suite.addTest(TestCaseCommon('test_human2mbytes_l10n', verbose))
    # suite.addTest(TestCaseCommon('test_bytes2human', verbose))
    # suite.addTest(TestCaseCommon('test_to_bool', verbose))

    runner = unittest.TextTestRunner(verbosity=verbose)

    result = runner.run(suite)

# =============================================================================

# vim: tabstop=4 expandtab shiftwidth=4 softtabstop=4
