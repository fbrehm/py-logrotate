#!/usr/bin/env python
# -*- coding: utf-8 -*-

# $Id$
# $URL$

'''
@author: Frank Brehm
@contact: frank@brehm-online.com
@license: GPL3
@copyright: (c) 2010-2011 by Frank Brehm, Berlin
@version: 0.1.0
@summary: Module for common used functions
'''

import re
import sys
import locale
import logging
import gettext
import csv
import pprint
import email.utils

revision = '$Revision$'
revision = re.sub( r'\$', '', revision )
revision = re.sub( r'Revision: ', r'r', revision )
revision = re.sub( r'\s*$', '', revision )

__author__    = 'Frank Brehm'
__copyright__ = '(C) 2011 by Frank Brehm, Berlin'
__contact__    = 'frank@brehm-online.com'
__version__    = '0.1.0 ' + revision
__license__    = 'GPL3'


logger = logging.getLogger('pylogrotate.common')
locale_dir = None

#========================================================================

def split_parts( text, keep_quotes = False, raise_on_unbalanced = True):
    '''
    Split the given text in chunks by whitespaces or
    single or double quoted strings.
        
    @param text:        the text to split in chunks
    @type text:         str
    @param keep_quotes: keep quotes of quoted chunks
    @type keep_quotes:  bool
    @param raise_on_unbalanced: raise an exception on
                                unbalanced quotes
    @type raise_on_unbalanced:  bool

    @return: list of chunks
    @rtype:  list
    '''

    chunks = []
    if text is None:
        return chunks

    txt = str(text)
    last_chunk = ''

    # Big loop to split the text - until it is empty
    while txt != '':

        # add chunk, if there is a chunk left and a whitspace
        # at the begin of the line
        match = re.search(r"\s+", txt)
        if ( last_chunk != '' ) and match:
            chunks.append(last_chunk)
            last_chunk = ''

        # clean the line
        txt = txt.strip()
        if txt == '':
            break

        # search for a single quoted string at the begin of the line
        match = re.search(r"^'((?:\\'|[^'])*)'", txt)
        if match:
            chunk = match.group(1)
            chunk = re.sub(r"\\'", "'", chunk)
            if keep_quotes:
                chunk = "'" + chunk + "'"
            last_chunk += chunk
            txt = re.sub(r"^'(?:\\'|[^'])*'", "", txt)
            continue

        # search for a double quoted string at the begin of the line
        match = re.search(r'^"((?:\\"|[^"])*)"', txt)
        if match:
            chunk = match.group(1)
            chunk = re.sub(r'\\"', '"', chunk)
            if keep_quotes:
                chunk = '"' + chunk + '"'
            last_chunk += chunk
            txt = re.sub(r'^"(?:\\"|[^"])*"', "", txt)
            continue

        # search for unquoted, whitespace delimited text
        # at the begin of the line
        match = re.search(r'^((?:[^\s\'"]+|\\\'|\\")+)', txt)
        if match:
            last_chunk += match.group(1)
            txt = re.sub(r'^(?:[^\s\'"]+|\\\'|\\")+', "", txt)
            continue

        # Only whitespaces left
        match = re.search(r'^\s*$', txt)
        if match:
            break

        # Check for unbalanced quotes
        match = re.search(r'^([\'"].*)\s*', txt)
        if match:
            chunk = match.group(1)
            if raise_on_unbalanced:
                raise Exception("Unbalanced quotes in »%s«." % ( str(text) ) )
            else:
                last_chunk += chunk
                continue

        # Here we should not come to ...
        raise Exception("Broken split of »%s«: »%s« left" %( str(text), txt))

    if last_chunk != '':
        chunks.append(last_chunk)

    return chunks

#------------------------------------------------------------------------

