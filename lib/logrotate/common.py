#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
@author: Frank Brehm
@contact: frank@brehm-online.com
@license: GPL3
@copyright: © 2010 - 2016 by Frank Brehm, Berlin
@summary: Module for common used functions
"""
from __future__ import absolute_import, print_function

# Standard modules
import re
import locale
import logging
import csv
import email.utils

from numbers import Number

# Third party modules

# Own modules

from fb_tools.common import pp

from .errors import UnbalancedQuotesError

from .translate import XLATOR

__version__ = '0.4.5'

_ = XLATOR.gettext
ngettext = XLATOR.ngettext

RE_WS = re.compile(r'\s+')
RE_WS_ONLY = re.compile(r'^\s*$')

RE_BS_SQ = re.compile(r"\\'")
RE_SINGLE_QUOTED = re.compile(r"^'((?:\\'|[^'])*)'")

RE_BS_DQ = re.compile(r'\\"')
RE_DOUBLE_QUOTED = re.compile(r'^"((?:\\"|[^"])*)"')

RE_UNQUOTED = re.compile(r'^((?:[^\s\'"]+|\\\'|\\")+)')
RE_UNBALANCED_QUOTE = re.compile(r'^(?P<chunk>(?P<quote>[\'"]).*)\s*')

RE_EMAIL = re.compile(
    r'^[a-z0-9._%-+]+@[a-z0-9._%-]+\.[a-z]{2,12}$',
    re.IGNORECASE)

RE_YES = re.compile(r'^\s*(?:y(?:es)?|true|on)\s*$', re.IGNORECASE)
RE_NO = re.compile(r'^\s*(?:no?|false|off)\s*$', re.IGNORECASE)

RE_UNIT_BYTES = re.compile(r'^\s*(?:b(?:yte)?)?\s*$', re.IGNORECASE)
RE_UNIT_KBYTES = re.compile(r'^\s*k(?:[bB](?:[Yy][Tt][Ee])?)?\s*$')
RE_UNIT_KIBYTES = re.compile(r'^\s*K[Ii]?(?:[bB](?:[Yy][Tt][Ee])?)?\s*$')
RE_UNIT_MBYTES = re.compile(r'^\s*M(?:B(?:yte)?)?\s*$', re.IGNORECASE)
RE_UNIT_MIBYTES = re.compile(r'^\s*Mi(?:B(?:yte)?)?\s*$', re.IGNORECASE)
RE_UNIT_GBYTES = re.compile(r'^\s*G(?:B(?:yte)?)?\s*$', re.IGNORECASE)
RE_UNIT_GIBYTES = re.compile(r'^\s*Gi(?:B(?:yte)?)?\s*$', re.IGNORECASE)
RE_UNIT_TBYTES = re.compile(r'^\s*T(?:B(?:yte)?)?\s*$', re.IGNORECASE)
RE_UNIT_TIBYTES = re.compile(r'^\s*Ti(?:B(?:yte)?)?\s*$', re.IGNORECASE)
RE_UNIT_PBYTES = re.compile(r'^\s*P(?:B(?:yte)?)?\s*$', re.IGNORECASE)
RE_UNIT_PIBYTES = re.compile(r'^\s*Pi(?:B(?:yte)?)?\s*$', re.IGNORECASE)
RE_UNIT_EBYTES = re.compile(r'^\s*E(?:B(?:yte)?)?\s*$', re.IGNORECASE)
RE_UNIT_EIBYTES = re.compile(r'^\s*Ei(?:B(?:yte)?)?\s*$', re.IGNORECASE)
RE_UNIT_ZBYTES = re.compile(r'^\s*Z(?:B(?:yte)?)?\s*$', re.IGNORECASE)
RE_UNIT_ZIBYTES = re.compile(r'^\s*Zi(?:B(?:yte)?)?\s*$', re.IGNORECASE)

LOG = logging.getLogger(__name__)


# =============================================================================
def split_parts(text, keep_quotes=False, raise_on_unbalanced=True):
    """
    Split the given text in chunks by whitespaces or
    single or double quoted strings.

    @param text: the text to split in chunks
    @type text: str
    @param keep_quotes: keep quotes of quoted chunks
    @type keep_quotes: bool
    @param raise_on_unbalanced: raise an exception on unbalanced quotes
    @type raise_on_unbalanced: bool

    @return: list of chunks
    @rtype: list
    """

    chunks = []
    if text is None:
        return chunks

    txt = str(text)
    last_chunk = ''

    # Big loop to split the text - until it is empty
    while txt != '':

        # add chunk, if there is a chunk left and a whitspace
        # at the begin of the line
        match = RE_WS.search(txt)
        if (last_chunk != '') and match:
            chunks.append(last_chunk)
            last_chunk = ''

        # clean the line
        txt = txt.strip()
        if txt == '':
            break

        # search for a single quoted string at the begin of the line
        match = RE_SINGLE_QUOTED.search(txt)
        if match:
            chunk = match.group(1)
            chunk = RE_BS_SQ.sub("'", chunk)
            if keep_quotes:
                chunk = "'" + chunk + "'"
            last_chunk += chunk
            txt = RE_SINGLE_QUOTED.sub("", txt)
            continue

        # search for a double quoted string at the begin of the line
        match = RE_DOUBLE_QUOTED.search(txt)
        if match:
            chunk = match.group(1)
            chunk = RE_BS_DQ.sub('"', chunk)
            if keep_quotes:
                chunk = '"' + chunk + '"'
            last_chunk += chunk
            txt = RE_DOUBLE_QUOTED.sub("", txt)
            continue

        # search for unquoted, whitespace delimited text
        # at the begin of the line
        match = RE_UNQUOTED.search(txt)
        if match:
            last_chunk += match.group(1)
            txt = RE_UNQUOTED.sub("", txt)
            continue

        # Only whitespaces left
        if RE_WS_ONLY.search(txt):
            break

        # Check for unbalanced quotes
        match = RE_UNBALANCED_QUOTE.search(txt)
        if match:
            chunk = match.group('chunk')
            quote_char = match.group('quote')
            if raise_on_unbalanced:
                raise UnbalancedQuotesError(text, quote_char)
            last_chunk += chunk
            txt = RE_UNBALANCED_QUOTE.sub("", txt)
            continue

        # Here we should not come to ...
        msg = _("Broken split of {chunk!r}: {left!r} left.").format(
            chunk=text, left=txt)
        raise Exception(msg)

    if last_chunk != '':
        chunks.append(last_chunk)

    return chunks


# =============================================================================
def email_valid(address):
    """
    Simple Check for E-Mail addresses

    @param address: the mail address to check
    @type address: str

    @return: Validity of the given mil address
    @rtype: bool
    """

    if address is None:
        return False

    adr = str(address)
    if adr is None or adr == '':
        return False

    if RE_EMAIL.search(adr):
        return True
    return False


# =============================================================================
def human2bytes(
        value, si_conform=False, use_locale_radix=False, as_float=False, verbose=0):
    """
    Converts the given human readable byte value (e.g. 5MB, 8.4GiB etc.)
    with a suffix into an integer/long value (without a suffix).
    It raises a ValueError on invalid values.

    Available prefixes are:
        - kB (1000), KB (1024), KiB (1024)
        - MB (1000*1000), MiB (1024*1024)
        - GB (1000³), GiB (1024³)
        - TB (1000^4), TiB (1024^4)
        - PB (1000^5), PiB (1024^5)
        - EB (1000^6), EiB (1024^6)
        - ZB (1000^7), ZiB (1024^7)

    @param value: the value to convert
    @type value: str
    @param si_conform: use factor 1000 instead of 1024 for kB a.s.o.
    @type si_conform: bool
    @param use_locale_radix: use the locale version of radix instead of the english decimal dot.
    @type use_locale_radix: bool
    @param verbose: level of verbosity
    @type verbose: int

    @return: amount of bytes
    @rtype: int (or long in Python2)
    """

    if value is None:
        msg = _("Given value is None.")
        raise ValueError(msg)

    if isinstance(value, Number):
        return int(value)

    radix = '.'
    thousep = ','
    if use_locale_radix:
        radix = locale.nl_langinfo(locale.RADIXCHAR)
        thousep = locale.nl_langinfo(locale.THOUSEP)
    radix = re.escape(radix)
    thousep = re.escape(thousep)
    if verbose > 4:
        LOG.debug(_("Using radix {radix!r}, thousend separator {sep!r}").format(
            radix=radix, sep=thousep))

    value_raw = ''
    value_pre = value
    suffix = None

    if thousep:
        value_pre = re.sub(thousep, '', value)
        if verbose > 3:
            LOG.debug(_("Value without thousend separators: {!r}.").format(value_pre))

    pattern = r'^\s*\+?(\d+(?:' + radix + r'\d*)?)\s*(\S+)?'
    match = re.search(pattern, value_pre)
    if match is not None:
        value_raw = match.group(1)
        suffix = match.group(2)
    else:
        msg = _("Could not determine bytes in {!r}.").format(value)
        raise ValueError(msg)

    if use_locale_radix:
        value_raw = re.sub(radix, '.', value_raw, 1)
    value_float = float(value_raw)
    value_long = int(value_float)
    if suffix is None:
        suffix = ''
    if verbose > 4:
        LOG.debug(
            "Value float: {vf!r}, Value long: {vl!r}, suffix: {s!r}".format(
                vf=value_float, vl=value_long, s=suffix))

    factor_bin = 1024
    factor_si = 1000
    factor = 1
    if not si_conform:
        factor_si = factor_bin

    factor = _get_factor_human2bytes(suffix, factor_bin, factor_si)
    if verbose > 4:
        msg = _("Found factor {}.").format(factor)
        LOG.debug(msg)

    fbytes = float(factor) * value_float
    if as_float:
        return fbytes
    lbytes = int(fbytes)

    return lbytes


# =============================================================================
def _get_factor_human2bytes(suffix, factor_bin, factor_si):

    factor = 1

    if RE_UNIT_BYTES.search(suffix):
        factor = 1
    elif RE_UNIT_KBYTES.search(suffix):
        factor = factor_si
    elif RE_UNIT_KIBYTES.search(suffix):
        factor = factor_bin
    elif RE_UNIT_MBYTES.search(suffix):
        factor = (factor_si * factor_si)
    elif RE_UNIT_MIBYTES.search(suffix):
        factor = (factor_bin * factor_bin)
    elif RE_UNIT_GBYTES.search(suffix):
        factor = (factor_si ** 3)
    elif RE_UNIT_GIBYTES.search(suffix):
        factor = (factor_bin ** 3)
    elif RE_UNIT_TBYTES.search(suffix):
        factor = (factor_si ** 4)
    elif RE_UNIT_TIBYTES.search(suffix):
        factor = (factor_bin ** 4)
    elif RE_UNIT_PBYTES.search(suffix):
        factor = (factor_si ** 5)
    elif RE_UNIT_PIBYTES.search(suffix):
        factor = (factor_bin ** 5)
    elif RE_UNIT_EBYTES.search(suffix):
        factor = (factor_si ** 6)
    elif RE_UNIT_EIBYTES.search(suffix):
        factor = (factor_bin ** 6)
    elif RE_UNIT_ZBYTES.search(suffix):
        factor = (factor_si ** 7)
    elif RE_UNIT_ZIBYTES.search(suffix):
        factor = (factor_bin ** 7)
    else:
        msg = _("Couldn't detect suffix {!r}.").format(suffix)
        raise ValueError(msg)

    return factor


# =============================================================================
def period2days(period, use_locale_radix=False, verbose=0):
    """
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

    @param period: the period to convert
    @type period: str
    @param use_locale_radix: use the locale version of radix instead of the english decimal dot.
    @type use_locale_radix: bool
    @param verbose: level of verbosity
    @type verbose: int

    @return: amount of days
    @rtype: float
    """

    if period is None:
        raise ValueError(_("Given period is None."))

    if isinstance(period, Number):
        return int(period)

    value = str(period).strip().lower()
    if period == '':
        raise ValueError(_("Given period was empty."))

    if verbose > 3:
        LOG.debug(_("Called with {!r}.").format(period))

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
    if verbose > 3:
        LOG.debug(_("Using radix {!r} ...").format(radix))

    (d, hours, v) = _get_hours_in_period(value, radix, use_locale_radix, verbose)
    days += d
    value = v

    (d, weeks, v) = _get_weeks_in_period(value, radix, use_locale_radix, verbose)
    days += d
    value = v

    (d, months, v) = _get_months_in_period(value, radix, use_locale_radix, verbose)
    days += d
    value = v

    (d, years, v) = _get_years_in_period(value, radix, use_locale_radix, verbose)
    days += d
    value = v

    (d, v) = _get_days_in_period(value, radix, use_locale_radix, verbose)
    days += d
    value = v

    # warn, if there is a rest
    if not RE_WS_ONLY.search(value):
        LOG.warning(_("Invalid content for a period: {!r}.").format(value))

    if verbose > 3:
        LOG.debug(_("Total {!r} days found.").format(days))

    return days


# =============================================================================
def _get_hours_in_period(value, radix, use_locale_radix=False, verbose=0):
    "Search for hours in value"

    days = 0
    hours = 0

    pattern = r'(\d+(?:' + radix + r'\d*)?)\s*h(?:ours?)?'
    if verbose > 4:
        LOG.debug(_("Pattern {!r}.").format(pattern))
    match = re.search(pattern, value, re.IGNORECASE)
    if match:
        hours_str = match.group(1)
        if use_locale_radix:
            hours_str = re.sub(radix, '.', hours_str, 1)
        hours = float(hours_str)
        days = hours / 24
        if verbose > 3:
            LOG.debug(_("Found {:.2f} hours.").format(hours))
        value = re.sub(pattern, '', value, re.IGNORECASE)
    if verbose > 4:
        LOG.debug(_("Rest after hours: {!r}.").format(value))

    return (days, hours, value)


# =============================================================================
def _get_weeks_in_period(value, radix, use_locale_radix=False, verbose=0):
    "Search for weeks in value"

    days = 0
    weeks = 0

    pattern = r'(\d+(?:' + radix + r'\d*)?)\s*w(?:eeks?)?'
    if verbose > 4:
        LOG.debug(_("Pattern {!r}.").format(pattern))
    match = re.search(pattern, value, re.IGNORECASE)
    if match:
        weeks_str = match.group(1)
        if use_locale_radix:
            weeks_str = re.sub(radix, '.', weeks_str, 1)
        weeks = float(weeks_str)
        days = weeks * 7
        if verbose > 3:
            LOG.debug(_("Found {:f} weeks.").format(weeks))
        value = re.sub(pattern, '', value, re.IGNORECASE)
    if verbose > 4:
        LOG.debug(_("Rest after weeks: {!r}.").format(value))

    return (days, weeks, value)


# =============================================================================
def _get_months_in_period(value, radix, use_locale_radix=False, verbose=0):
    "Search for months in value"

    days = 0
    months = 0

    pattern = r'(\d+(?:' + radix + r'\d*)?)\s*m(?:onths?)?'
    if verbose > 4:
        LOG.debug(_("Pattern {!r}.").format(pattern))
    match = re.search(pattern, value, re.IGNORECASE)
    if match:
        months_str = match.group(1)
        if use_locale_radix:
            months_str = re.sub(radix, '.', months_str, 1)
        months = float(months_str)
        days = months * 30
        if verbose > 3:
            LOG.debug(_("Found {:f} months.").format(months))
        value = re.sub(pattern, '', value, re.IGNORECASE)
    if verbose > 4:
        LOG.debug(_("Rest after months: {!r}.").format(value))

    return (days, months, value)


# =============================================================================
def _get_years_in_period(value, radix, use_locale_radix=False, verbose=0):
    "Search for years in value"

    days = 0
    years = 0

    pattern = r'(\d+(?:' + radix + r'\d*)?)\s*y(?:ears?)?'
    if verbose > 4:
        LOG.debug(_("Pattern {!r}.").format(pattern))
    match = re.search(pattern, value, re.IGNORECASE)
    if match:
        years_str = match.group(1)
        if use_locale_radix:
            years_str = re.sub(radix, '.', years_str, 1)
        years = float(years_str)
        days = years * 365
        if verbose > 3:
            LOG.debug(_("Found {:f} years.").format(years))
        value = re.sub(pattern, '', value, re.IGNORECASE)
    if verbose > 4:
        LOG.debug(_("Rest after years: {!r}.").format(value))

    return (days, years, value)


# =============================================================================
def _get_days_in_period(value, radix, use_locale_radix=False, verbose=0):
    "Search for days in value"

    days = 0.0

    pattern = r'(\d+(?:' + radix + r'\d*)?)\s*(?:d(?:ays?)?)?'
    if verbose > 4:
        LOG.debug(_("Pattern {!r}.").format(pattern))
    match = re.search(pattern, value, re.IGNORECASE)
    if match:
        days_str = match.group(1)
        if use_locale_radix:
            days_str = re.sub(radix, '.', days_str, 1)
        days = float(days_str)
        if verbose > 3:
            LOG.debug(_("Found {:f} days.").format(days))
        value = re.sub(pattern, '', value, re.IGNORECASE)
    if verbose > 4:
        LOG.debug(_("Rest after days: {!r}.").format(value))

    return (days, value)


# =============================================================================
def get_address_list(address_str, verbose=0):
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

    addr_list = []
    addresses = []

    for row in csv.reader([address_str], doublequote=False, skipinitialspace=True):
        for address in row:
            addr_list.append(address)

    if verbose > 3:
        msg = ngettext("Found address entry:", "Found address entries:", len(addr_list))
        msg += "\n" + pp(addr_list)
        LOG.debug(msg)

    for address in addr_list:
        address = re.sub(r',', ' ', address)
        address = re.sub(r'\s+', ' ', address)
        pair = email.utils.parseaddr(address)
        if verbose > 3:
            LOG.debug(_("Got mail address pair:") + "\n" + pp(pair))
        if not email_valid(pair[1]):
            LOG.warning(_("Found invalid mail address {!r}.").format(address))
            continue
        addresses.append(pair)

    return addresses


# =============================================================================

if __name__ == "__main__":
    pass

# =============================================================================

# vim: fileencoding=utf-8 filetype=python ts=4 expandtab
