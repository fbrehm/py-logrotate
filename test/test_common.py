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

from fb_tools.common import pp

from general import BaseTestCase, get_arg_verbose, init_root_logger

LOG = logging.getLogger('test_common')

# =============================================================================
class TestCaseCommon(BaseTestCase):

    # -------------------------------------------------------------------------
    def setUp(self):
        pass

    # -------------------------------------------------------------------------
    def test_import(self):

        LOG.info("Testing import of logrotate.common ...")
        import logrotate.common                                         # noqa

    # -------------------------------------------------------------------------
    def test_split_parts(self):

        LOG.info("Testing split_parts() ...")

        from logrotate.common import split_parts
        from logrotate.common import UnbalancedQuotesError

        LOG.debug("Testing simple splitting ...")
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
                LOG.debug("Testing split_parts(%r) => %s", text, expected)
            result = split_parts(text)
            if self.verbose > 1:
                LOG.debug("Got result: %s", result)
            self.assertIsInstance(result, list)
            self.assertEqual(expected, result)

        LOG.debug("Testing splitting with keeping quoting characters ...")
        test_pairs = [
            ['Hello "bla" \'blub\'', ['Hello', '"bla"', "'blub'"]],
            ['"bla\'s blub" cries \'He says "Hello!"\'', ['"bla\'s blub"', 'cries', '\'He says "Hello!"\'']],
        ]

        for pair in test_pairs:
            text = pair[0]
            expected = pair[1]
            if self.verbose > 1:
                LOG.debug("Testing split_parts(%r) => %s", text, expected)
            result = split_parts(text, keep_quotes=True)
            if self.verbose > 1:
                LOG.debug("Got result: %s", result)
            self.assertIsInstance(result, list)
            self.assertEqual(expected, result)

        LOG.debug("Testing unbalanced quoting ...")
        text = "Hey bro's!"
        expected = ['Hey', "bro's!"]

        if self.verbose > 1:
            LOG.debug("Testing split_parts(%r) => %s", text, expected)
        result = split_parts(text, raise_on_unbalanced=False)
        if self.verbose > 1:
            LOG.debug("Got result: %s", result)
        self.assertIsInstance(result, list)
        self.assertEqual(expected, result)

        if self.verbose > 1:
            LOG.debug("Testing raising an exception on unbalanced quotings by %r", text)
        with self.assertRaises(UnbalancedQuotesError) as cm:
            result = split_parts(text)
        e = cm.exception
        LOG.debug("%s raised: %s", e.__class__.__name__, e)

    # -------------------------------------------------------------------------
    def test_email_valid(self):

        LOG.info("Testing email_valid() ...")

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
                LOG.debug("Testing email_valid(%r) => %s", address, expected)
            result = email_valid(address)
            if self.verbose > 1:
                LOG.debug("Got result: %s", result)
            self.assertIsInstance(result, bool)
            self.assertEqual(expected, result)

    # -------------------------------------------------------------------------
    def test_human2bytes(self):

        LOG.info("Testing human2bytes() from logrotate.common ...")

        from logrotate.common import human2bytes

        loc = locale.getlocale()    # get current locale
        encoding = loc[1]
        LOG.debug("Current locale is {!r}r.".format(loc))
        german = ('de_DE', encoding)                                # noqa

        do_switch_locales = True
        try:
            locale.setlocale(locale.LC_ALL, german)
        except Exception as e:
            LOG.warning("Got a {c}: {e}".format(c=e.__class__.__name__, e=e))
            do_switch_locales = False

        if do_switch_locales:
            LOG.debug("Setting to locale 'C' to be secure.")
            locale.setlocale(locale.LC_ALL, 'C')
            LOG.debug("Current locale is now %r.", locale.getlocale())

        test_pairs_int_si = (
            ('1048576', 1024 ** 2),
            ('1MiB', 1024 ** 2),
            ('1 MiB', 1024 ** 2),
            ('1 MiB', 1024 ** 2),
            (' 1 MiB	', 1024 ** 2),
            ('1.2 MiB', int(1.2 * (1024 ** 2))),
            ('1 GiB', 1024 ** 3),
            ('1 GB', 1000 ** 3),
            ('1.2 GiB', int(1.2 * (1024 ** 3))),
            ('102400 KB', 100 * (1024 ** 2)),
            ('100000 KB', 100000 * 1024),
            ('102400 MB', 1024 * 1000 * 1000 * 100),
            ('100000 MB', 1000 * 1000 * 1000 * 100),
            ('102400 MiB', 1024 * 100 * (1024 ** 2)),
            ('100000 MiB', 1000 * 100 * (1024 ** 2)),
            ('102400 GB', 1024 * 1000 * 1000 * 1000 * 100),
            ('100000 GB', 1000 * 1000 * 1000 * 1000 * 100),
            ('102400 GiB', 1024 * 1024 * 100 * (1024 ** 2)),
            ('100000 GiB', 1024 * 1000 * 100 * (1024 ** 2)),
            ('1024 TB', 1024 * (1000 ** 4)),
            ('1000 TB', 1000 * (1000 ** 4)),
            ('1024 TiB', 1024 ** 5),
            ('1000 TiB', 1000 * (1024 ** 4)),
            ('1024 PB', 1024 * (1000 ** 5)),
            ('1000 PB', 1000 * (1000 ** 5)),
            ('1024 PiB', 1024 ** 6),
            ('1000 PiB', 1000 * (1024 ** 5)),
            ('1024 EB', 1024 * (1000 ** 6)),
            ('1000 EB', 1000 * (1000 ** 6)),
            ('1024 EiB', 1024 ** 7),
            ('1000 EiB', 1000 * (1024 ** 6)),
        )

        for pair in test_pairs_int_si:

            src = pair[0]
            expected = pair[1]
            if self.verbose > 1:
                LOG.debug("Testing human2bytes(%r) => %d", src, expected)
            result = human2bytes(src, si_conform=True, verbose=self.verbose)
            if self.verbose > 1:
                LOG.debug("Got result: %r", result)
            if six.PY2:
                self.assertIsInstance(result, long)
            else:
                self.assertIsInstance(result, int)
            self.assertEqual(expected, result)

        # Switch back to saved locales
        if do_switch_locales:
            LOG.debug("Switching back to saved locales %r.", loc)
            locale.setlocale(locale.LC_ALL, loc)    # restore saved locale

    # -------------------------------------------------------------------------
    def test_human2bytes_l10n(self):

        LOG.info("Testing localisation of human2bytes() from logrotate.common ...")

        loc = locale.getlocale()    # get current locale
        encoding = loc[1]
        LOG.debug("Current locale is %r.", loc)
        german = ('de_DE', encoding)

        try:
            locale.setlocale(locale.LC_ALL, german)
        except Exception as e:
            LOG.warning("Got a {c}: {e}".format(c=e.__class__.__name__, e=e))
            return True

        LOG.debug("Setting to locale 'C' to be secure.")
        locale.setlocale(locale.LC_ALL, 'C')
        LOG.debug("Current locale is now %r.", locale.getlocale())

        from logrotate.common import human2bytes

        pairs_en = (
            ('1.2 GiB', int(1.2 * (1024 ** 3))),
            ('1.2 TiB', int(1.2 * (1024 ** 4))),
        )

        pairs_de = (
            ('1,2 GiB', int(1.2 * (1024 ** 3))),
            ('1,2 TiB', int(1.2 * (1024 ** 4))),
            ('1.024 MiB', 1024 ** 3),
            ('1.055,4 GiB', int(10554 * (1024 ** 3) / 10)),
        )

        LOG.debug("Testing english decimal radix character %r.", '.')
        for pair in pairs_en:
            src = pair[0]
            expected = pair[1]
            if self.verbose > 1:
                LOG.debug("Testing localisation of human2bytes(%r) => %d", src, expected)
            result = human2bytes(src, si_conform=True, use_locale_radix=True, verbose=self.verbose)
            if self.verbose > 1:
                LOG.debug("Got result: %r", result)
            self.assertIsInstance(result, int)
            self.assertEqual(expected, result)

        # Switch to german locales
        LOG.debug("Switching to german locale %r.", german)
        # use German locale; name might vary with platform
        locale.setlocale(locale.LC_ALL, german)
        LOG.debug("Current locale is now %r.", locale.getlocale())

        LOG.debug("Testing german decimal radix character %r.", ',')
        for pair in pairs_de:
            src = pair[0]
            expected = pair[1]
            if self.verbose > 1:
                LOG.debug("Testing localisation of human2bytes(%r) => %d", src, expected)
            result = human2bytes(src, si_conform=True, use_locale_radix=True, verbose=self.verbose)
            if self.verbose > 1:
                LOG.debug("Got result: %r", result)
            self.assertIsInstance(result, int)
            self.assertEqual(expected, result)

        # Switch back to english locales
        locale.setlocale(locale.LC_ALL, 'C')    # restore saved locale

        LOG.debug("Testing english decimal radix character %r again.", '.')
        for pair in pairs_en:
            src = pair[0]
            expected = pair[1]
            if self.verbose > 1:
                LOG.debug("Testing localisation of human2bytes(%r) => %d", src, expected)
            result = human2bytes(src, si_conform=True, use_locale_radix=True, verbose=self.verbose)
            if self.verbose > 1:
                LOG.debug("Got result: %r", result)
            self.assertIsInstance(result, int)
            self.assertEqual(expected, result)

        # Switch back to saved locales
        LOG.debug("Switching back to saved locales %r.", loc)
        locale.setlocale(locale.LC_ALL, loc)    # restore saved locale

    # -------------------------------------------------------------------------
    def test_period2days(self):

        LOG.info("Testing period2days() from logrotate.common ...")

        from logrotate.common import period2days

        test_pairs = (
            ('now', 0.0),
            ('never', float('inf')),
            ('1', 1.0),
            ('1d', 1.0),
            ('1day', 1.0),
            ('1 days', 1.0),
            ('1.1', 1.1),
            ('1.1 day', 1.1),
            ('1. bla', 1.0),
            ('blub', 0.0),
            ('2 weeks', 14.0),
            ('2 week 1d', 15.0),
            ('1day 2w', 15.0),
            ('2.5m 1', 76.0),
            ('0.4h', 1.0 / 24 * 0.4),
            ('1.3y 2.1m 1.1w 0.7d', 1.3 * 365.0 + 2.1 * 30.0 + 1.1 * 7.0 + 0.7),
        )

        for pair in test_pairs:
            text = pair[0]
            expected = pair[1]
            if self.verbose > 1:
                LOG.debug("Testing period2days(%r) => %r", text, expected)
            result = period2days(text, verbose=self.verbose)
            if self.verbose > 1:
                LOG.debug("Got result: %r", result)
            self.assertIsInstance(result, float)
            self.assertEqual(expected, result)

    # -------------------------------------------------------------------------
    def test_get_address_list(self):

        LOG.info("Testing get_address_list() from logrotate.common ...")

        from logrotate.common import get_address_list

        test_pairs = (
            ('', []),
            ('frank@brehm-online.com', [('', 'frank@brehm-online.com')]),
            ('<frank@brehm-online.com>', [('', 'frank@brehm-online.com')]),
            ('Frank Brehm <frank@brehm-online.com>', [('Frank Brehm', 'frank@brehm-online.com')]),
            ('"Frank Brehm" <frank@brehm-online.com>', [('Frank Brehm', 'frank@brehm-online.com')]),
            ('A B <a@b.de>, CD <c@d.com>', [
                ('A B', 'a@b.de'),
                ('CD', 'c@d.com'),
            ]),
        )

        for pair in test_pairs:
            text = pair[0]
            expected = pair[1]
            if self.verbose > 1:
                LOG.debug("Testing get_address_list(%r) => %r", text, expected)
            result = get_address_list(text, verbose=self.verbose)
            if self.verbose > 1:
                LOG.debug("Got result: %r", pp(result))
            self.assertIsInstance(result, list)
            self.assertEqual(expected, result)


# =============================================================================

if __name__ == '__main__':

    verbose = get_arg_verbose()
    if verbose is None:
        verbose = 0
    init_root_logger(verbose)

    LOG.info("Starting tests ...")

    suite = unittest.TestSuite()

    suite.addTest(TestCaseCommon('test_import', verbose))
    suite.addTest(TestCaseCommon('test_split_parts', verbose))
    suite.addTest(TestCaseCommon('test_email_valid', verbose))
    suite.addTest(TestCaseCommon('test_human2bytes', verbose))
    suite.addTest(TestCaseCommon('test_human2bytes_l10n', verbose))
    suite.addTest(TestCaseCommon('test_period2days', verbose))
    suite.addTest(TestCaseCommon('test_get_address_list', verbose))

    runner = unittest.TextTestRunner(verbosity=verbose)

    result = runner.run(suite)

# =============================================================================

# vim: tabstop=4 expandtab shiftwidth=4 softtabstop=4