def email_valid(address):
    '''
    Simple Check for E-Mail addresses

    @param address: the mail address to check
    @type address:  str

    @return: Validity of the given mil address
    @rtype:  bool
    '''

    if address is None:
        return False

    adr = str(address)
    if adr is None or adr == '':
        return False

    pattern = r'^[a-z0-9._%-+]+@[a-z0-9._%-]+.[a-z]{2,6}$'
    if re.search(pattern, adr, re.IGNORECASE) is None:
        return False

    return True

#------------------------------------------------------------------------

def human2bytes(value, si_conform = True, use_locale_radix = False, verbose = 0):
    '''
    Converts the given human readable byte value (e.g. 5MB, 8.4GiB etc.)
    with a prefix into an integer/long value (without a prefix).
    It raises a ValueError on invalid values.

    Available prefixes are:
        - kB (1000), KB (1024), KiB (1024)
        - MB (1000*1000), MiB (1024*1024)
        - GB (1000³), GiB (1024³)
        - TB (1000^4), TiB (1024^4)
        - PB (1000^5), PiB (1024^5)

    @param value:            the value to convert
    @type value:             str
    @param si_conform:       use factor 1000 instead of 1024 for kB a.s.o.
    @type si_conform:        bool
    @param use_locale_radix: use the locale version of radix instead of the
                             english decimal dot.
    @type use_locale_radix:  bool
    @param verbose:          level of verbosity
    @type verbose:           int

    @return: amount of bytes
    @rtype:  long
    '''

    t = gettext.translation('LogRotateCommon', locale_dir, fallback=True)
    _ = t.lgettext

    if value is None:
        msg = _("Given value is 'None'.")
        raise ValueError(msg)

    radix = '.'
    if use_locale_radix:
        radix = locale.RADIXCHAR
    radix = re.escape(radix)
    if verbose > 5:
        msg = _("using radix '%s'.") % (radix)
        logger.debug(msg)

    value_raw = ''
    prefix = None
    pattern = r'^\s*\+?(\d+(?:' + radix + r'\d*)?)\s*(\S+)?'
    match = re.search(pattern, value)
    if match is not None:
        value_raw = match.group(1)
        prefix = match.group(2)
    else:
        msg = _("Could not determine bytes in '%s'.") % (value)
        raise ValueError(msg)

    if use_locale_radix:
        value_raw = re.sub(radix, '.', value_raw, 1)
    value_float = float(value_raw)
    if prefix is None:
        prefix = ''

    factor_bin = long(1024)
    factor_si  = long(1000)
    if not si_conform:
        factor_si = factor_bin

    factor = long(1)

    if re.search(r'^\s*(?:b(?:yte)?)?\s*$', prefix, re.IGNORECASE):
        factor = long(1)
    elif re.search(r'^\s*k(?:[bB](?:[Yy][Tt][Ee])?)?\s*$', prefix):
        factor = factor_si
    elif re.search(r'^\s*Ki?(?:[bB](?:[Yy][Tt][Ee])?)?\s*$', prefix):
        factor = factor_bin
    elif re.search(r'^\s*M(?:B(?:yte)?)?\s*$', prefix, re.IGNORECASE):
        factor = (factor_si * factor_si)
    elif re.search(r'^\s*MiB(?:yte)?\s*$', prefix, re.IGNORECASE):
        factor = (factor_bin * factor_bin)
    elif re.search(r'^\s*G(?:B(?:yte)?)?\s*$', prefix, re.IGNORECASE):
        factor = (factor_si * factor_si * factor_si)
    elif re.search(r'^\s*GiB(?:yte)?\s*$', prefix, re.IGNORECASE):
        factor = (factor_bin * factor_bin * factor_bin)
    elif re.search(r'^\s*T(?:B(?:yte)?)?\s*$', prefix, re.IGNORECASE):
        factor = (factor_si * factor_si * factor_si * factor_si)
    elif re.search(r'^\s*TiB(?:yte)?\s*$', prefix, re.IGNORECASE):
        factor = (factor_bin * factor_bin * factor_bin * factor_bin)
    elif re.search(r'^\s*P(?:B(?:yte)?)?\s*$', prefix, re.IGNORECASE):
        factor = (factor_si * factor_si * factor_si * factor_si * factor_si)
    elif re.search(r'^\s*PiB(?:yte)?\s*$', prefix, re.IGNORECASE):
        factor = (factor_bin * factor_bin * factor_bin * factor_bin * factor_bin)
    else:
        msg = _("Couldn't detect prefix '%s'.") % (prefix)
        raise ValueError(msg)

    if verbose > 5:
        msg = _("Found factor %d.") % (factor)
        logger.debug(msg)

    return long(factor * value_float)

#------------------------------------------------------------------------

def period2days(period, use_locale_radix = False, verbose = 0):
    '''
    Converts the given string of the form »5d 8h« in an amount of days.
    It raises a ValueError on invalid values.

    Special values of period:
        - now (returns 0)
        - never (returns float('inf'))

    Valid units for periods are:
        - »h[ours]«
        - »d[ays]«   - default, if bare numbers are given
        - »w[eeks]«  - == 7 days
        - »m[onths]« - == 30 days
        - »y[ears]«  - == 365 days

    @param period:           the period to convert
    @type period:            str
    @param use_locale_radix: use the locale version of radix instead of the
                             english decimal dot.
    @type use_locale_radix:  bool
    @param verbose:          level of verbosity
    @type verbose:           int

    @return: amount of days
    @rtype:  float
    '''

    t = gettext.translation('LogRotateCommon', locale_dir, fallback=True)
    _ = t.lgettext

    if period is None:
        msg = _("Given period is 'None'.")
        raise ValueError(msg)

    value = str(period).strip().lower()
    if period == '':
        msg = _("Given period was empty")
        raise ValueError(msg)

    if verbose > 4:
        msg = _("Called with '%s'.") % (period)
        logger.debug(msg)

    if period == 'now':
        return float(0)

    # never - returns a positive infinite value
    if period == 'never':
        return float('inf')

    days = float(0)
    radix = '.'
    if use_locale_radix:
        radix = locale.RADIXCHAR
    radix = re.escape(radix)
    if verbose > 5:
        msg = _("Using radix '%s'.") % (radix)
        logger.debug(msg)

    # Search for hours in value
    pattern = r'(\d+(?:' + radix + r'\d*)?)\s*h(?:ours?)?'
    if verbose > 5:
        msg = _("Pattern '%s'.") % (pattern)
        logger.debug(msg)
    match = re.search(pattern, value, re.IGNORECASE)
    if match:
        hours_str = match.group(1)
        if use_locale_radix:
            hours_str = re.sub(radix, '.', hours_str, 1)
        hours = float(hours_str)
        days += (hours/24)
        if verbose > 4:
            msg = _("Found %f hours.") % (hours)
            logger.debug(msg)
        value = re.sub(pattern, '', value, re.IGNORECASE)
    if verbose > 5:
        msg = _("Rest after hours: '%s'." % (value))
        logger.debug(msg)

    # Search for weeks in value
    pattern = r'(\d+(?:' + radix + r'\d*)?)\s*w(?:eeks?)?'
    if verbose > 5:
        msg = _("Pattern '%s'.") % (pattern)
        logger.debug(msg)
    match = re.search(pattern, value, re.IGNORECASE)
    if match:
        weeks_str = match.group(1)
        if use_locale_radix:
            weeks_str = re.sub(radix, '.', weeks_str, 1)
        weeks = float(weeks_str)
        days += (weeks*7)
        if verbose > 4:
            msg = _("Found %f weeks.") % (weeks)
            logger.debug(msg)
        value = re.sub(pattern, '', value, re.IGNORECASE)
    if verbose > 5:
        msg = _("Rest after weeks: '%s'." % (value))
        logger.debug(msg)

    # Search for months in value
    pattern = r'(\d+(?:' + radix + r'\d*)?)\s*m(?:onths?)?'
    if verbose > 5:
        msg = _("Pattern '%s'.") % (pattern)
        logger.debug(msg)
    match = re.search(pattern, value, re.IGNORECASE)
    if match:
        months_str = match.group(1)
        if use_locale_radix:
            months_str = re.sub(radix, '.', months_str, 1)
        months = float(months_str)
        days += (months*30)
        if verbose > 4:
            msg = _("Found %f months.") % (months)
            logger.debug(msg)
        value = re.sub(pattern, '', value, re.IGNORECASE)
    if verbose > 5:
        msg = _("Rest after months: '%s'." % (value))
        logger.debug(msg)

    # Search for years in value
    pattern = r'(\d+(?:' + radix + r'\d*)?)\s*y(?:ears?)?'
    if verbose > 5:
        msg = _("Pattern '%s'.") % (pattern)
        logger.debug(msg)
    match = re.search(pattern, value, re.IGNORECASE)
    if match:
        years_str = match.group(1)
        if use_locale_radix:
            years_str = re.sub(radix, '.', years_str, 1)
        years = float(years_str)
        days += (years*365)
        if verbose > 4:
            msg = _("Found %f years.") % (years)
            logger.debug(msg)
        value = re.sub(pattern, '', value, re.IGNORECASE)
    if verbose > 5:
        msg = _("Rest after years: '%s'." % (value))
        logger.debug(msg)

    # At last search for days in value
    pattern = r'(\d+(?:' + radix + r'\d*)?)\s*(?:d(?:ays?)?)?'
    if verbose > 5:
        msg = _("Pattern '%s'.") % (pattern)
        logger.debug(msg)
    match = re.search(pattern, value, re.IGNORECASE)
    if match:
        days_str = match.group(1)
        if use_locale_radix:
            days_str = re.sub(radix, '.', days_str, 1)
        days_float = float(days_str)
        days += days_float
        if verbose > 4:
            msg = _("Found %f days.") % (days_float)
            logger.debug(msg)
        value = re.sub(pattern, '', value, re.IGNORECASE)
    if verbose > 5:
        msg = _("Rest after days: '%s'." % (value))
        logger.debug(msg)

    # warn, if there is a rest
    if re.search(r'^\s*$', value) is None:
        msg = _("Invalid content for a period: '%s'.") % (value)
        logger.warning(msg)

    if verbose > 4:
        msg = _("Total %f days found.") % (days)
        logger.debug(msg)

    return days

#------------------------------------------------------------------------

def get_address_list(address_str, verbose = 0):
    '''
    Retrieves all mail addresses from address_str and give them back
    as a list of tuples.

    @param address_str: the string with all mail addresses as a comma
                        separated list
    @type address_str:  str
    @param verbose:     level of verbosity
    @type verbose:      int

    @return: list of tuples in the form of the return value
             of email.utils.parseaddr()
    @rtype:  list

    '''

    t = gettext.translation('LogRotateCommon', locale_dir, fallback=True)
    _ = t.lgettext
    pp = pprint.PrettyPrinter(indent=4)

    addr_list = []
    addresses = []

    for row in csv.reader([address_str], doublequote=False, skipinitialspace=True):
        for address in row:
            addr_list.append(address)

    if verbose > 2:
        msg = _("Found address entries:") + "\n" + pp.pformat(addr_list)
        logger.debug(msg)

    for address in addr_list:
        address = re.sub(r',', ' ', address)
        address = re.sub(r'\s+', ' ', address)
        pair = email.utils.parseaddr(address)
        if verbose > 2:
            msg = _("Got mail address pair:") + "\n" + pp.pformat(pair)
            logger.debug(msg)
        if not email_valid(pair[1]):
            msg = _("Found invalid mail address '%s'.") % (address)
            logger.warning(msg)
            continue
        addresses.append(pair)

    return addresses

#========================================================================

if __name__ == "__main__":
    pass

#========================================================================

# vim: fileencoding=utf-8 filetype=python ts=4 expandtab
